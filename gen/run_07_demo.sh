#!/bin/sh
# 第7回の実測ログ。会話を伸ばして圧縮し、畳んだ後に昔のことを訊く
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/07_demo_log.txt"
mkdir -p outputs
rm -f code/memory.md
echo "=== \$ python3 07_memory.py --reset" > "$OUT"
python3 code/07_memory.py --reset 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"
echo "== 長期記憶ファイルの中身 ==" | tee -a "$OUT"
cat code/memory.md | tee -a "$OUT"
ollama stop gemma4:e4b || true
echo "done: $OUT"
