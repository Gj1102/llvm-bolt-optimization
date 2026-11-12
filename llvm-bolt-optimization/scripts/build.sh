#!/usr/bin/env bash
set -euo pipefail
PROJECT=$(cd -- "$(dirname -- "$0")/.." && pwd)
WORK=${WORK:-/tmp/bolt-small-layout}
JOBS=${JOBS:-2}
REV=$(cat "$PROJECT/LLVM_REVISION")
mkdir -p "$WORK"
if [[ ! -d "$WORK/llvm-project/.git" ]]; then
  git init "$WORK/llvm-project"
  git -C "$WORK/llvm-project" config core.autocrlf false
  git -C "$WORK/llvm-project" remote add origin https://github.com/llvm/llvm-project.git
  git -C "$WORK/llvm-project" sparse-checkout set bolt cmake third-party libc llvm/include llvm/lib llvm/tools llvm/utils llvm/cmake llvm/projects
  git -C "$WORK/llvm-project" fetch --depth=1 --filter=blob:none origin "$REV"
  git -C "$WORK/llvm-project" checkout --detach FETCH_HEAD
fi
test "$(git -C "$WORK/llvm-project" rev-parse HEAD)" = "$REV"
PATCH="$PROJECT/patches/small-function-layout.patch"
if git -C "$WORK/llvm-project" apply --check "$PATCH"; then
  git -C "$WORK/llvm-project" apply "$PATCH"
else
  git -C "$WORK/llvm-project" apply --reverse --check "$PATCH"
fi
cmake -G Ninja -S "$WORK/llvm-project/llvm" -B "$WORK/build" \
  -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS=bolt \
  -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_ENABLE_ASSERTIONS=ON \
  -DLLVM_FORCE_VC_REVISION="$REV" \
  -DLLVM_FORCE_VC_REPOSITORY=https://github.com/llvm/llvm-project \
  -DLLVM_INCLUDE_TESTS=OFF -DLLVM_BUILD_UTILS=ON -DLLVM_INCLUDE_BENCHMARKS=OFF \
  -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_DOCS=OFF -DLLVM_INCLUDE_RUNTIMES=OFF \
  -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_ZLIB=OFF \
  -DLLVM_USE_LINKER=lld -DLLVM_PARALLEL_LINK_JOBS=1
cmake --build "$WORK/build" --target llvm-bolt merge-fdata llvm-mc llvm-objdump llvm-nm FileCheck -j "$JOBS"
"$WORK/build/bin/llvm-bolt" --version
