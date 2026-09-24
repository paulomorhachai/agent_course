"""第7回: 完成品 — 会話を畳み、覚えておく

使い方:  python3 07_memory.py            （長い会話を圧縮して昔のことを訊く）

文脈には限りがある。伸び続ける会話をそのまま持ち歩けない。
畳む（圧縮）と、外に出す（長期記憶）の二段構えで凌ぐ。
"""
import json
import sys
import urllib.request
from pathlib import Path

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"
MEMORY_PATH = Path(__file__).resolve().parent / "memory.md"

KEEP_RECENT = 4  # 直近この件数はそのまま残す


def ask(messages, tools=None):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]


# ---------- 圧縮：古い会話を要約に畳む ----------

def compress(messages, keep=KEEP_RECENT):
    """先頭のsystemと直近keep件を残し、間を1件の要約に畳む。

    要約もモデルに書かせる。つまり**畳んだ時点で情報は失われる**。
    何を残すかを指示で決めるのが設計で、「全部残して」は不可能な相談になる。
    """
    head = [m for m in messages if m["role"] == "system"][:1]
    body = [m for m in messages if m["role"] != "system"]
    if len(body) <= keep:
        return messages
    old, recent = body[:-keep], body[-keep:]
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    summary = ask([
        {"role": "system", "content":
         "会話の要約係です。後で参照する事実（固有名詞・数値・決めごと）を"
         "落とさずに、5行以内の箇条書きにしてください。"},
        {"role": "user", "content": transcript},
    ])["content"]
    note = {"role": "system", "content": f"【これまでの会話の要約】\n{summary}"}
    return head + [note] + recent


# ---------- 長期記憶：ファイルに残す ----------

def remember(text):
    """覚えておきたい一行を追記する。第4回の write_file の親戚。"""
    with MEMORY_PATH.open("a", encoding="utf-8") as f:
        f.write(f"- {text}\n")
    return f"覚えました: {text}"


def recall(keyword=""):
    """記憶を読み出す。keyword があれば含む行だけ返す。

    これは検索と呼ぶには素朴すぎる（文字が一致しないと引けない）。
    その限界が第8回の入口になる。
    """
    if not MEMORY_PATH.exists():
        return "（まだ何も覚えていません）"
    lines = MEMORY_PATH.read_text(encoding="utf-8").splitlines()
    hit = [ln for ln in lines if keyword in ln] if keyword else lines
    return "\n".join(hit) if hit else f"（「{keyword}」を含む記憶はありません）"


# ---------- 実験 ----------

CONVERSATION = [
    "私の名前は太郎です。よろしく。",
    "私は札幌に住んでいます。",
    "飼っている猫の名前はミケです。",
    "今日は本を3冊買いました。",
    "夕食はカレーにしました。",
    "明日は雨だそうです。",
]


def main():
    messages = [{"role": "system", "content": "あなたは丁寧なアシスタントです。"}]
    for line in CONVERSATION:
        messages.append({"role": "user", "content": line})
        reply = ask(messages)
        messages.append({"role": "assistant", "content": reply["content"]})
        print(f"user: {line}")
        print(f"  assistant: {reply['content'][:50]}")

    print(f"\n--- 圧縮前: {len(messages)}件 ---")
    messages = compress(messages)
    print(f"--- 圧縮後: {len(messages)}件 ---")
    for m in messages:
        if m["content"].startswith("【これまでの会話の要約】"):
            print(m["content"])

    print("\n--- 畳んだ後で、昔のことを訊く ---")
    for q in ["私の猫の名前は？", "私はどこに住んでいますか？"]:
        messages.append({"role": "user", "content": q})
        reply = ask(messages)
        messages.append({"role": "assistant", "content": reply["content"]})
        print(f"user: {q}")
        print(f"  assistant: {reply['content'][:80]}")

    print("\n--- 長期記憶に書いて、読み出す ---")
    print(remember("飼い猫の名前はミケ"))
    print(remember("住まいは札幌"))
    print("recall('猫') →", recall("猫"))
    print("recall('東京') →", recall("東京"))


if __name__ == "__main__":
    if "--reset" in sys.argv and MEMORY_PATH.exists():
        MEMORY_PATH.unlink()
    main()
