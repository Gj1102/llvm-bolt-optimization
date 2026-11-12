import importlib.util
from pathlib import Path
from types import SimpleNamespace
import subprocess

project=Path('/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization')
spec=importlib.util.spec_from_file_location('experiment',project/'scripts/experiment.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.CASES=('correlated',)
args=SimpleNamespace(work=Path('/home/gj/bolt-course-4794/confirmation64'),
                     bolt=Path('/home/gj/bolt-course-4794/candidate64/bin/llvm-bolt'),
                     training_iterations=1000, iterations=10000, min_seconds=1.5,
                     repeats=31,cpu=None,order_seed=456)
module.prepare(args)
module.benchmark(args)
out=project/'results/confirmation64'
subprocess.run(['python3',str(project/'scripts/export_results.py'),str(args.work),str(out)],check=True)
subprocess.run(['python3',str(project/'scripts/analyze_uncertainty.py'),str(out)],check=True)
