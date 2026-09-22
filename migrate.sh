#!/usr/bin/env bash
# migrate.sh — move existing ~/bubba/*.txt personas into the new layout
#
# Before:
#   ~/bubba/dave.txt
#   ~/bubba/bubba_glasgow.txt
#   ...
#
# After:
#   ~/bubba/dave/system.txt
#   ~/bubba/dave/diary.md
#   ~/bubba/dave/config.json
#   ~/bubba/bubba_glasgow/system.txt
#   ...
#
# Idempotent — safe to run multiple times.

set -euo pipefail

BASE="$HOME/bubba"
DEFAULT_CONFIG='{
  "model": "llama3.2:3b",
  "temperature": 0.85,
  "num_ctx": 4096,
  "history_turns": 20
}'

if [ ! -d "$BASE" ]; then
    echo "No $BASE directory. Nothing to migrate."
    exit 0
fi

cd "$BASE"

for txt in *.txt; do
    # No .txt files? Shell expands to the literal — skip.
    [ "$txt" = "*.txt" ] && continue

    name="${txt%.txt}"
    dir="$BASE/$name"

    if [ -e "$dir" ]; then
        echo "skip: $name (directory already exists)"
        continue
    fi

    echo "migrating: $txt  ->  $name/"
    mkdir -p "$dir"
    mv "$txt" "$dir/system.txt"
    : > "$dir/diary.md"
    echo "$DEFAULT_CONFIG" > "$dir/config.json"
done

# CRIB.md and README.md aren't personas — leave them alone.
echo
echo "Done. Current layout:"
ls -la "$BASE"
