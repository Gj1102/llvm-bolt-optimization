#!/usr/bin/env python3
"""Small real-BOLT regression: a good local edge must not hide bad external edges."""
import json
import os
from pathlib import Path
import re
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
BOLT = Path(os.environ.get('BOLT', '/tmp/bolt-small-layout/build/bin/llvm-bolt'))
WORK = Path(os.environ.get('WORK', '/tmp/bolt-experiments')) / 'regression'


def run(argv, log=None):
    process = subprocess.run([str(x) for x in argv], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = process.stdout
    if log:
        log.write_text(result)
    if process.returncode:
        print(result, flush=True)
        process.check_returncode()
    return result


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    binary = WORK / 'fixture'
    run(['gcc', '-no-pie', '-Wl,--emit-relocs', PROJECT / 'tests/local-swap.s', '-o', binary])
    checks = []
    for label, weight, b_weight, c_weight, swaps in [
            ('accept', 1000, 100, 100, 1), ('tie', 1900, 100, 100, 0),
            ('external-veto', 10000, 100, 100, 0), ('low-count', 100, 10, 10, 0)]:
        profile = WORK / (label + '.fdata')
        profile.write_text(f'0 [unknown] 0 1 main 0 0 {weight}\n'
                           f'1 main 4 1 small_a 0 0 {weight}\n'
                           f'1 main b 1 main d 0 {b_weight}\n'
                           f'1 main b 1 main 12 0 {weight-b_weight}\n'
                           f'1 main d 1 small_b 0 0 {b_weight}\n'
                           f'1 small_a 2 1 small_a 4 0 {c_weight}\n'
                           f'1 small_a 2 1 small_a 11 0 {weight-c_weight}\n'
                           f'1 small_a 8 1 large_c 0 0 {c_weight}\n')
        orders = {}
        for mode in ('off', 'on'):
            order, output = WORK / (label + '-' + mode + '.order'), WORK / (label + '-' + mode)
            log = run([BOLT, binary, '--data=' + str(profile), '--reorder-functions=none',
                       '--reorder-blocks=none', '--split-functions=0', '--align-functions=1',
                       '--small-function-layout=' + str(mode == 'on').lower(),
                       '--generate-function-order=' + str(order), '-o', output],
                      WORK / (label + '-' + mode + '.log'))
            run([output])
            orders[mode] = [x for x in order.read_text().splitlines()
                            if x in ('main', 'small_a', 'small_b', 'large_c')]
            if mode == 'on':
                match = re.search(r'swaps=(\d+)', log)
                assert match and int(match[1]) == swaps, (label, log)
        assert orders['off'] == ['main', 'small_a', 'small_b', 'large_c'], orders
        expected = ['main', 'small_b', 'small_a', 'large_c'] if swaps else orders['off']
        assert orders['on'] == expected, (label, orders)
        checks.append(label + ': passed; swaps=' + str(swaps))
    # User-defined order is deliberately protected, even when an improving swap exists.
    user = WORK / 'user.order'
    user.write_text('main\nsmall_a\nsmall_b\nlarge_c\n')
    log = run([BOLT, binary, '--data=' + str(WORK / 'accept.fdata'),
               '--function-order=' + str(user), '--small-function-layout',
               '--generate-function-order=' + str(WORK / 'user-output.order'),
               '-o', WORK / 'user-output'], WORK / 'user.log')
    assert 'skipped (unsupported order)' in log
    assert (WORK / 'user-output.order').read_text().splitlines()[:4] == user.read_text().splitlines()
    run([WORK / 'user-output'])
    checks.append('explicit user order: skipped and preserved')
    no_relocs = WORK / 'no-relocations'
    run(['gcc', '-no-pie', PROJECT / 'tests/local-swap.s', '-o', no_relocs])
    log = run([BOLT, no_relocs, '--data=' + str(WORK / 'accept.fdata'),
               '--small-function-layout', '-o', WORK / 'no-relocations-output'],
              WORK / 'no-relocations.log')
    assert 'skipped (unsupported order)' in log
    run([WORK / 'no-relocations-output'])
    checks.append('missing relocations: skipped; executable runs')
    (WORK / 'regression.json').write_text(json.dumps({'passed': checks}, indent=2))
    print('\n'.join(checks))


if __name__ == '__main__':
    main()
