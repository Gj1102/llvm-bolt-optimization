#!/usr/bin/env bash
set -u
ROOT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
docker images --format '{{.Repository}}:{{.Tag}}' | head -10
docker build --check "$ROOT" > "$ROOT/results/docker-check.log" 2>&1
