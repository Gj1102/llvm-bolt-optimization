#!/usr/bin/env bash
set -u
grep -Rn 'new ReorderFunctions\|make_unique<ReorderFunctions\|registerPass.*ReorderFunctions' ~/llvm-project/bolt/lib
sed -n '130,210p' ~/llvm-project/bolt/lib/Core/BinaryFunctionCallGraph.cpp
grep -n -E 'compareBinaryFunctionByIndex|isSimple|getAlignment|isSplit' ~/llvm-project/bolt/include/bolt/Core/BinaryFunction.h
grep -n -E 'reorder-functions|ReorderFunctions' ~/llvm-project/bolt/lib/Rewrite/RewriteInstance.cpp
