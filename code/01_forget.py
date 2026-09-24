"""第1回: 「記憶」の正体を確かめる実験。履歴を送らないと直前の話も忘れる"""
import json
import urllib.request

def chat(messages):
    payload = {"model": "gemma4:e4b", "messages": messages, "stream": False}
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]["content"]

# 実験A: 履歴を渡さず、2回別々に呼ぶ
print("--- 実験A: 毎回まっさら ---")
print("1回目:", chat([{"role": "user", "content": "私の名前は太郎です。覚えてください。"}])[:80])
print("2回目:", chat([{"role": "user", "content": "私の名前は何でしたか？"}])[:80])

# 実験B: 履歴を全部渡して呼ぶ
print("--- 実験B: 履歴を全部送る ---")
messages = [{"role": "user", "content": "私の名前は太郎です。覚えてください。"}]
reply = chat(messages)
messages.append({"role": "assistant", "content": reply})
messages.append({"role": "user", "content": "私の名前は何でしたか？"})
print("2回目:", chat(messages)[:80])
