#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
WORK=/home/gj/bolt-course-4794
cp "$ROOT/.reorder-modified.cpp" "$WORK/llvm-project/bolt/lib/Passes/ReorderFunctions.cpp"
cp "$ROOT/llvm-bolt-optimization/tests/local-swap.s" "$WORK/llvm-project/bolt/test/X86/small-function-layout.s"
cmake --build "$WORK/build-gcc" --target llvm-bolt -j 6 >> "$ROOT/llvm-bolt-optimization/results/build.log" 2>&1
bash "$ROOT/.run-functional.sh"
