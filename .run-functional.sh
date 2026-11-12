#!/usr/bin/env bash
set -euo pipefail
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
export BOLT=/home/gj/bolt-course-4794/build-gcc/bin/llvm-bolt
export WORK=/home/gj/bolt-course-4794/experiments
python3 "$PROJECT/scripts/run_lit.py"
python3 "$PROJECT/scripts/regression.py"
python3 "$PROJECT/scripts/experiment.py" prepare
python3 "$PROJECT/scripts/experiment.py" functional
