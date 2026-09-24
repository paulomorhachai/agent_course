"""第2回: ツールなしで計算させてみる実験。小型モデルは暗算が苦手"""
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

question = "48273 × 6157 を計算してください。答えの数値だけを出してください。"
for i in range(3):
    print(f"{i+1}回目:", chat([{"role": "user", "content": question}]).strip())
print("正解:  ", 48273 * 6157)
