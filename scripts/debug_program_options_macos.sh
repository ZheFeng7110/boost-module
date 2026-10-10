#!/usr/bin/env bash
set -uo pipefail

# Temporary CI diagnostics: compare the linked mcpp test with a plain build.
test_bin=$(find target -type f -name program_options_invalid_value -perm -111 | head -n 1)
if [[ -n "$test_bin" ]]; then
  echo "=== mcpp test dependencies ==="
  otool -L "$test_bin"
  echo "=== exception backtrace ==="
  lldb --batch -k bt -o 'breakpoint set -n __cxa_throw' -o run -o bt \
    -o continue -o bt -o continue -o bt -- "$test_bin" || true
  echo "=== terminate backtrace ==="
  lldb --batch -k bt -o 'breakpoint set -n __cxa_call_terminate' -o run \
    -o bt -- "$test_bin" || true
fi

echo "=== inspect unwind metadata and compare linkers ==="
python3 - <<'PY'
import pathlib
import shlex
import subprocess

for ninja in pathlib.Path('target').rglob('build.ninja'):
    lines = ninja.read_text().splitlines()
    variables = {}
    for line in lines:
        if not line.startswith(' ') and ' = ' in line:
            key, value = line.split('=', 1)
            variables[key.strip()] = value.strip()
    for i, line in enumerate(lines):
        if not line.startswith('build bin/program_options_invalid_value : cxx_link '):
            continue
        objects = shlex.split(line.split(': cxx_link ', 1)[1].split(' | ', 1)[0])
        unit_flags = lines[i + 1].split('=', 1)[1].strip()
        compiler = shlex.split(variables['cxx'])
        flags = shlex.split(variables['ldflags']) + shlex.split(unit_flags)
        flags = [f for f in flags if not f.startswith('-fuse-ld=')]
        for name, linker in [('lld', '-fuse-ld=lld'), ('apple', '-fuse-ld=/usr/bin/ld')]:
            output = 'bin/program_options_' + name
            command = compiler + objects + ['-o', output] + flags + [linker]
            subprocess.run(command, cwd=ninja.parent, check=True)
            result = subprocess.run([output], cwd=ninja.parent)
            print(name, 'linker result:', result.returncode, flush=True)
            objdump = pathlib.Path(compiler[0]).parent / 'llvm-objdump'
            dump = subprocess.check_output([str(objdump), '--unwind-info', output],
                                           cwd=ninja.parent, text=True)
            entries = [l.strip() for l in dump.splitlines() if 'function offset=' in l]
            previous = None
            duplicates = 0
            for entry in entries:
                address = entry.split('function offset=', 1)[1].split(',', 1)[0]
                if previous and address == previous[0]:
                    duplicates += 1
                    if duplicates <= 10:
                        print('duplicate unwind:', previous[1], entry, flush=True)
                previous = address, entry
            print(name, 'duplicate unwind entry count:', duplicates, flush=True)
PY

echo "=== generated compile/link rules ==="
find target -name build.ninja -exec sh -c \
  'grep -A 5 -B 2 program_options_invalid_value "$1"' sh {} \;

echo "=== standalone Apple clang build ==="
/usr/bin/clang++ -std=c++23 -g -DBOOST_ALL_NO_LIB -Ideps/boost \
  tests/program_options_invalid_value.cpp deps/boost/libs/program_options/src/*.cpp \
  -o /tmp/program_options_apple && /tmp/program_options_apple
echo "Apple clang result: $?"

echo "=== installed LLVM clang paths ==="
find "$HOME/.mcpp" -type f -name clang++ -print
