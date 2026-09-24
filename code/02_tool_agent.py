"""第2回: 完成品 — 電卓ツールを1つ持つ最小エージェント（約80行）

使い方:  python3 02_tool_agent.py "48273 × 6157 は？"
"""
import ast
import json
import operator
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ---------- 道具（厨房）側 ----------

OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
}

def calc(expression):
    """四則演算と累乗だけを許す電卓。eval は使わない（理由は第5回）"""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        raise ValueError("数値と + - * / ** 以外は使えません")
    return ev(ast.parse(expression, mode="eval").body)

TOOLS_IMPL = {"calc": calc}

# ---------- モデルに渡す道具の説明書（メニュー）側 ----------

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
    }
]

# ---------- エージェント本体 ----------

def chat(messages):
    """messages を送り、モデルの返答メッセージ（辞書ごと）を返す"""
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
    while True:
        msg = chat(messages)
        messages.append(msg)
        if not msg.get("tool_calls"):          # 道具の注文がなければ最終回答
            return msg["content"]
        for call in msg["tool_calls"]:          # 注文が来た。厨房（こちら側）が実行する
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            print(f"[ツール実行] {name}({args})")
            try:
                result = TOOLS_IMPL[name](**args)
            except Exception as e:
                result = f"エラー: {e}"
            print(f"[結果] {result}")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})

if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "48273 × 6157 は？"
    print("最終回答:", run_agent(question))
