#!/usr/bin/env python3
"""Describe uncertainty from matched repeat blocks; do not infer cache misses."""
import argparse
import csv
import json
from pathlib import Path
import random
import statistics

p = argparse.ArgumentParser()
p.add_argument('results', type=Path)
args = p.parse_args()
rows = list(csv.DictReader((args.results / 'timings.csv').open()))
rng = random.Random(42)
output = []
for case in sorted({row['case'] for row in rows}):
    for baseline, treatment in [('off', 'on'), ('cdsort', 'cdsort-on')]:
        times = {mode: {int(r['repeat']): float(r['seconds']) for r in rows
                        if r['case'] == case and r['mode'] == mode}
                 for mode in (baseline, treatment)}
        gains = [1-times[treatment][i]/times[baseline][i] for i in sorted(times[baseline])]
        bootstrap = sorted(statistics.median(rng.choices(gains, k=len(gains)))
                           for _ in range(10000))
        output.append({'case': case, 'baseline': baseline, 'treatment': treatment,
                       'paired_median_gain_percent': 100*statistics.median(gains),
                       'bootstrap_95_percentile_interval_percent': [100*bootstrap[249], 100*bootstrap[9749]],
                       'note': 'Exploratory paired-block bootstrap; assumes independent repeat blocks. VM/frequency effects may violate this assumption.'})
(args.results / 'uncertainty.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output, indent=2))
