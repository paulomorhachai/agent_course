"""第1回: 完成品 — urllib だけで作るチャットループ（約40行）

使い方:  python3 01_chat_loop.py
終了:    exit と入力（または Ctrl-C / Ctrl-D）
"""
import json
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"

def chat(messages):
    """messages を送り、モデルの返答（文字列）を返す"""
    payload = {"model": MODEL, "messages": messages, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]["content"]

def main():
    messages = [
        {"role": "system", "content": "あなたは簡潔に答えるアシスタントです。"}
    ]
    while True:
        try:
            user_input = input("あなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input in ("exit", "quit"):
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        reply = chat(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"モデル> {reply}")
    print(f"（終了。この会話の messages は {len(messages)} 件でした）")

if __name__ == "__main__":
    main()
