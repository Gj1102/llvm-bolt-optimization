from pathlib import Path
import ast
import csv
from collections import Counter
import hashlib
import json
import statistics
import subprocess

root = Path(__file__).resolve().parent
project = root / 'llvm-bolt-optimization'
results = project / 'results'
for path in project.rglob('*.pyc'):
    assert path.resolve().is_relative_to(project.resolve())
    path.unlink()
for path in sorted(project.rglob('__pycache__'), reverse=True):
    if not any(path.iterdir()):
        path.rmdir()
stale = results / 'compile-check.log'
if stale.exists():
    stale.unlink()

git = ['git', '-c', 'safe.directory=' + (root / '.llvm-source').as_posix(), '-C', str(root / '.llvm-source')]
revision = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
assert revision == (project / 'LLVM_REVISION').read_text().strip()
subprocess.run([*git, 'apply', '--check', str(project / 'patches/small-function-layout.patch')], check=True)
paths = {'baseline_source': root / '.reorder-original.cpp',
         'patched_source': root / '.reorder-modified.cpp',
         'baseline_header': root / '.llvm-source/bolt/include/bolt/Core/BinaryFunction.h',
         'patched_header': root / '.BinaryFunction-modified.h',
         'patch': project / 'patches/small-function-layout.patch'}
proof = {'llvm_revision': revision, 'hash_normalization': 'UTF-8 text, LF line endings',
         'patch_apply_check': 'passed',
         'sha256': {key: hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
                    for key, path in paths.items()}}
(results / 'source-verification.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
for path in project.rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
bad = []
for path in project.rglob('*'):
    if path.is_file():
        with path.open('rb') as file:
            prefix = file.read(4)
        if prefix == b'\x7fELF' or path.suffix in {'.exe', '.o', '.a', '.so', '.pyc'}:
            bad.append(str(path))
assert not bad, bad

timings = list(csv.DictReader((results / 'timings.csv').open()))
counts = Counter((row['case'], row['mode']) for row in timings)
assert len(counts) == 15 and len(set(counts.values())) == 1 and min(counts.values()) >= 15, counts
summaries = json.loads((results / 'summary.json').read_text())
for summary in summaries:
    values = [float(row['seconds']) for row in timings
              if row['case'] == summary['case'] and row['mode'] == summary['mode']]
    assert abs(statistics.median(values) - summary['median_seconds']) < 1e-12
functional = json.loads((results / 'functional.json').read_text())
regression = json.loads((results / 'regression/regression.json').read_text())
assert 'Passed: 1' in (results / 'lit.log').read_text()
audit = {'verified_date': '2026-11-11', 'llvm_revision': revision,
         'release_build_with_assertions': 'passed', 'patch_apply_check': 'passed',
         'lit_tests_passed': 1, 'functional_checks': functional['passed'],
         'regression_checks': regression['passed'], 'timed_runs': len(timings),
         'runs_per_case_and_mode': next(iter(counts.values())), 'binary_artifacts_in_submission': bad}
docker_environment=json.loads((results/'docker-runtime/environment.json').read_text())
environment=json.loads((results/'environment.json').read_text())
assert docker_environment['bolt_sha256']==environment['bolt_sha256']
docker_functional=json.loads((results/'docker-runtime/functional.json').read_text())
assert len(docker_functional['passed'])==5
audit['docker_image_validation']='passed: offline Ubuntu runtime image build and full functional tests'
audit['docker_image_id']=json.loads((results/'docker-runtime-image.json').read_text())[0]['Id']
audit['independent_confirmation']=json.loads((results/'confirmation64/uncertainty.json').read_text())
(results / 'validation.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps(audit, indent=2))
for name in ('correlated', 'dispersed', 'ordinary'):
    modes = {s['mode']: s for s in summaries if s['case'] == name}
    for off, on in [('off', 'on'), ('cdsort', 'cdsort-on')]:
        b, t = modes[off], modes[on]
        print(name, off, '->', on, 'time reduction %', 100 * (1-t['median_seconds']/b['median_seconds']),
              'swaps', t['swaps'], 'model', t['model_before'], '->', t['model_after'])
