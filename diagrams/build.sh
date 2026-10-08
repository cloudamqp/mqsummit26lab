#!/bin/sh
# Renders every diagram in this folder to SVG. Needs d2 (https://d2lang.com) on the PATH.
set -e
cd "$(dirname "$0")"
for f in [0-9]*.d2; do
    d2 "$f" "${f%.d2}.svg"
done
