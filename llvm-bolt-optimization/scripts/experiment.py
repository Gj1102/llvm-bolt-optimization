#!/usr/bin/env python3
"""Build workloads, collect real instrumentation profiles, verify and time BOLT."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import subprocess
import time

PROJECT = Path(__file__).resolve().parents[1]
CASES = ('correlated', 'dispersed', 'ordinary')
SUMMARY = re.compile(r'swaps=(\d+) weighted-distance-before=([\d.]+) after=([\d.]+)')


def refinement_stats(log):
    match = SUMMARY.search(log)
    if match:
        return {'swaps': int(match[1]), 'model_before': float(match[2]),
                'model_after': float(match[3]), 'skip_reason': None}
    skip = re.search(r'small-function-layout: skipped \(([^)]+)\)', log)
    if skip:
        return {'swaps': 0, 'model_before': None, 'model_after': None,
                'skip_reason': skip[1]}
    raise AssertionError('Missing refinement statistics')


def run(args, log=None):
    result = subprocess.run([str(a) for a in args],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if log:
        Path(log).write_text(result.stdout)
    if result.returncode:
        print(result.stdout, flush=True)
        result.check_returncode()
    return result.stdout


def symbols(binary):
    result = {}
    for line in run(['nm', '-S', '--defined-only', binary]).splitlines():
        fields = line.split()
        if len(fields) == 4 and fields[2].lower() == 't':
            result[fields[3]] = (int(fields[0], 16), int(fields[1], 16))
    return result


def actual_distance(binary, profile):
    """Distance for resolvable named edges; call offsets are profile/input offsets.

    This is a second approximation, not a hardware I-cache measurement. BOLT may
    change instruction offsets, so do not assert equality with its internal model.
    """
    syms = symbols(binary)
    weighted, calls, near = 0, 0, 0
    for line in profile.read_text().splitlines():
        f = line.split()
        if len(f) != 8 or f[0] != '1' or f[3] != '1':
            continue
        if f[1] not in syms or f[4] not in syms or f[1] == f[4]:
            continue
        distance = abs(syms[f[1]][0] + int(f[2], 16) -
                       syms[f[4]][0] - int(f[5], 16))
        count = int(f[7])
        weighted += distance * count
        calls += count
        if distance < 4096:
            near += count
    return {'weighted_distance_profile_offsets': weighted, 'resolved_calls': calls,
            'calls_within_4k_percent': 100 * near / calls if calls else None}


def sizes(binary):
    fields = run(['size', binary]).splitlines()[1].split()
    sections = run(['objdump', '-h', binary]).splitlines()
    code_bytes = 0
    for i, line in enumerate(sections[:-1]):
        f = line.split()
        if len(f) >= 3 and f[0].isdigit() and 'CODE' in sections[i + 1]:
            code_bytes += int(f[2], 16)
    return {'file_bytes': binary.stat().st_size, 'text_bytes': int(fields[0]),
            'code_section_bytes': code_bytes,
            'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}


def prepare(args):
    work, bolt = args.work, args.bolt
    work.mkdir(parents=True, exist_ok=True)
    run(['python3', PROJECT / 'tests/generate.py', work / 'src'])
    env = {'llvm_revision': (PROJECT / 'LLVM_REVISION').read_text().strip(),
           'platform': platform.platform(), 'cpu': Path('/proc/cpuinfo').read_text(),
           'gcc': run(['gcc', '--version']), 'bolt': run([bolt, '--version']),
           'bolt_sha256': hashlib.sha256(bolt.read_bytes()).hexdigest(),
           'cmake': run(['cmake', '--version']) if shutil.which('cmake') else None,
           'affinity': sorted(os.sched_getaffinity(0)),
           'training_iterations': args.training_iterations}
    (work / 'environment.json').write_text(json.dumps(env, indent=2))
    for name in CASES:
        case = work / name
        case.mkdir(exist_ok=True)
        original = case / 'original'
        flags = ['-O2', '-g', '-fno-pie', '-no-pie', '-fno-inline', '-fno-ipa-icf',
                 '-fno-optimize-sibling-calls', '-fno-toplevel-reorder',
                 '-fno-reorder-functions', '-fno-reorder-blocks-and-partition',
                 '-falign-functions=1', '-falign-jumps=1',
                 '-falign-loops=1', '-falign-labels=1', '-Wl,--emit-relocs']
        run(['gcc', *flags, work / 'src' / (name + '.c'), '-o', original], case / 'compile.log')
        profile = case / 'profile.fdata'
        if profile.exists():
            profile.unlink()  # instrumentation merges existing data; start clean
        run([bolt, original, '-o', case / 'instrumented', '--instrument',
             '--instrumentation-file=' + str(profile),
             '--instrumentation-file-append-pid=0'], case / 'instrument.log')
        run([case / 'instrumented', args.training_iterations], case / 'training.log')
        if not profile.is_file() or not profile.stat().st_size:
            raise RuntimeError('Instrumentation did not produce a profile: ' + str(profile))
        common = [bolt, original, '--data=' + str(profile), '--reorder-blocks=none',
                  '--split-functions=0', '--align-functions=1']
        for mode, algo, enabled in [('off', 'exec-count', False),
                                    ('on', 'exec-count', True),
                                    ('cdsort', 'cdsort', False),
                                    ('cdsort-on', 'cdsort', True)]:
            run([*common, '--reorder-functions=' + algo,
                 '--small-function-layout=' + str(enabled).lower(),
                 '--generate-function-order=' + str(case / (mode + '.order')),
                 '-o', case / mode], case / (mode + '.log'))
        print('Prepared', name, flush=True)
    # Real command lines are preserved in BOLT logs and metadata as well.
    (work / 'compile-flags.json').write_text(json.dumps(flags, indent=2))


def functional(args):
    checks = []
    for name in CASES:
        case = args.work / name
        # Different inputs exercise arithmetic and loop boundaries.
        for n in (0, 1, 17, 211):
            expected = run([case / 'original', n])
            for mode in ('off', 'on', 'cdsort', 'cdsort-on'):
                assert run([case / mode, n]) == expected, (name, mode, n)
        for mode in ('on', 'cdsort-on'):
            stat = refinement_stats((case / (mode + '.log')).read_text())
            if stat['skip_reason']:
                base = 'off' if mode == 'on' else 'cdsort'
                assert (case / (mode + '.order')).read_bytes() == (case / (base + '.order')).read_bytes()
            else:
                assert stat['model_after'] <= stat['model_before'], (name, mode, 'model regressed')
                if stat['swaps']:
                    assert stat['model_after'] < stat['model_before']
        # An option that is default-off must preserve the baseline layout.
        run([args.bolt, case / 'original', '--data=' + str(case / 'profile.fdata'),
             '--reorder-functions=exec-count', '--reorder-blocks=none',
             '--split-functions=0', '--align-functions=1',
             '--generate-function-order=' + str(case / 'default.order'),
             '-o', case / 'default'], case / 'default.log')
        assert (case / 'default.order').read_bytes() == (case / 'off.order').read_bytes()
        checks.append(name + ': 16 output comparisons; model monotonicity; default-off order')
        before_order = (case / 'off.order').read_text().splitlines()
        after_order = (case / 'on.order').read_text().splitlines()
        assert sorted(before_order) == sorted(after_order)
        input_symbols = symbols(case / 'original')
        for i, function in enumerate(before_order):
            if function in input_symbols and input_symbols[function][1] > 128:
                assert after_order[i] == function, (name, function, 'large-function barrier moved')
    ordinary = args.work / 'ordinary'
    assert (ordinary / 'on.order').read_bytes() == (ordinary / 'off.order').read_bytes()
    assert refinement_stats((ordinary / 'on.log').read_text())['swaps'] == 0
    # No profile: same baseline order, no static fallback graph.
    for mode in ('off', 'on'):
        run([args.bolt, ordinary / 'original', '--small-function-layout=' + str(mode == 'on').lower(),
             '--generate-function-order=' + str(ordinary / ('no-profile-' + mode + '.order')),
             '-o', ordinary / ('no-profile-' + mode)], ordinary / ('no-profile-' + mode + '.log'))
        assert run([ordinary / ('no-profile-' + mode), 17]) == run([ordinary / 'original', 17])
    assert 'no valid call edges' in (ordinary / 'no-profile-on.log').read_text()
    assert (ordinary / 'no-profile-off.order').read_bytes() == (ordinary / 'no-profile-on.order').read_bytes()
    checks += ['ordinary: zero swaps and identical order', 'missing profile: skipped; identical order and output']
    (args.work / 'functional.json').write_text(json.dumps({'passed': checks}, indent=2))
    print('\n'.join(checks), flush=True)


def benchmark(args):
    # Pin all timed children to one available logical CPU; preserve the choice.
    cpu = min(os.sched_getaffinity(0)) if args.cpu is None else args.cpu
    os.sched_setaffinity(0, {cpu})
    rows, summaries = [], []
    rng = random.Random(args.order_seed)
    (args.work / 'benchmark-settings.json').write_text(json.dumps(
        {'repeats': args.repeats, 'min_seconds_target': args.min_seconds,
         'order_seed': args.order_seed, 'cpu': cpu}, indent=2))
    modes = ('original', 'off', 'on', 'cdsort', 'cdsort-on')
    for name in CASES:
        case = args.work / name
        iterations = args.iterations
        # Calibrate on off, then use the SAME iteration count for all variants.
        start = time.perf_counter()
        run([case / 'off', iterations])
        elapsed = time.perf_counter() - start
        if elapsed < args.min_seconds:
            iterations = max(iterations, int(iterations * args.min_seconds / max(elapsed, .001)))
        expected = run([case / 'original', iterations])
        for mode in modes:
            assert run([case / mode, iterations]) == expected
        for repeat in range(args.repeats):
            order = list(modes)
            rng.shuffle(order)
            for mode in order:
                start = time.perf_counter_ns()
                output = run([case / mode, iterations])
                seconds = (time.perf_counter_ns() - start) / 1e9
                assert output == expected
                rows.append({'case': name, 'mode': mode, 'repeat': repeat,
                             'iterations': iterations, 'cpu': cpu, 'seconds': seconds})
        for mode in modes:
            times = [r['seconds'] for r in rows if r['case'] == name and r['mode'] == mode]
            item = {'case': name, 'mode': mode, 'iterations': iterations, 'cpu': cpu,
                    'median_seconds': statistics.median(times),
                    'min_seconds': min(times), 'max_seconds': max(times),
                    **sizes(case / mode), **actual_distance(case / mode, case / 'profile.fdata')}
            if mode in ('on', 'cdsort-on'):
                item.update(refinement_stats((case / (mode + '.log')).read_text()))
            summaries.append(item)
        print('Measured', name, iterations, 'iterations,', args.repeats, 'repeats', flush=True)
    with (args.work / 'timings.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.work / 'summary.json').write_text(json.dumps(summaries, indent=2))
    report = ['# 实测结果', '', '计时为固定单核、预热后随机交错执行的 wall time；原始数据见 timings.csv。', '',
              '| 程序 | 模式 | 中位时间(s) | min–max(s) | 文件字节 | CODE段字节 | 交换次数 |',
              '|---|---|---:|---:|---:|---:|---:|']
    for r in summaries:
        report.append(f"| {r['case']} | {r['mode']} | {r['median_seconds']:.6f} | "
                      f"{r['min_seconds']:.6f}–{r['max_seconds']:.6f} | {r['file_bytes']} | "
                      f"{r['code_section_bytes']} | {r.get('swaps', '—')} |")
    report += ['', '正值代表中位时间减少；小幅变化需要结合原始波动判断：', '']
    for name in CASES:
        by_mode = {r['mode']: r for r in summaries if r['case'] == name}
        for baseline, treatment in [('off', 'on'), ('cdsort', 'cdsort-on')]:
            b, t = by_mode[baseline], by_mode[treatment]
            gain = 100 * (1 - t['median_seconds'] / b['median_seconds'])
            if t['model_before'] is None:
                distance_note = '优化跳过，未计算内部距离：' + t['skip_reason']
            else:
                drop = 100 * (1 - t['model_after'] / t['model_before']) if t['model_before'] else 0
                distance_note = f'估计距离减少 {drop:.2f}%'
            report.append(f"- {name}, {baseline} → {treatment}: 时间变化 {gain:+.2f}%；{distance_note}。")
    report += ['', '距离指标属于估计布局模型，不能据此声称 I-Cache miss 已降低。',
               'WSL/虚拟化、CPU 频率和系统噪声限制结论；没有跨机器或真实应用推广结论。']
    (args.work / 'RESULTS.md').write_text('\n'.join(report) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=('prepare', 'functional', 'benchmark'))
    p.add_argument('--work', type=Path, default=Path(os.environ.get('WORK', '/tmp/bolt-experiments')))
    p.add_argument('--bolt', type=Path, default=Path(os.environ.get('BOLT', '/tmp/bolt-small-layout/build/bin/llvm-bolt')))
    p.add_argument('--training-iterations', type=int, default=1000)
    p.add_argument('--iterations', type=int, default=10000)
    p.add_argument('--min-seconds', type=float, default=.4)
    p.add_argument('--repeats', type=int, default=15)
    p.add_argument('--cpu', type=int)
    p.add_argument('--order-seed', type=int, default=123)
    args = p.parse_args()
    args.work = args.work.resolve()
    args.bolt = args.bolt.resolve()
    if args.repeats < 1 or args.iterations < 1 or args.training_iterations < 1:
        p.error('repeat and iteration counts must be positive')
    globals()[args.phase](args)


if __name__ == '__main__':
    main()
