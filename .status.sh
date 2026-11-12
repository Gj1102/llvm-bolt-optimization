#!/usr/bin/env bash
ps -eo pid,etimes,rss,args | grep -E 'tar -C|cmake|ninja|clang.*\.cpp|\.build-local' | head -15
du -sh /home/gj/bolt-course-4794/llvm-project /home/gj/bolt-course-4794/build 2>/dev/null || true
tail -12 /mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization/results/configure.log 2>/dev/null || true
tail -5 /mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization/results/build.log 2>/dev/null || true
