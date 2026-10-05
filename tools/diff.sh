#!/usr/bin/env bash
# Show the solution to exercise N: the code changes between exercise N and exercise N+1.
# The diff also contains the scaffolding for exercise N+1. Usage: tools/diff.sh 3
set -euo pipefail
shopt -s nullglob

cd "$(dirname "$0")/.."
n=$((10#${1:?usage: tools/diff.sh N}))
from=("$(printf '%02d' "$n")"-*/)
to=("$(printf '%02d' "$((n + 1))")"-*/)
if [[ ${#from[@]} -eq 0 || ${#to[@]} -eq 0 ]]; then
  echo "No exercise $n, or no exercise after it" >&2
  exit 1
fi

diff -ruN --color=auto --exclude=__pycache__ --exclude=README.md "${from[0]}" "${to[0]}" || true
