from pathlib import Path
import hashlib
import json
import struct

root = Path('/home/gj/bolt-course-4794')
out = Path('/mnt/d/MyAppreciation/Homework/系统优化/poject-1/llvm-bolt-optimization/results')
sources = {'patched_source': root / 'llvm-project/bolt/lib/Passes/ReorderFunctions.cpp',
           'patched_header': root / 'llvm-project/bolt/include/bolt/Core/BinaryFunction.h'}
proof = json.loads((out / 'source-verification.json').read_text())
hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in sources.items()}
assert all(proof['sha256'][key] == value for key, value in hashes.items())
bolt = root / 'build-gcc/bin/llvm-bolt'
binary_hash = hashlib.sha256(bolt.read_bytes()).hexdigest()
env = json.loads((out / 'environment.json').read_text())
assert env['bolt_sha256'] == binary_hash

def code_sections(binary):
    data = binary.read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01'
    offset = struct.unpack_from('<Q', data, 40)[0]
    entry_size, count, strings = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i*entry_size) for i in range(count)]
    table = data[headers[strings][4]:headers[strings][4]+headers[strings][5]]
    result = {}
    for header in headers:
        if header[2] & 4:
            name = table[header[0]:].split(b'\0', 1)[0].decode()
            content = data[header[4]:header[4]+header[5]]
            result[name] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    return result

sections = {case: {mode: code_sections(root / 'experiments' / case / mode)
                   for mode in ('original', 'off', 'on', 'cdsort', 'cdsort-on')}
            for case in ('correlated', 'dispersed', 'ordinary')}
cache = {}
keys = {'CMAKE_BUILD_TYPE', 'CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'LLVM_TARGETS_TO_BUILD',
        'LLVM_ENABLE_PROJECTS', 'LLVM_ENABLE_ASSERTIONS', 'LLVM_FORCE_VC_REVISION',
        'LLVM_USE_LINKER', 'LLVM_ENABLE_ZLIB', 'LLVM_ENABLE_ZSTD'}
for line in (root / 'build-gcc/CMakeCache.txt').read_text().splitlines():
    if '=' in line and ':' in line and line.split(':', 1)[0] in keys:
        cache[line.split(':', 1)[0]] = line.split('=', 1)[1]
result = {'compiled_source_hashes': hashes, 'bolt_sha256': binary_hash,
          'matches_profile_collection_binary': True, 'build_configuration': cache,
          'executable_sections': sections,
          'identical_code_sections': {case: {'off_vs_on': sections[case]['off'] == sections[case]['on'],
                                           'cdsort_vs_cdsort_on': sections[case]['cdsort'] == sections[case]['cdsort-on']}
                                      for case in sections}}
(out / 'native-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result['identical_code_sections'], indent=2))
