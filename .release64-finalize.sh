#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
BASE=/home/gj/bolt-course-4794
mkdir -p "$BASE/eight-rounds-work-metadata"
for name in summary.json timings.csv RESULTS.md benchmark-settings.json; do
  if [[ -f "$BASE/experiments/$name" ]]; then mv "$BASE/experiments/$name" "$BASE/eight-rounds-work-metadata/$name"; fi
done
bash "$ROOT/.rebuild-refinement.sh"
python3 "$ROOT/llvm-bolt-optimization/scripts/export_results.py" "$BASE/experiments" "$ROOT/llvm-bolt-optimization/results/release-functional"
CONTEXT=$BASE/runtime-context
cp "$BASE/build-gcc/bin/llvm-bolt" "$CONTEXT/runtime/bin/"
tar -C "$ROOT/llvm-bolt-optimization" --exclude=.git --exclude=__pycache__ -cf - . | tar -C "$CONTEXT/project" -xf -
bash "$ROOT/.docker-ubuntu-offline.sh"
