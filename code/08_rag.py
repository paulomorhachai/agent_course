"""第8回: 完成品 — 意味で探す記憶（素朴なRAGを標準ライブラリだけで）

使い方:  python3 08_rag.py            （検索の実験）
         python3 08_rag.py "猫の名前は？"   （探してから答えさせる）

第7回の recall は文字が一致しないと引けなかった。
「住まい」で引きたいのに記憶には「札幌」としか書いていない、という取りこぼしが起きる。
意味の近さを数で測れば、その溝を越えられる。
"""
import json
import math
import sys
import urllib.request

CHAT_MODEL = "gemma4:e4b"
EMBED_MODEL = "bge-m3"
OLLAMA = "http://localhost:11434"

# 記憶の代わりの小さな知識。実際は第7回の memory.md を1行ずつ入れればよい
NOTES = [
    "飼っている猫の名前はミケで、三毛猫の雌です。",
    "住まいは札幌で、冬は雪かきに追われます。",
    "先週、書店で小説を3冊買いました。",
    "夕食にカレーを作るときは、隠し味に珈琲を少し入れます。",
    "自転車の後輪がパンクしたので、来週修理に出す予定です。",
    "会社の締め切りは毎月20日です。",
]


def post(path, payload):
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)


# ---------- 埋め込みと距離 ----------

def embed(text):
    """文を数のベクトルに変える。近い意味の文は近い方向を向く。"""
    return post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})["embedding"]


def cosine(a, b):
    """2つの向きがどれだけ揃っているか。1に近いほど同じ方向を向いている。

    長さを割り落として向きだけを見るので、文の長短に振り回されない。
    """
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ---------- 探す ----------

INDEX = []  # (本文, ベクトル) の並び。件数が少ないので総当たりでよい


def build_index(notes=NOTES):
    INDEX.clear()
    for text in notes:
        INDEX.append((text, embed(text)))
    return len(INDEX)


def search(query, k=2):
    """問いに近い順に k 件返す。総当たりで全件と比べるだけ。"""
    qv = embed(query)
    scored = [(cosine(qv, v), text) for text, v in INDEX]
    scored.sort(reverse=True)
    return scored[:k]


# ---------- 道具として繋ぐ ----------

def recall_tool(query):
    hits = search(query, k=2)
    return "\n".join(f"（近さ {s:.3f}）{t}" for s, t in hits)


TOOLS_IMPL = {"recall": recall_tool}

TOOLS_SPEC = [{
    "type": "function",
    "function": {
        "name": "recall",
        "description": "自分の記憶から、質問に関係のある事柄を探して返す",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "探したい内容"}},
            "required": ["query"]}},
}]


def run_agent(question):
    messages = [
        {"role": "system", "content":
         "あなたはユーザー本人の記憶を預かるアシスタントです。"
         "答える前に必ず recall で記憶を探してください。"},
        {"role": "user", "content": question},
    ]
    for _ in range(4):
        payload = {"model": CHAT_MODEL, "messages": messages,
                   "tools": TOOLS_SPEC, "stream": False}
        msg = post("/api/chat", payload)["message"]
        messages.append(msg)
        if not msg.get("tool_calls"):
            return msg["content"]
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            print(f"[ツール実行] {name}({args})")
            result = TOOLS_IMPL[name](**args)
            print(f"[結果] {result}")
            messages.append({"role": "tool", "tool_name": name, "content": str(result)})
    return "（打ち切り）"


QUERIES = [
    ("住んでいる場所", "文字は一致しないが意味は近い"),
    ("ペット", "「猫」とも「ミケ」とも書いていない"),
    ("読書", "「書店」「小説」に届くか"),
    ("パンク", "文字が一致する素直な例"),
    ("量子力学", "記憶に無い話題。それでも何かは返る"),
]


def experiment():
    n = build_index()
    print(f"記憶 {n} 件を埋め込みました（{EMBED_MODEL}、次元 {len(INDEX[0][1])}）")
    for q, why in QUERIES:
        print(f"--- 問い: {q}  （{why}）")
        for s, t in search(q, k=2):
            print(f"  {s:.3f}  {t}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        build_index()
        print("最終回答:", run_agent(sys.argv[1]))
    else:
        experiment()
