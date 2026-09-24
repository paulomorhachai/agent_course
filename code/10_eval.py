"""第10回: 完成品 — 小型モデルの出力を受け止め、点をつける

使い方:  python3 10_eval.py            （厳格な受け取りと緩い受け取りを比べる）

小型モデルは「JSONで返して」と書いても、前置きを付けたり、```で囲んだり、
末尾にコンマを残したりする。受け取り側を厳しくするほど、通らなくなる。
"""
import json
import re
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"

PROMPT = """次の文から、人名・場所・日付を抜き出してください。
必ず {"name": ..., "place": ..., "date": ...} の形のJSONだけを返してください。

文: {text}"""

EVALSET = [
    {"text": "太郎は3月4日に札幌へ行きました。",
     "want": {"name": "太郎", "place": "札幌", "date": "3月4日"}},
    {"text": "花子が10月1日、名古屋で講演します。",
     "want": {"name": "花子", "place": "名古屋", "date": "10月1日"}},
    {"text": "次郎は先週、京都に滞在していました（5月20日から）。",
     "want": {"name": "次郎", "place": "京都", "date": "5月20日"}},
    {"text": "美咲さんの引っ越し先は福岡で、日取りは12月8日です。",
     "want": {"name": "美咲", "place": "福岡", "date": "12月8日"}},
    {"text": "健一は8月15日に仙台の実家へ帰省しました。",
     "want": {"name": "健一", "place": "仙台", "date": "8月15日"}},
]


def ask(text):
    payload = {"model": MODEL, "stream": False, "messages": [
        {"role": "user", "content": PROMPT.replace("{text}", text)}]}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]["content"]


# ---------- 受け取り方1: 厳格 ----------

def strict_json(raw):
    """返ってきた文字列がそのままJSONであることを要求する。

    仕様どおりではあるが、仕様どおりに返すかはモデル次第で、こちらに決定権がない。
    """
    return json.loads(raw)


# ---------- 受け取り方2: 緩い ----------

def loose_parse(raw):
    """前置き・コードフェンス・末尾コンマを許して、中の対応表を取り出す。

    「モデルを直す」のではなく「受け取り方を広げる」。
    こちらのコードは自分で直せるが、モデルの癖は直せない。
    """
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)  # フェンスを剥がす
    m = re.search(r"\{.*\}", s, re.S)                            # 最初の { から } まで
    if not m:
        raise ValueError("JSONらしき部分が見つからない")
    body = re.sub(r",\s*([}\]])", r"\1", m.group(0))             # 末尾コンマを落とす
    return json.loads(body)


# ---------- 採点 ----------

def score(got, want):
    """3項目のうち何項目が一致したか。部分点を出すのは、
    全部一致だけを見ると「惜しい失敗」と「全然違う失敗」が同じ0点になるため。"""
    return sum(1 for k in want if str(got.get(k, "")).strip() == want[k])


def main():
    raws = [ask(c["text"]) for c in EVALSET]

    for mode, parse in (("厳格 strict_json", strict_json), ("緩い loose_parse", loose_parse)):
        ok, pts = 0, 0
        print(f"--- 受け取り方: {mode}")
        for c, raw in zip(EVALSET, raws):
            try:
                got = parse(raw)
                s = score(got, c["want"])
                ok += 1
                pts += s
                print(f"  受理 {s}/3  {got}")
            except Exception as e:
                print(f"  拒否 0/3  {type(e).__name__}: {str(e)[:40]}  生={raw[:40]!r}")
        print(f"  受理 {ok}/{len(EVALSET)} 件 / 合計 {pts}/{len(EVALSET)*3} 点\n")

    print("--- 生の返答（先頭2件）")
    for raw in raws[:2]:
        print(f"  {raw[:120]!r}")


if __name__ == "__main__":
    main()
