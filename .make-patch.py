from pathlib import Path
import difflib

base = Path(__file__).resolve().parent
original = (base / '.reorder-original.cpp').read_text(encoding='utf-8')
changed = original.replace('#include <fstream>', '#include <cmath>\n#include <fstream>')
changed = changed.replace('extern cl::opt<unsigned> Verbosity;', 'extern cl::opt<unsigned> Verbosity;\nextern cl::opt<bool> HotFunctionsAtEnd;\nextern cl::opt<bool> HotText;\nextern bool isHotTextMover(const bolt::BinaryFunction &Function);')
changed = changed.replace('static cl::opt<bool> ReorderFunctionsUseHotSize(', '''static cl::opt<bool> SmallFunctionLayout(
    "small-function-layout",
    cl::desc("refine small-function order using weighted call distance"),
    cl::init(false), cl::cat(BoltOptCategory));

static cl::opt<bool> ReorderFunctionsUseHotSize(''')
anchor = 'Error ReorderFunctions::runOnFunctions(BinaryContext &BC) {'
changed = changed.replace(anchor, (base / '.small-layout.inc').read_text(encoding='utf-8') + anchor)
anchor = '  BC.HasFinalizedFunctionOrder = true;'
changed = changed.replace(anchor, '  if (opts::SmallFunctionLayout)\n    refineSmallFunctionLayout(BC);\n\n' + anchor)
assert changed != original and changed.count('refineSmallFunctionLayout(BC);') == 1
path = 'bolt/lib/Passes/ReorderFunctions.cpp'
patch = 'diff --git a/' + path + ' b/' + path + '\n'
patch += ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True), 'a/' + path, 'b/' + path))
test_path = 'bolt/test/X86/small-function-layout.s'
test_text = (base / 'llvm-bolt-optimization/tests/local-swap.s').read_text(encoding='utf-8')
patch += 'diff --git a/' + test_path + ' b/' + test_path + '\nnew file mode 100644\n'
patch += ''.join(difflib.unified_diff([], test_text.splitlines(True), '/dev/null', 'b/' + test_path))
header_path = 'bolt/include/bolt/Core/BinaryFunction.h'
header = (base / '.llvm-source' / header_path).read_text(encoding='utf-8')
anchor = '  /// Return offset of the function body in the binary file.'
updated_header = header.replace(anchor, '''  /// Exchange two already assigned streaming order indices.
  void swapIndex(BinaryFunction &Other) {
    assert(hasValidIndex() && Other.hasValidIndex());
    std::swap(Index, Other.Index);
  }

''' + anchor)
assert header != updated_header
patch += 'diff --git a/' + header_path + ' b/' + header_path + '\n'
patch += ''.join(difflib.unified_diff(header.splitlines(True), updated_header.splitlines(True), 'a/' + header_path, 'b/' + header_path))
(base / '.BinaryFunction-modified.h').write_text(updated_header, encoding='utf-8', newline='\n')
(base / 'llvm-bolt-optimization/patches/small-function-layout.patch').write_text(patch, encoding='utf-8', newline='\n')
(base / '.reorder-modified.cpp').write_text(changed, encoding='utf-8', newline='\n')
print('Patch written:', len(patch.splitlines()), 'lines')
