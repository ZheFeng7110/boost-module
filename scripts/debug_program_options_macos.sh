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

echo "=== relink with DWARF unwind metadata ==="
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
        command = (shlex.split(variables['cxx']) + objects +
                   ['-o', 'bin/program_options_dwarf'] +
                   shlex.split(variables['ldflags']) + shlex.split(unit_flags) +
                   ['-Wl,-no_compact_unwind'])
        subprocess.run(command, cwd=ninja.parent, check=True)
        result = subprocess.run(['bin/program_options_dwarf'], cwd=ninja.parent)
        print('DWARF unwind result:', result.returncode, flush=True)
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
