#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/11_demo_log.txt"
mkdir -p outputs
echo "=== \$ python3 11_multi.py" > "$OUT"
python3 code/11_multi.py 2>&1 | tee -a "$OUT"
ollama stop gemma4:e4b || true
echo "done: $OUT"
