from pathlib import Path
p = Path('llvm-bolt-optimization/tests/local-swap.s')
text = p.read_text(encoding='utf-8')
start, end = text.index('# FDATA:'), text.index('# A and B are adjacent')
lines = []
for prefix, weight in [('FDATA', 1000), ('VETO', 10000), ('TIEPROFILE', 1900)]:
    records = [f'0 [unknown] 0 1 main 0 0 {weight}',
               f'1 main 4 1 small_a 0 0 {weight}',
               '1 main b 1 main d 0 100',
               f'1 main b 1 main 12 0 {weight-100}',
               '1 main d 1 small_b 0 0 100',
               '1 small_a 2 1 small_a 4 0 100',
               f'1 small_a 2 1 small_a 11 0 {weight-100}',
               '1 small_a 8 1 large_c 0 0 100']
    lines += [f'# {prefix}: {record}' for record in records]
p.write_text(text[:start] + '\n'.join(lines) + '\n\n' + text[end:], encoding='utf-8', newline='\n')
