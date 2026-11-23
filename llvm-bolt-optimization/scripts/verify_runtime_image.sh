#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
image=${1:-bolt-small-layout:verified}
docker run --rm --network=none \
  --mount "type=bind,src=$project,dst=/project,readonly" \
  "$image" bash -c 'python3 scripts/run_lit.py && python3 scripts/regression.py && python3 scripts/experiment.py prepare && python3 scripts/experiment.py functional'
