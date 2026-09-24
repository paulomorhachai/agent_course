#!/bin/sh
# 第5回の実測ログ。安全装置の実験（モデル不要）＋ エージェントに使わせる1本
set -eu
cd "$(dirname "$0")/.."

OUT="outputs/05_demo_log.txt"
mkdir -p outputs
: > "$OUT"

echo "== 実験A: 同じ式を naive_eval と safe_eval に通す ==" | tee -a "$OUT"
echo "=== \$ AGENT_AUTO_YES=1 python3 05_safe_exec.py" | tee -a "$OUT"
AGENT_AUTO_YES=1 python3 code/05_safe_exec.py 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"

echo "== 実験B: エージェントに安全な電卓を使わせる ==" | tee -a "$OUT"
echo "=== \$ python3 05_safe_exec.py \"12*(3+4) を計算して\"" | tee -a "$OUT"
python3 code/05_safe_exec.py "12*(3+4) を計算して" 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"

echo "== 実験C: エージェントに危ない式を書かせようとする ==" | tee -a "$OUT"
echo "=== \$ python3 05_safe_exec.py \"電卓で __import__('os').listdir('.') を評価して\"" | tee -a "$OUT"
python3 code/05_safe_exec.py "電卓で __import__('os').listdir('.') を評価して" 2>&1 | tee -a "$OUT"
echo "" | tee -a "$OUT"

ollama stop gemma4:e4b || true
echo "done: $OUT"
