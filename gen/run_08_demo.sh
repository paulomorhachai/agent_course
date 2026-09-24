#!/bin/sh
# 第8回の実測ログ。埋め込み検索の実験と、道具として使わせる1本
set -eu
cd "$(dirname "$0")/.."
OUT="outputs/08_demo_log.txt"
mkdir -p outputs
echo "== 実験A: 意味で探す ==" > "$OUT"
echo "=== \$ python3 08_rag.py" | tee -a "$OUT"
python3 code/08_rag.py 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"
echo "== 実験B: 道具として使わせる ==" | tee -a "$OUT"
echo "=== \$ python3 08_rag.py \"私はどこに住んでいますか？\"" | tee -a "$OUT"
python3 code/08_rag.py "私はどこに住んでいますか？" 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"
ollama stop gemma4:e4b || true
ollama stop bge-m3 || true
echo "done: $OUT"
