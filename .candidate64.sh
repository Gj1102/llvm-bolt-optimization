#!/usr/bin/env bash
set -euo pipefail
BASE=/home/gj/bolt-course-4794
PROJECT=/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization
SOURCE=$BASE/llvm-project/bolt/lib/Passes/ReorderFunctions.cpp
cp "$SOURCE" "$BASE/ReorderFunctions.release.cpp"
restore() { cp "$BASE/ReorderFunctions.release.cpp" "$SOURCE"; }
trap restore EXIT
python3 - "$SOURCE" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text(); assert text.count('Round < 8')==1
p.write_text(text.replace('Round < 8','Round < 64'))
PY
cmake --build "$BASE/build-gcc" --target llvm-bolt -j 6 > "$PROJECT/results/candidate64-build.log" 2>&1
mkdir -p "$BASE/candidate64/bin" "$BASE/candidate64/lib"
cp "$BASE/build-gcc/bin/llvm-bolt" "$BASE/candidate64/bin/"
cp "$BASE/build-gcc/lib/libbolt_rt_instr.a" "$BASE/build-gcc/lib/libbolt_rt_hugify.a" "$BASE/candidate64/lib/"
restore
cmake --build "$BASE/build-gcc" --target llvm-bolt -j 6 >> "$PROJECT/results/candidate64-build.log" 2>&1
export BOLT=$BASE/candidate64/bin/llvm-bolt
export WORK=$BASE/experiments64
python3 "$PROJECT/scripts/experiment.py" prepare
python3 "$PROJECT/scripts/experiment.py" functional
python3 "$PROJECT/scripts/experiment.py" benchmark --repeats 31 --min-seconds 1
python3 "$PROJECT/scripts/export_results.py" "$WORK" "$PROJECT/results/candidate64"
python3 "$PROJECT/scripts/analyze_uncertainty.py" "$PROJECT/results/candidate64"
