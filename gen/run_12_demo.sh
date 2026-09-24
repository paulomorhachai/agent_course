#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/12_demo_log.txt"
mkdir -p outputs
echo "=== \$ python3 12_watch.py --demo" > "$OUT"
python3 code/12_watch.py --demo 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"
echo "== 日報ファイルの中身 ==" | tee -a "$OUT"
cat code/watch_report.md | tee -a "$OUT"
ollama stop gemma4:e4b || true
echo "done: $OUT"
