#!/usr/bin/env sh
# ============================================================================
#  rpa.sh - DSH launcher for rpa-ipa-analyzer (Linux / macOS / Git Bash / WSL)
#
#  Usage:
#    "<SK>/scripts/rpa.sh" extract  "<project>" --force
#    "<SK>/scripts/rpa.sh" skeleton "<project>" --depth standard
#
#  Same contract as rpa.cmd: resolve an interpreter every call (DSH uses a fresh
#  shell per command), accept only Python >= 3.8, and always pass -X utf8 so
#  Chinese node names are not mangled on the way into the agent's context.
#
#  Interpreter search order:
#    $RPA_IPA_PYTHON -> .venv-py38 | .venv | venv under $PWD and its parents
#                    -> python3 | python on PATH
# ============================================================================
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCRIPT="$HERE/extract_nodes.py"

if [ ! -f "$SCRIPT" ]; then
  echo "[rpa.sh] not found: $SCRIPT" >&2
  exit 2
fi

ok_python() {
  [ -n "${1:-}" ] || return 1
  command -v "$1" >/dev/null 2>&1 || [ -x "$1" ] || return 1
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 3)' >/dev/null 2>&1
}

PY=""

# 1. explicit override
if ok_python "${RPA_IPA_PYTHON:-}"; then
  PY="$RPA_IPA_PYTHON"
fi

# 2. a venv at $PWD or in an ancestor directory
if [ -z "$PY" ]; then
  d=$(pwd)
  i=0
  while [ "$i" -lt 6 ]; do
    for cand in \
      "$d/.venv-py38/bin/python" "$d/.venv-py38/Scripts/python.exe" \
      "$d/.venv/bin/python"      "$d/.venv/Scripts/python.exe" \
      "$d/venv/bin/python"       "$d/venv/Scripts/python.exe"
    do
      if ok_python "$cand"; then PY="$cand"; break; fi
    done
    [ -n "$PY" ] && break
    parent=$(dirname -- "$d")
    [ "$parent" = "$d" ] && break
    d="$parent"
    i=$((i + 1))
  done
fi

# 3. PATH
if [ -z "$PY" ]; then
  for cand in python3 python; do
    if ok_python "$cand"; then PY="$cand"; break; fi
  done
fi

if [ -z "$PY" ]; then
  echo "[rpa.sh] no Python 3.8+ interpreter found." >&2
  echo "  Fix: export RPA_IPA_PYTHON=/path/to/python3" >&2
  exit 127
fi

exec "$PY" -X utf8 "$SCRIPT" "$@"
