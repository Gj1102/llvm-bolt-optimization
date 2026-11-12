#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
WORK=/home/gj/bolt-course-4794
REV=$(cat "$ROOT/llvm-bolt-optimization/LLVM_REVISION")
cmake -S "$WORK/llvm-project/llvm" -B "$WORK/build-gcc" \
  -DLLVM_FORCE_VC_REVISION="$REV" \
  -DLLVM_FORCE_VC_REPOSITORY=https://github.com/llvm/llvm-project \
  > "$ROOT/llvm-bolt-optimization/results/configure.log" 2>&1
cmake --build "$WORK/build-gcc" --target llvm-bolt merge-fdata llvm-mc llvm-objdump llvm-nm FileCheck -j 6 \
  >> "$ROOT/llvm-bolt-optimization/results/build.log" 2>&1
"$WORK/build-gcc/bin/llvm-bolt" --version > "$ROOT/llvm-bolt-optimization/results/bolt-version.txt"
cat "$ROOT/llvm-bolt-optimization/results/bolt-version.txt"
