#!/usr/bin/env python3
"""Generate deterministic C workloads; no generated binaries enter the repo."""
from pathlib import Path
import argparse
import random

HEADER = '''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define FN __attribute__((noinline, noclone))
'''


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    groups, stages = 64, 32
    names = [(g, s) for g in range(groups) for s in range(stages)]
    text = HEADER + ''.join(f'FN uint64_t f{g}_{s}(uint64_t);\n' for g, s in names)
    random.Random(17).shuffle(names)
    for g, s in names:
        body = f'x = (x ^ {g * stages + s + 1}ULL) * 33ULL;'
        if s + 1 < stages:
            body += f'x = f{g}_{s+1}(x);'
        text += f'FN uint64_t f{g}_{s}(uint64_t x) {{ {body} return x + 7; }}\n'
    text += 'int main(int argc, char **argv) {\n'
    text += 'unsigned long n = argc > 1 ? strtoul(argv[1], 0, 10) : 100000; uint64_t x = 1;\n'
    text += 'for (unsigned long i = 0; i < n; ++i) {\n'
    text += ''.join(f'x = f{g}_0(x);\n' for g in range(groups))
    text += '} printf("%llu\\n", (unsigned long long)x); return 0; }\n'
    (out / 'correlated.c').write_text(text)

    text = HEADER
    for i in range(512):
        text += f'FN uint64_t leaf{i}(uint64_t x) {{ return (x ^ {i+1}ULL) * 33ULL + 7; }}\n'
    text += 'FN uint64_t dispatch(uint64_t x, unsigned k) { switch(k) {\n'
    for i in range(512):
        text += f'case {i}: return leaf{i}(x);\n'
    text += '} return x; }\n'
    text += '''int main(int argc, char **argv) {
unsigned long n = argc > 1 ? strtoul(argv[1], 0, 10) : 100000;
uint64_t x = 1; unsigned r = 12345;
for (unsigned long i = 0; i < n * 64; ++i) {
r ^= r << 13; r ^= r >> 17; r ^= r << 5; x = dispatch(x, r & 511);
} printf("%llu\\n", (unsigned long long)x); return 0; }
'''
    (out / 'dispersed.c').write_text(text)
    (out / 'ordinary.c').write_text((Path(__file__).parent / 'ordinary.c').read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    generate(parser.parse_args().output)
