#!/usr/bin/env python3
"""Copy evidence into the repo without copying binaries or LLVM build products."""
import argparse
from pathlib import Path
import shutil

p = argparse.ArgumentParser()
p.add_argument('work', type=Path)
p.add_argument('output', type=Path, nargs='?', default=Path(__file__).resolve().parents[1] / 'results')
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
allowed = {'.json', '.csv', '.md', '.log', '.order', '.fdata'}
for source in args.work.rglob('*'):
    if source.is_file() and source.suffix in allowed:
        target = args.output / source.relative_to(args.work)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
print('Exported evidence to', args.output)
