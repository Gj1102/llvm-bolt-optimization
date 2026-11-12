#!/usr/bin/env bash
set -euo pipefail
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
CONTEXT=/home/gj/bolt-course-4794/runtime-context
tar -C "$PROJECT" --exclude=.git --exclude=__pycache__ --exclude=results -cf - . | tar -C "$CONTEXT/project" -xf -
cat > "$CONTEXT/.dockerignore" <<'EOF'
project/results
project/.git
**/__pycache__
EOF
docker image inspect ubuntu:24.04 > "$PROJECT/results/docker-runtime-base.json"
docker build --network=none -t bolt-small-layout:verified "$CONTEXT" > "$PROJECT/results/docker-runtime-build.log" 2>&1
docker run --rm --network=none -v "$PROJECT/results/docker-runtime:/results" bolt-small-layout:verified \
  bash -c 'python3 scripts/run_lit.py && python3 scripts/regression.py && python3 scripts/experiment.py prepare && python3 scripts/experiment.py functional && python3 scripts/export_results.py "$WORK" /results' \
  > "$PROJECT/results/docker-runtime-test.log" 2>&1
docker run --rm --network=none -i bolt-small-layout:verified bash -c \
  'cat >/tmp/smoke.cpp; g++ /tmp/smoke.cpp -o /tmp/smoke && test "$(/tmp/smoke)" = 6 && echo "C++ compiler and runtime: passed"' \
  > "$PROJECT/results/docker-cpp-smoke.log" 2>&1 <<'CPP'
#include <iostream>
#include <vector>
int main() { std::vector<int> v{1,2,3}; int s=0; for(int x:v) s+=x; std::cout<<s; }
CPP
docker image inspect bolt-small-layout:verified > "$PROJECT/results/docker-runtime-image.json"
