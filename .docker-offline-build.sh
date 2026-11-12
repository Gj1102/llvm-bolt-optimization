#!/usr/bin/env bash
set -euo pipefail
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
CONTEXT=/home/gj/bolt-course-4794/runtime-context
pkill -TERM -f '^docker build --network=host --build-arg BASE_IMAGE=python:3.11-slim' || true
python3 "$PROJECT/scripts/package_toolchain.py" "$CONTEXT/toolchain"
cp "$PROJECT/Dockerfile.runtime" "$CONTEXT/Dockerfile"
docker build --network=none -t bolt-small-layout:verified "$CONTEXT" > "$PROJECT/results/docker-runtime-build.log" 2>&1
docker run --rm --network=none -v "$PROJECT/results/docker-runtime:/results" bolt-small-layout:verified \
  bash -c 'python3 scripts/run_lit.py && python3 scripts/regression.py && python3 scripts/experiment.py prepare && python3 scripts/experiment.py functional && python3 scripts/export_results.py "$WORK" /results' \
  > "$PROJECT/results/docker-runtime-test.log" 2>&1
docker image inspect bolt-small-layout:verified > "$PROJECT/results/docker-runtime-image.json"
