#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import os, signal
from pathlib import Path
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        cmd = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
        cwd = str((proc / 'cwd').resolve())
        if cwd.startswith('/home/gj/bolt-course-4794/build') and ('clang' in cmd or '/usr/bin/ninja' in cmd):
            os.kill(int(proc.name), signal.SIGTERM)
    except (OSError, UnicodeError):
        pass
PY
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
WORK=/home/gj/bolt-course-4794
cmake -G Ninja -S "$WORK/llvm-project/llvm" -B "$WORK/build-gcc" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
  -DLLVM_ENABLE_PROJECTS=bolt -DLLVM_TARGETS_TO_BUILD=X86 \
  -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_INCLUDE_TESTS=OFF -DLLVM_BUILD_UTILS=ON \
  -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_ZLIB=OFF \
  -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF -DLLVM_INCLUDE_RUNTIMES=OFF \
  -DLLVM_USE_LINKER=lld -DLLVM_PARALLEL_LINK_JOBS=1 \
  > "$ROOT/llvm-bolt-optimization/results/configure.log" 2>&1
cmake --build "$WORK/build-gcc" --target llvm-bolt merge-fdata llvm-mc llvm-objdump llvm-nm FileCheck -j 6 \
  > "$ROOT/llvm-bolt-optimization/results/build.log" 2>&1
"$WORK/build-gcc/bin/llvm-bolt" --version
