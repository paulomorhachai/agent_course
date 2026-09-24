#!/bin/sh
# 第6回の実測ログ。3種類の質問を走らせて足跡を書き、最後に読んで分類する
set -eu
cd "$(dirname "$0")/.."

OUT="outputs/06_demo_log.txt"
mkdir -p outputs
rm -f code/trace.jsonl
: > "$OUT"

run() {
  echo "=== \$ python3 06_trace.py \"$1\"" | tee -a "$OUT"
  python3 code/06_trace.py "$1" 2>&1 | tee -a "$OUT"
  echo "" | tee -a "$OUT"
}

echo "== 走らせる（3本） ==" | tee -a "$OUT"
run "今の時刻の分を二乗して"
run "こんにちは"
run "1から100までの素数を全部足して"

echo "== 足跡を読む ==" | tee -a "$OUT"
echo "=== \$ python3 06_trace.py --read" | tee -a "$OUT"
python3 code/06_trace.py --read 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"

echo "== 足跡ファイルの生（先頭6行） ==" | tee -a "$OUT"
head -6 code/trace.jsonl | tee -a "$OUT"

ollama stop gemma4:e4b || true
echo "done: $OUT"
