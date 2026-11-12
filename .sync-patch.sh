#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
cp "$ROOT/.reorder-modified.cpp" /home/gj/bolt-course-4794/llvm-project/bolt/lib/Passes/ReorderFunctions.cpp
cp "$ROOT/llvm-bolt-optimization/tests/local-swap.s" /home/gj/bolt-course-4794/llvm-project/bolt/test/X86/small-function-layout.s
