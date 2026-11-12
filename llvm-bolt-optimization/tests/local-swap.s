# REQUIRES: system-linux
# RUN: llvm-mc -filetype=obj -triple x86_64-unknown-linux %s -o %t.o
# RUN: link_fdata %s %t.o %t.fdata
# RUN: %clang %cflags %t.o -o %t.exe -Wl,-q
# RUN: llvm-bolt %t.exe --data=%t.fdata --reorder-functions=none \
# RUN:   --reorder-blocks=none --split-functions=0 --align-functions=1 \
# RUN:   --small-function-layout --generate-function-order=%t.order \
# RUN:   -o %t.good 2>&1 | FileCheck %s --check-prefix=GOOD
# RUN: FileCheck %s --input-file=%t.order --check-prefix=ORDER
# RUN: link_fdata %s %t.o %t.bad.fdata VETO
# RUN: llvm-bolt %t.exe --data=%t.bad.fdata --reorder-functions=none \
# RUN:   --reorder-blocks=none --split-functions=0 --align-functions=1 \
# RUN:   --small-function-layout -o %t.bad 2>&1 | FileCheck %s --check-prefix=KEEP
# RUN: link_fdata %s %t.o %t.tie.fdata TIEPROFILE
# RUN: llvm-bolt %t.exe --data=%t.tie.fdata --reorder-functions=none \
# RUN:   --reorder-blocks=none --split-functions=0 --align-functions=1 \
# RUN:   --small-function-layout -o %t.tie 2>&1 | FileCheck %s --check-prefix=KEEP
# RUN: llvm-bolt %t.exe --small-function-layout -o %t.nodata 2>&1 \
# RUN:   | FileCheck %s --check-prefix=NODATA
# GOOD: small-function-layout: swaps=1
# KEEP: small-function-layout: swaps=0
# NODATA: small-function-layout: skipped (no valid call edges)
# ORDER: main
# ORDER-NEXT: small_b
# ORDER-NEXT: small_a
# ORDER-NEXT: large_c
# FDATA: 0 [unknown] 0 1 main 0 0 1000
# FDATA: 1 main 4 1 small_a 0 0 1000
# FDATA: 1 main b 1 main d 0 100
# FDATA: 1 main b 1 main 12 0 900
# FDATA: 1 main d 1 small_b 0 0 100
# FDATA: 1 small_a 2 1 small_a 4 0 100
# FDATA: 1 small_a 2 1 small_a 11 0 900
# FDATA: 1 small_a 8 1 large_c 0 0 100
# VETO: 0 [unknown] 0 1 main 0 0 10000
# VETO: 1 main 4 1 small_a 0 0 10000
# VETO: 1 main b 1 main d 0 100
# VETO: 1 main b 1 main 12 0 9900
# VETO: 1 main d 1 small_b 0 0 100
# VETO: 1 small_a 2 1 small_a 4 0 100
# VETO: 1 small_a 2 1 small_a 11 0 9900
# VETO: 1 small_a 8 1 large_c 0 0 100
# TIEPROFILE: 0 [unknown] 0 1 main 0 0 1900
# TIEPROFILE: 1 main 4 1 small_a 0 0 1900
# TIEPROFILE: 1 main b 1 main d 0 100
# TIEPROFILE: 1 main b 1 main 12 0 1800
# TIEPROFILE: 1 main d 1 small_b 0 0 100
# TIEPROFILE: 1 small_a 2 1 small_a 4 0 100
# TIEPROFILE: 1 small_a 2 1 small_a 11 0 1800
# TIEPROFILE: 1 small_a 8 1 large_c 0 0 100

# A and B are adjacent small functions. main and C exceed 128 bytes.
# Moving A right shortens A->C but lengthens main->A. The regression runner
# varies main->A's weight to exercise acceptance, ties, and external-edge veto.
.text
.globl main
.type main,@function
main:
  .cfi_startproc
  subq $8, %rsp
  .cfi_adjust_cfa_offset 8
  call small_a
  testl %edi, %edi
  je .Lskip_b
  call small_b
.Lskip_b:
  .rept 80
  addl $1, %eax
  .endr
  xorl %eax, %eax
  addq $8, %rsp
  .cfi_adjust_cfa_offset -8
  ret
  .cfi_endproc
.size main, .-main

.globl small_a
.type small_a,@function
small_a:
  .cfi_startproc
  testl %edi, %edi
  je .Lskip_c
  subq $8, %rsp
  .cfi_adjust_cfa_offset 8
  call large_c
  addq $8, %rsp
  .cfi_adjust_cfa_offset -8
.Lskip_c:
  ret
  .cfi_endproc
.size small_a, .-small_a

.globl small_b
.type small_b,@function
small_b:
  .cfi_startproc
  ret
  .cfi_endproc
.size small_b, .-small_b

.globl large_c
.type large_c,@function
large_c:
  .cfi_startproc
  .rept 80
  addl $1, %eax
  .endr
  ret
  .cfi_endproc
.size large_c, .-large_c
.section .note.GNU-stack,"",@progbits
