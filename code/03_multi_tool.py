"""第3回: 完成品 — 複数の道具を自分で選んで使うエージェント

使い方:  python3 03_multi_tool.py "今の時刻の「分」を二乗するといくつ？"
"""
import ast
import datetime
import json
import operator
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_ROUNDS = 8   # 暴走防止の安全弁（第1号）

# ---------- 道具の実装（厨房） ----------

OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
}

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

# ---------- 道具の説明書（メニュー） ----------

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "calc",
            "description": "数式を計算して正確な答えを返す電卓。計算が必要なときは必ず使うこと",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Python 形式の数式。例: 12*(3+4), 2**10",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "now",
            "description": "現在の日時を返す。今日の日付や今の時刻が必要なときに使う",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# ---------- エージェント本体（第2回と同じ心臓部＋安全弁） ----------

def chat(messages):
    payload = {"model": MODEL, "messages": messages,
               "tools": TOOLS_SPEC, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]

def run_agent(user_input):
    messages = [
        {"role": "system", "content": "あなたは正確さを重視するアシスタントです。"},
        {"role": "user", "content": user_input},
    ]
    for _ in range(MAX_ROUNDS):
        msg = chat(messages)
        messages.append(msg)
        if not msg.get("tool_calls"):
            return msg["content"]
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            print(f"[ツール実行] {name}({args})")
            try:
                result = TOOLS_IMPL[name](**args)
            except Exception as e:
                result = f"エラー: {e}"
            print(f"[結果] {result}")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "（打ち切り：ツール使用が上限に達しました）"

if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "今の時刻の「分」を二乗するといくつ？"
    print("最終回答:", run_agent(question))
