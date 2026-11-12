from pathlib import Path
import shlex
import subprocess

build = Path('/home/gj/bolt-course-4794/build-gcc')
results = Path('/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization/results')
target = 'tools/bolt/lib/Passes/CMakeFiles/LLVMBOLTPasses.dir/ReorderFunctions.cpp.o'
command = subprocess.check_output(['ninja', '-t', 'commands', target], cwd=build, text=True).splitlines()[-1]
argv = shlex.split(command)
for flag, value in [('-o', str(build / 'reorder-compile-check.o')),
                    ('-MF', str(build / 'reorder-compile-check.o.d')),
                    ('-MT', 'reorder-compile-check.o')]:
    argv[argv.index(flag) + 1] = value
with (results / 'compile-check.log').open('w') as out:
    out.write(command + '\n')
    out.flush()
    result = subprocess.run(argv, cwd=build, stdout=out, stderr=subprocess.STDOUT)
    out.write('Exit status: ' + str(result.returncode) + '\n')
raise SystemExit(result.returncode)
