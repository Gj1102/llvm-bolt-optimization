#!/usr/bin/env python3
"""Stage the installed GCC/binutils development files for an offline runtime image.

The runtime base must supply a glibc at least as new as the packaging host.
Do not copy the host's glibc over the container's glibc.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess

p=argparse.ArgumentParser()
p.add_argument('destination',type=Path)
args=p.parse_args()
packages=['gcc','g++','cpp','gcc-13','g++-13','cpp-13','gcc-13-base','binutils',
          'binutils-common','binutils-x86-64-linux-gnu','libc6-dev',
          'libgcc-13-dev','libstdc++-13-dev','linux-libc-dev',
          'python3','python3-minimal','python3.12','python3.12-minimal',
          'libpython3.12-stdlib','libpython3.12-minimal']
paths=subprocess.check_output(['dpkg-query','-L',*packages],text=True).splitlines()
seen=set()
elf=[]
def stage(source):
    source=Path(source)
    if str(source) in seen or not source.exists(): return
    seen.add(str(source))
    if source.is_dir(): return
    relative=str(source).lstrip('/')
    if relative.startswith('lib/'): relative='usr/'+relative
    target=args.destination/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if source.is_symlink():
        link=source.readlink()
        if not target.exists() and not target.is_symlink(): target.symlink_to(link)
        stage(source.parent/link if not link.is_absolute() else link)
    else:
        shutil.copy2(source,target)
        with source.open('rb') as f:
            if f.read(4)==b'\x7fELF': elf.append(source)
for path in paths:
    if path.startswith('/'): stage(path)
# Ubuntu splits compiler executables into architecture-specific packages.
# Include the compiler's private directory, including cc1/cc1plus/collect2.
for directory in ('/usr/lib/gcc/x86_64-linux-gnu/13', '/usr/libexec/gcc/x86_64-linux-gnu/13'):
    for path in Path(directory).rglob('*'):
        stage(path)
index=0
while index<len(elf):
    binary=elf[index]; index+=1
    output=subprocess.run(['ldd',str(binary)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True).stdout
    for path in re.findall(r'(/[^\s()]+)',output):
        name=Path(path).name
        if name.startswith('ld-linux') or name in {'libc.so.6','libm.so.6','libpthread.so.0',
                'libdl.so.2','librt.so.1','libresolv.so.2','libutil.so.1','libanl.so.1'}:
            continue
        stage(path)
versions=subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version}\n',*packages],text=True)
(args.destination/'toolchain-packages.txt').write_text(versions)
print('Staged',len(seen),'toolchain paths')
