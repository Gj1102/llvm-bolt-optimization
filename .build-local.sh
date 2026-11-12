#!/usr/bin/env bash
set -euo pipefail
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1
WORK=/home/gj/bolt-course-4794
mkdir -p "$WORK"
if [[ ! -d "$WORK/llvm-project" ]]; then
  mkdir "$WORK/llvm-project"
  # WSL's Linux filesystem avoids slow compilation on /mnt/d.
  tar -C "$ROOT/.llvm-source" --exclude=.git -cf - . | tar -C "$WORK/llvm-project" -xf -
fi
WORK=/home/gj/bolt-course-4794
if [[ ! -d "$WORK/llvm-project/libc" ]]; then
  mkdir "$WORK/llvm-project/libc"
  tar -C "$ROOT/.llvm-source/libc" -cf - . | tar -C "$WORK/llvm-project/libc" -xf -
fi
cp "$ROOT/.reorder-modified.cpp" "$WORK/llvm-project/bolt/lib/Passes/ReorderFunctions.cpp"
mkdir -p "$WORK/llvm-project/llvm/projects"
cp "$ROOT/.llvm-source/llvm/projects/CMakeLists.txt" "$WORK/llvm-project/llvm/projects/CMakeLists.txt"
python3 - "$WORK/llvm-project" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
if not (root / '.lf-normalized').exists():
    for path in root.rglob('*'):
        if path.is_file():
            data = path.read_bytes()
            if b'\0' not in data and b'\r\n' in data:
                path.write_bytes(data.replace(b'\r\n', b'\n'))
    (root / '.lf-normalized').touch()
PY
python3 - "$WORK/llvm-project" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
if not (root / '.lf-normalized').exists():
    for path in root.rglob('*'):
        if path.is_file():
            data = path.read_bytes()
            if b'\0' not in data and b'\r\n' in data:
                path.write_bytes(data.replace(b'\r\n', b'\n'))
    (root / '.lf-normalized').touch()
PY
cmake -G Ninja -S "$WORK/llvm-project/llvm" -B "$WORK/build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/home/gj/llvm-build-debug/bin/clang \
  -DCMAKE_CXX_COMPILER=/home/gj/llvm-build-debug/bin/clang++ \
  -DLLVM_ENABLE_PROJECTS=bolt -DLLVM_TARGETS_TO_BUILD=X86 \
  -DLLVM_ENABLE_ASSERTIONS=ON -DLLVM_INCLUDE_TESTS=OFF -DLLVM_BUILD_UTILS=ON \
  -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_ZLIB=OFF \
  -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF -DLLVM_INCLUDE_RUNTIMES=OFF \
  -DLLVM_USE_LINKER=lld -DLLVM_PARALLEL_LINK_JOBS=1 \
  > "$ROOT/llvm-bolt-optimization/results/configure.log" 2>&1
cmake --build "$WORK/build" --target llvm-bolt merge-fdata llvm-mc llvm-objdump llvm-nm FileCheck -j 4 \
  > "$ROOT/llvm-bolt-optimization/results/build.log" 2>&1
"$WORK/build/bin/llvm-bolt" --version
