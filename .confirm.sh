#!/usr/bin/env bash
set -euo pipefail
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
BASE=/home/gj/bolt-course-4794
export BOLT=$BASE/build-gcc/bin/llvm-bolt
export WORK=$BASE/confirmation
mkdir -p "$WORK"
cp -a "$BASE/experiments/correlated" "$BASE/experiments/dispersed" "$BASE/experiments/ordinary" "$WORK/"
cp "$BASE/experiments/environment.json" "$WORK/"
python3 "$PROJECT/scripts/experiment.py" benchmark --repeats 31 --min-seconds 1.5
python3 "$PROJECT/scripts/export_results.py" "$WORK" "$PROJECT/results/confirmation"
python3 "$PROJECT/scripts/analyze_uncertainty.py" "$PROJECT/results/confirmation"
