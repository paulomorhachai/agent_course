"""第1回: Ollama の API を裸で1回だけ叩く（フレームワークなし・標準ライブラリのみ）"""
import json
import urllib.request

payload = {
    "model": "gemma4:e4b",
    "messages": [
        {"role": "user", "content": "こんにちは。あなたは何ができますか？2文で。"}
    ],
    "stream": False,
}

req = urllib.request.Request(
    "http://localhost:11434/api/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as res:
    body = json.load(res)

print(json.dumps(body["message"], ensure_ascii=False, indent=2))
