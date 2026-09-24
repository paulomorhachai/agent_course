"""第9回: 完成品 — 考えてから動く、そして分ける

使い方:  python3 09_plan.py            （素のループ／ReAct／計画分離を並べて比べる）

手数が2手までなら、その場の判断で足りた。増えると迷子になる。
迷子の直し方は2つある。一手ごとに考えさせる（ReAct）か、先に段取りを立てさせる（計画分離）か。
"""
import ast
import datetime
import json
import operator
import re
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_ROUNDS = 8

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


def chat(messages, tools=TOOLS_SPEC):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]


def _loop(messages, label):
    """道具ループの共通部分。周回数と道具の呼び出し列を返す。"""
    used = []
    for i in range(1, MAX_ROUNDS + 1):
        msg = chat(messages)
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content", ""), used, i
        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            try:
                result = TOOLS_IMPL[name](**args)
            except Exception as e:
                result = f"エラー: {e}"
            used.append(f"{name}({args})")
            print(f"  [{label}] {name}({args}) → {str(result)[:40]}")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "（打ち切り）", used, MAX_ROUNDS


# ---------- 型1: 素のループ（第3回のまま） ----------

def plain(question):
    return _loop([
        {"role": "system", "content": "あなたは正確さを重視するアシスタントです。"},
        {"role": "user", "content": question}], "素")


# ---------- 型2: ReAct — 一手ごとに考えさせる ----------

REACT_SYSTEM = """あなたは正確さを重視するアシスタントです。
道具を呼ぶ前に、必ず1文で「いま何のためにどの道具を使うか」を書いてください。
書いてから呼びます。書かずに呼ばないでください。"""


def react_step(question):
    """考えを口に出させてから動かす。出させること自体が手綱になる。"""
    return _loop([
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user", "content": question}], "ReAct")


# ---------- 型3: 計画係と実行係に分ける ----------

def plan(question):
    """道具を持たせずに段取りだけ書かせる。持たせないので手が出ない。"""
    msg = chat([
        {"role": "system", "content":
         "あなたは段取りを立てる係です。道具は使えません。"
         "使える道具は calc（電卓）と now（現在時刻）の2つです。"
         "解くための手順を、1行に1手ずつ、3手以内の番号付きで書いてください。"},
        {"role": "user", "content": question},
    ], tools=None)
    steps = [ln.strip() for ln in msg["content"].splitlines()
             if re.match(r"^\s*\d[\.\)]", ln)]
    return steps or [msg["content"].strip()]


def execute(question, steps):
    """段取りを渡して実行させる。考える仕事は済んでいる。"""
    plan_text = "\n".join(steps)
    return _loop([
        {"role": "system", "content":
         "あなたは実行係です。次の段取りに従って道具を呼び、最後に答えを出してください。\n"
         + plan_text},
        {"role": "user", "content": question}], "実行")


QUESTION = "今の時刻の「時」と「分」を足して、その結果を3乗するといくつ？"


def main():
    print(f"問い: {QUESTION}\n")

    print("--- 型1: 素のループ")
    ans, used, rounds = plain(QUESTION)
    print(f"  答え: {ans[:80]}")
    print(f"  道具 {len(used)}回 / {rounds}周\n")

    print("--- 型2: ReAct（一手ごとに考えさせる）")
    ans, used, rounds = react_step(QUESTION)
    print(f"  答え: {ans[:80]}")
    print(f"  道具 {len(used)}回 / {rounds}周\n")

    print("--- 型3: 計画係と実行係に分ける")
    steps = plan(QUESTION)
    print("  立てた段取り:")
    for s in steps:
        print(f"    {s}")
    ans, used, rounds = execute(QUESTION, steps)
    print(f"  答え: {ans[:80]}")
    print(f"  道具 {len(used)}回 / {rounds}周")


if __name__ == "__main__":
    main()
