# macOS LLVM exception unwinding workaround

LLVM 22.1.8's `ld64.lld` can emit duplicate `__unwind_info` entries when a
zero-length `__TEXT,__text` input section precedes a function. The zero entry
shadows the real entry, causing libunwind to stop during phase one and making
all handlers unreachable. This affected the include-only
`program_options_invalid_value` test in group A.

The macOS target now passes `-Wl,-no_compact_unwind`, preserving DWARF EH
tables instead of the affected compact-unwind index. Linux and Windows retain
their existing link flags.
