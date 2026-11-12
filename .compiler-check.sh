#!/usr/bin/env bash
grep '^CMAKE_BUILD_TYPE:' /home/gj/llvm-build-debug/CMakeCache.txt
free -h
ps -eo rss,args | grep clang | head -6
command -v docker || true
docker version 2>/dev/null || true
