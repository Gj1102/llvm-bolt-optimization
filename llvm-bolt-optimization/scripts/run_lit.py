#!/usr/bin/env python3
"""Run the patch's LLVM-style test without requiring the full LLVM test tree."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

project = Path(__file__).resolve().parents[1]
bolt = Path(os.environ.get('BOLT', '/tmp/bolt-small-layout/build/bin/llvm-bolt')).resolve()
source = Path(os.environ.get('LLVM_SOURCE', str(bolt.parents[2] / 'llvm-project')))
work = Path(os.environ.get('WORK', '/tmp/bolt-experiments'))
work.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='lit-', dir=work) as temp:
    suite = Path(temp)
    shutil.copyfile(project / 'tests/local-swap.s', suite / 'small-function-layout.s')
    config = '''import os
import lit.formats
config.name = 'BOLT small-function-layout'
config.test_format = lit.formats.ShTest()
config.suffixes = ['.s']
config.available_features.add('system-linux')
config.test_source_root = os.path.dirname(__file__)
config.test_exec_root = config.test_source_root
config.environment['PATH'] = TOOL_PATH + os.pathsep + os.environ['PATH']
config.substitutions += [('%clang', '/usr/bin/gcc'), ('%cflags', '-no-pie'),
                        ('link_fdata', LINK_FDATA)]
'''
    prefix = 'TOOL_PATH = ' + repr(str(bolt.parent)) + '\n'
    prefix += 'LINK_FDATA = ' + repr('python3 ' + str(source / 'bolt/test/link_fdata.py')) + '\n'
    (suite / 'lit.cfg.py').write_text(prefix + config)
    result = subprocess.run(['python3', str(source / 'llvm/utils/lit/lit.py'), '-v', str(suite)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (work / 'lit.log').write_text(result.stdout)
    print(result.stdout)
    result.check_returncode()
