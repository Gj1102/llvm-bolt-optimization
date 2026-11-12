from pathlib import Path
import json
import shutil
import subprocess

root=Path(__file__).resolve().parent
project=root/'llvm-bolt-optimization'
results=project/'results'
confirmation=json.loads((results/'confirmation64/uncertainty.json').read_text())
target=next(x for x in confirmation if x['case']=='correlated' and x['baseline']=='off')
assert target['bootstrap_95_percentile_interval_percent'][0]>0, 'Independent confirmation does not support promotion'
archive=results/'eight-rounds'
archive.mkdir(exist_ok=False)
for name in ['RESULTS.md','summary.json','timings.csv','environment.json','uncertainty.json',
             'source-verification.json','native-verification.json','validation.json']:
    shutil.copy2(results/name,archive/name)
shutil.copy2(project/'patches/small-function-layout.patch',archive/'small-function-layout.patch')
helper=root/'.small-layout.inc'
text=helper.read_text(); assert text.count('Round < 8')==1
helper.write_text(text.replace('Round < 8','Round < 64'),newline='\n')
subprocess.run(['python',str(root/'.make-patch.py')],check=True)
for path in (results/'candidate64').rglob('*'):
    if path.is_file():
        destination=results/path.relative_to(results/'candidate64')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination)
print('Promoted 64-round refinement; preserved eight-round measurements and patch')
