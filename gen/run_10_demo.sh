#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/10_demo_log.txt"
mkdir -p outputs
echo "=== \$ python3 10_eval.py" > "$OUT"
python3 code/10_eval.py 2>&1 | tee -a "$OUT"
ollama stop gemma4:e4b || true
echo "done: $OUT"
