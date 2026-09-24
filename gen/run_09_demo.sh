#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/09_demo_log.txt"
mkdir -p outputs
echo "=== \$ python3 09_plan.py" > "$OUT"
python3 code/09_plan.py 2>&1 | tee -a "$OUT"
ollama stop gemma4:e4b || true
echo "done: $OUT"
