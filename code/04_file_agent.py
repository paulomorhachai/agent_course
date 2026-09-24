"""第4回: 完成品 — ファイルを読み書きできるエージェント（作業フォルダの中だけ）

使い方:  python3 04_file_agent.py "メモ帳に今日の予定を3つ書いて"

第3回との差は道具だけ。ループは1行も変わっていない。
新しいのは「道具が外の世界を書き換える」ことと、その範囲を縛る仕組み。
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_ROUNDS = 8

# エージェントに与える身体の範囲。ここから外へは手が届かない
WORKDIR = Path(__file__).resolve().parent / "workspace"
WORKDIR.mkdir(exist_ok=True)

# ---------- 身体の範囲を決める関門 ----------

def safe_path(name):
    """WORKDIR の中の実パスを返す。外を指していたら例外を投げる。

    ポイントは resolve() を先に呼ぶこと。"../../etc/passwd" のような文字列は
    resolve() して初めて実体が分かる。文字列のまま "../" を弾く方式だと、
    シンボリックリンクや "a/../../b" のような書き方で抜けられる。
    """
    target = (WORKDIR / name).resolve()
    if not target.is_relative_to(WORKDIR):
        raise ValueError(f"作業フォルダの外は触れません: {name}")
    return target


# ---------- 道具の実装（厨房） ----------

def list_files():
    names = sorted(p.name for p in WORKDIR.iterdir() if p.is_file())
    return "\n".join(names) if names else "（空です）"


def read_file(name):
    path = safe_path(name)
    if not path.exists():
        return f"エラー: {name} はありません"
    return path.read_text(encoding="utf-8")


def write_file(name, content):
    path = safe_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"{name} に {len(content)} 文字を書きました"


TOOLS_IMPL = {"list_files": list_files, "read_file": read_file, "write_file": write_file}

# ---------- 道具の説明書（メニュー） ----------

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "作業フォルダにあるファイル名の一覧を返す",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "作業フォルダのファイルを読んで中身を返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "ファイル名。例: memo.txt"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "作業フォルダのファイルに書き込む。既にあれば上書きする",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "ファイル名。例: memo.txt"},
                    "content": {"type": "string", "description": "書き込む本文"},
                },
                "required": ["name", "content"],
            },
        },
    },
]

# ---------- エージェント本体（第3回と同じ） ----------

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


# 「お願い」で守る層。環境変数で差し替えられるようにしてあるのは、
# これを外すと何が起きるかを第4回で実際に見るため
SYSTEM = os.environ.get(
    "AGENT_SYSTEM",
    "あなたはファイル操作ができるアシスタントです。作業フォルダの中だけで作業してください。",
)


def run_agent(user_input):
    messages = [
        {"role": "system", "content": SYSTEM},
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
    question = sys.argv[1] if len(sys.argv) > 1 else "作業フォルダに何がある？"
    print("最終回答:", run_agent(question))
