"""第5回: 完成品 — 道具に安全装置を三枚重ねる

使い方:  python3 05_safe_exec.py            （安全装置の実験だけ）
         python3 05_safe_exec.py "12*(3+4) を計算して"   （エージェントに使わせる）

第4回の関門は「触れる場所」を縛るものだった。今回縛るのは「できること」。
"""
import ast
import json
import operator
import os
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_ROUNDS = 8

# ---------- 層1: やってはいけない書き方 ----------

def naive_eval(expression):
    """一行で済む電卓。そして一行で全部渡してしまう電卓でもある。

    eval は「式」を評価するが、Python の式は関数呼び出しを含む。
    つまり計算だけを頼んだつもりで、実行環境そのものを渡している。
    """
    return eval(expression)


# ---------- 層2: 許す側を数える（ホワイトリスト） ----------

# 禁止したいものを並べる方式は、並べ忘れた1つで破れる。
# だから許すものだけを列挙する。ここに無い構文は、それだけで拒否される
OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
}

MAX_POW = 1000  # 2**999999999 のような式で固まらないための上限


def safe_eval(expression):
    """数と + - * / // % ** だけを許す電卓。それ以外は木の形で弾く。"""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > MAX_POW:
                raise ValueError(f"べき乗の指数が大きすぎます（上限 {MAX_POW}）")
            return OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        # ここに来た時点で、許した構文の外にいる
        raise ValueError(f"許可されていない書き方です: {type(node).__name__}")
    return ev(ast.parse(expression, mode="eval").body)


# ---------- 層3: 実行前に人へ聞く ----------

def confirm(action):
    """取り返しのつかない操作の前に人へ聞く。

    AGENT_AUTO_YES=1 のときは聞かずに通す。自動で流したいときの逃げ道だが、
    逃げ道を用意した瞬間に層3は無くなる、ということも一緒に覚えておきたい。
    """
    if os.environ.get("AGENT_AUTO_YES") == "1":
        print(f"[確認] {action} → 自動承認（AGENT_AUTO_YES=1）")
        return True
    answer = input(f"[確認] {action} を実行しますか？ [y/N] ").strip().lower()
    return answer == "y"


# ---------- 道具として繋ぐ ----------

def calc(expression):
    return safe_eval(expression)


TOOLS_IMPL = {"calc": calc}

TOOLS_SPEC = [{
    "type": "function",
    "function": {
        "name": "calc",
        "description": "数式を計算して正確な答えを返す電卓。計算が必要なときは必ず使うこと",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string",
                               "description": "Python 形式の数式。例: 12*(3+4), 2**10"}
            },
            "required": ["expression"],
        },
    },
}]


def chat(messages):
    payload = {"model": MODEL, "messages": messages,
               "tools": TOOLS_SPEC, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
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


# ---------- 実験 ----------

CASES = [
    "12*(3+4)",                          # ふつうの計算
    "2**10",                             # ふつうの計算
    '__import__("os").listdir(".")[:3]',  # 計算のふりをした環境アクセス
    'open(__file__).read()[:20]',         # 計算のふりをしたファイル読み出し
    "2**999999",                         # 計算だが機械を止めにかかる
]


def brief(value, limit=60):
    """2**999999 のような結果は30万桁になる。画面に出す前に切り詰める。"""
    s = repr(value)
    return s if len(s) <= limit else f"{s[:limit]}…（全{len(s)}文字）"


def experiment():
    for expr in CASES:
        print(f"--- 式: {expr}")
        try:
            print(f"  naive_eval → {brief(naive_eval(expr))}")
        except Exception as e:
            print(f"  naive_eval → 例外 {type(e).__name__}: {e}")
        try:
            print(f"  safe_eval  → {brief(safe_eval(expr))}")
        except Exception as e:
            print(f"  safe_eval  → 拒否 {type(e).__name__}: {e}")
    print("--- 層3: 実行前の確認")
    print(f"  confirm の戻り値: {confirm('memo.txt を上書き')}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("最終回答:", run_agent(sys.argv[1]))
    else:
        experiment()
