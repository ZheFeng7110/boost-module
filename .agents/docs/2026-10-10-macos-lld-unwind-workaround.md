# macOS LLVM exception unwinding workaround

LLVM 22.1.8's `ld64.lld` can emit duplicate `__unwind_info` entries when a
zero-length `__TEXT,__text` input section precedes a function. The zero entry
shadows the real entry, causing libunwind to stop during phase one and making
all handlers unreachable. This affected the include-only
`program_options_invalid_value` test in group A.

The macOS target uses Apple's `/usr/bin/ld` via
`-fuse-ld=/usr/bin/ld`. `ld64.lld` ignores `-no_compact_unwind`; the same-input
relink with that flag still aborts (run 38029410684). Linux and Windows retain
their existing link flags. Both the module consumer and include-only consumer
now exercise the invalid-value exception path on macOS.

Evidence so far: LLDB shows `__cxa_throw` calling `failed_throw` directly for
`invalid_option_value`, while the preceding `bad_lexical_cast` is caught.
Omitting the preceding library build does not change the failure. An Apple
clang standalone build passes. This is consistent with the layout-dependent
LLD defect described in [LLVM issue 216154](https://github.com/llvm/llvm-project/issues/216154);
run 38030544249 confirms the same-object linker comparison: LLD aborts with
SIGABRT, while Apple's linker produces a passing executable. The LLD binary
contains duplicate second-level unwind entries, including zero encodings at
the same address as real encodings. A minimal data-only TU followed by a
throwing function reproduces duplicate entries using the installed LLVM
22.1.8 toolchain cross-linking Mach-O on Linux.

Use `[target.macos.build]`, as documented by mcpp; `macosx` is the registry
artifact spelling and does not select this target's build settings. The
temporary diagnostic workflow and scripts have been removed. The complete
Tests matrix passed 15/15 jobs, including the restored module test and all
examples.
