#!/usr/bin/env bash
set -euo pipefail
PROJECT=$(cd -- "$(dirname -- "$0")/.." && pwd)
: "${BOLT:?Set BOLT to the verified compiled llvm-bolt}"
: "${LLVM_SOURCE:?Set LLVM_SOURCE to the matching LLVM checkout}"
: "${RUNTIME_CONTEXT:?Set RUNTIME_CONTEXT to a new directory outside this project}"
test ! -e "$RUNTIME_CONTEXT"
python3 - "$PROJECT" "$RUNTIME_CONTEXT" <<'PY'
from pathlib import Path
import sys
if Path(sys.argv[2]).resolve().is_relative_to(Path(sys.argv[1]).resolve()):
    raise SystemExit('RUNTIME_CONTEXT must be outside the submission directory')
PY
mkdir -p "$RUNTIME_CONTEXT/runtime/bin" "$RUNTIME_CONTEXT/runtime/lib" \
  "$RUNTIME_CONTEXT/llvm-test-tools/llvm/utils" "$RUNTIME_CONTEXT/llvm-test-tools/bolt/test"
BUILD_BIN=$(dirname -- "$BOLT")
for tool in llvm-bolt merge-fdata llvm-mc llvm-nm FileCheck; do
  cp "$BUILD_BIN/$tool" "$RUNTIME_CONTEXT/runtime/bin/"
done
cp "$BUILD_BIN/../lib/libbolt_rt_instr.a" "$RUNTIME_CONTEXT/runtime/lib/"
cp "$BUILD_BIN/../lib/libbolt_rt_hugify.a" "$RUNTIME_CONTEXT/runtime/lib/"
cp -a "$LLVM_SOURCE/llvm/utils/lit" "$RUNTIME_CONTEXT/llvm-test-tools/llvm/utils/"
cp "$LLVM_SOURCE/bolt/test/link_fdata.py" "$RUNTIME_CONTEXT/llvm-test-tools/bolt/test/"
mkdir "$RUNTIME_CONTEXT/project"
tar -C "$PROJECT" --exclude=.git --exclude=__pycache__ --exclude=results -cf - . | tar -C "$RUNTIME_CONTEXT/project" -xf -
cat > "$RUNTIME_CONTEXT/.dockerignore" <<'EOF'
project/results
project/.git
**/__pycache__
EOF
cp "$PROJECT/Dockerfile.runtime" "$RUNTIME_CONTEXT/Dockerfile"
python3 "$PROJECT/scripts/package_toolchain.py" "$RUNTIME_CONTEXT/toolchain"
printf 'External Docker context prepared: %s\n' "$RUNTIME_CONTEXT"
