#!/usr/bin/env bash
set -euo pipefail
PROJECT=$(cd -- "$(dirname -- "$0")/.." && pwd)
python3 "$PROJECT/scripts/run_lit.py"
python3 "$PROJECT/scripts/regression.py"
python3 "$PROJECT/scripts/experiment.py" prepare "$@"
python3 "$PROJECT/scripts/experiment.py" functional "$@"
python3 "$PROJECT/scripts/experiment.py" benchmark "$@"
