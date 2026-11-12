#!/usr/bin/env bash
set -euo pipefail
BASE=/home/gj/bolt-course-4794
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
export BOLT=$BASE/build-gcc/bin/llvm-bolt
export LLVM_SOURCE=$BASE/llvm-project
export RUNTIME_CONTEXT=$BASE/runtime-context
if [[ ! -d "$RUNTIME_CONTEXT" ]]; then bash "$PROJECT/scripts/package_runtime.sh"; fi
cp "$PROJECT/Dockerfile.runtime" "$RUNTIME_CONTEXT/Dockerfile"
docker image inspect python:3.11-slim > "$PROJECT/results/docker-runtime-base.json"
docker build --network=host --build-arg BASE_IMAGE=python:3.11-slim \
  --build-arg http_proxy=http://172.26.208.1:18797 \
  --build-arg https_proxy=http://172.26.208.1:18797 \
  -t bolt-small-layout:verified "$RUNTIME_CONTEXT" \
  > "$PROJECT/results/docker-runtime-build.log" 2>&1
docker run --rm -v "$PROJECT/results/docker-runtime:/results" bolt-small-layout:verified \
  bash -c 'python3 scripts/run_lit.py && python3 scripts/regression.py && python3 scripts/experiment.py prepare && python3 scripts/experiment.py functional && python3 scripts/export_results.py "$WORK" /results' \
  > "$PROJECT/results/docker-runtime-test.log" 2>&1
docker image inspect bolt-small-layout:verified > "$PROJECT/results/docker-runtime-image.json"
