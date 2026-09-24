"""第6回: 完成品 — エージェントの足跡を残して読む

使い方:  python3 06_trace.py "今の時刻の分を二乗して"   （走らせて足跡を書く）
         python3 06_trace.py --read                      （足跡を読んで分類する）

道具を足すほど、何が起きたのか分からなくなる。足跡が無いと直せない。
"""
import ast
import collections
import datetime
import json
import operator
import sys
import urllib.request
from pathlib import Path

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_ROUNDS = 6
TRACE_PATH = Path(__file__).resolve().parent / "trace.jsonl"

# ---------- 足跡 ----------

def trace(kind, **fields):
    """1件1行のJSONで書き足す。

    JSON Lines にするのは、途中で落ちても壊れないから。1行が独立しているので、
    書きかけの行を捨てれば残りは読める。表形式や1つの大きなJSONだと、
    最後まで書き終えないと読めない。
    """
    rec = {"t": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], "kind": kind}
    rec.update(fields)
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------- 道具（第3回と同じ2つ） ----------

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def calc(expression):
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        raise ValueError("数値と + - * / ** 以外は使えません")
    return ev(ast.parse(expression, mode="eval").body)


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS_IMPL = {"calc": calc, "now": now}

TOOLS_SPEC = [
    {"type": "function", "function": {
        "name": "calc", "description": "数式を計算して正確な答えを返す電卓",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "例: 12*(3+4)"}},
            "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "now", "description": "現在の日時を返す",
        "parameters": {"type": "object", "properties": {}}}},
]


def chat(messages):
    payload = {"model": MODEL, "messages": messages, "tools": TOOLS_SPEC, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]


def run_agent(user_input):
    trace("start", question=user_input)
    messages = [
        {"role": "system", "content": "あなたは正確さを重視するアシスタントです。"},
        {"role": "user", "content": user_input},
    ]
    for i in range(1, MAX_ROUNDS + 1):
        msg = chat(messages)
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        trace("round", n=i, n_calls=len(calls), said=(msg.get("content") or "")[:60])
        if not calls:
            trace("end", reason="answered", rounds=i)
            return msg["content"]
        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            try:
                result = TOOLS_IMPL[name](**args)
                trace("tool", n=i, name=name, args=args, ok=True, result=str(result)[:60])
            except Exception as e:
                result = f"エラー: {e}"
                trace("tool", n=i, name=name, args=args, ok=False, error=str(e)[:60])
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    trace("end", reason="max_rounds", rounds=MAX_ROUNDS)
    return "（打ち切り：ツール使用が上限に達しました）"


# ---------- 足跡を読む ----------

def classify(records):
    """1回の走行を型に分ける。型を決めておくと、直す場所が決まる。"""
    kinds = collections.Counter(r["kind"] for r in records)
    bad = [r for r in records if r["kind"] == "tool" and not r.get("ok")]
    end = next((r for r in records if r["kind"] == "end"), {})
    if end.get("reason") == "max_rounds":
        return "止まらない（上限で打ち切り）"
    if bad:
        return f"引数か呼び方が違う（失敗した道具呼び出し {len(bad)}件）"
    if kinds["tool"] == 0:
        return "道具を呼ばない（自分で答えた）"
    return f"正常（道具 {kinds['tool']}回 / {end.get('rounds', '?')}周）"


def read_trace():
    if not TRACE_PATH.exists():
        print("足跡がありません")
        return
    runs, cur = [], []
    for line in TRACE_PATH.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["kind"] == "start" and cur:
            runs.append(cur)
            cur = []
        cur.append(rec)
    if cur:
        runs.append(cur)
    for run in runs:
        print(f"--- 質問: {run[0].get('question')}")
        for rec in run[1:]:
            if rec["kind"] == "round":
                print(f"  {rec['t']} 周{rec['n']}: 道具{rec['n_calls']}件"
                      + (f" 「{rec['said']}」" if rec["said"] else ""))
            elif rec["kind"] == "tool":
                mark = "OK" if rec.get("ok") else "NG"
                print(f"  {rec['t']}   {mark} {rec['name']}({rec['args']})"
                      f" → {rec.get('result') or rec.get('error')}")
            elif rec["kind"] == "end":
                print(f"  {rec['t']} 終了: {rec['reason']}")
        print(f"  分類: {classify(run)}")


if __name__ == "__main__":
    if "--read" in sys.argv:
        read_trace()
    else:
        q = sys.argv[1] if len(sys.argv) > 1 else "今の時刻の分を二乗して"
        print("最終回答:", run_agent(q))
