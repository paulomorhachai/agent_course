"""第11回: 完成品 — 役割を分けて、会話させる

使い方:  python3 11_multi.py            （一人で書く／二人で直す を比べる）

自分の書いたものを自分で検品するのは難しい。人でも同じで、だから校正係がいる。
役割を分けるとは、同じモデルに違う立場を与えて、別々の文脈で走らせることです。
"""
import json
import re
import sys
import urllib.request

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"


class Agent:
    """名前と立場を持った話し相手。文脈は各自が別々に持つ。

    立場を分けることが要点で、1つの文脈で「次は校正して」と続けると、
    自分の書いたものを庇う側に引っ張られます。
    """

    def __init__(self, name, system):
        self.name = name
        self.system = system
        self.history = []

    def say(self, text):
        msgs = ([{"role": "system", "content": self.system}]
                + self.history + [{"role": "user", "content": text}])
        payload = {"model": MODEL, "messages": msgs, "stream": False}
        req = urllib.request.Request(
            OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            reply = json.load(res)["message"]["content"]
        self.history += [{"role": "user", "content": text},
                         {"role": "assistant", "content": reply}]
        return reply


DRAFTER = Agent("起草係", "あなたは短い技術文の起草係です。求められた文章だけを書きます。")
CHECKER = Agent(
    "検査係",
    "あなたは技術文の検査係です。書き手ではありません。"
    "渡された文の誤り・言い過ぎ・根拠のない断定だけを、箇条書きで指摘します。"
    "指摘が無ければ『指摘なし』とだけ答えます。文章を書き直してはいけません。")

TASK = ("Python の list と tuple の違いを、初学者向けに3文で説明してください。"
        "余計な前置きは書かないでください。")


def review_loop(task, rounds=2):
    """起草 → 指摘 → 直す、を繰り返す。指摘が尽きたら止める。"""
    draft = DRAFTER.say(task)
    print(f"[起草係] {draft}\n")
    for i in range(1, rounds + 1):
        review = CHECKER.say(f"次の文を検査してください。\n---\n{draft}")
        print(f"[検査係 {i}回目] {review}\n")
        if "指摘なし" in review:
            print("（指摘が尽きたので終了）")
            break
        draft = DRAFTER.say(f"次の指摘を踏まえて直してください。指摘:\n{review}")
        print(f"[起草係 {i}回目の直し] {draft}\n")
    return draft


def main():
    print("=== 一人で書く ===")
    solo = Agent("単独", "あなたは短い技術文の書き手です。")
    alone = solo.say(TASK)
    print(f"{alone}\n")

    print("=== 二人で直す ===")
    together = review_loop(TASK)

    print("=== 比べる ===")
    print(f"一人 {len(alone)}字 / 二人 {len(together)}字")


if __name__ == "__main__":
    main()
