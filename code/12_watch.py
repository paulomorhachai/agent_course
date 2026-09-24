"""第12回: 卒業制作 — フォルダを見張って日報を書く当直エージェント

使い方:  python3 12_watch.py --once      （1回だけ見回って日報を書く）
         python3 12_watch.py --demo      （変化を作ってから見回る。教材用）

これまでの部品をそのまま使う。
第4回=ファイルの読み書きと関門 / 第5回=安全装置 / 第6回=足跡 / 第7回=長期記憶。
新しく書くのは「前回との差を取る」ところだけです。
"""
import datetime
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/chat"

HERE = Path(__file__).resolve().parent
WATCH_DIR = HERE / "watched"          # 見張る対象（第4回の作業フォルダと同じ考え方）
STATE_PATH = HERE / "watch_state.json"  # 前回の姿を覚えておく場所
REPORT_PATH = HERE / "watch_report.md"  # 日報の置き場
TRACE_PATH = HERE / "watch_trace.jsonl"


def trace(kind, **fields):
    """第6回の足跡。当直は無人で回すので、足跡が無いと後から何も分からない。"""
    rec = {"t": datetime.datetime.now().strftime("%H:%M:%S"), "kind": kind}
    rec.update(fields)
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def safe_path(name):
    """第4回の関門。当直でも身体の範囲は変わらない。"""
    target = (WATCH_DIR / name).resolve()
    if not target.is_relative_to(WATCH_DIR):
        raise ValueError(f"見張り対象の外です: {name}")
    return target


# ---------- 前回との差を取る ----------

def snapshot():
    """いまのフォルダの姿を「名前 → 中身の指紋と大きさ」で写し取る。

    中身の指紋（ハッシュ）まで見るのは、更新日時だけだと
    「開いて保存しただけ」も変更に見えてしまうためです。
    """
    shot = {}
    for p in sorted(WATCH_DIR.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            shot[str(p.relative_to(WATCH_DIR))] = {
                "size": len(data),
                "hash": hashlib.sha256(data).hexdigest()[:12],
            }
    return shot


def diff(old, new):
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = [k for k in new if k in old and new[k]["hash"] != old[k]["hash"]]
    return {"added": added, "removed": removed, "changed": changed}


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(shot):
    STATE_PATH.write_text(json.dumps(shot, ensure_ascii=False, indent=1),
                          encoding="utf-8")


# ---------- 日報を書かせる ----------

def summarize(changes, samples):
    """差分と、変わったファイルの冒頭だけをモデルに渡して短くまとめさせる。

    **判断の材料はこちらが集める。** モデルにフォルダを歩かせない。
    歩かせないので、見ていないものを見たと書くことができません。
    """
    facts = [f"追加 {len(changes['added'])}件: {changes['added']}",
             f"変更 {len(changes['changed'])}件: {changes['changed']}",
             f"削除 {len(changes['removed'])}件: {changes['removed']}"]
    for name, head in samples.items():
        facts.append(f"--- {name} の冒頭\n{head}")
    payload = {"model": MODEL, "stream": False, "messages": [
        {"role": "system", "content":
         "あなたは当直の記録係です。渡された事実だけを使って、"
         "3行以内の日本語で日報を書いてください。推測を足さないでください。"},
        {"role": "user", "content": "\n".join(facts)},
    ]}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)["message"]["content"].strip()


def patrol():
    WATCH_DIR.mkdir(exist_ok=True)
    trace("patrol_start", dir=str(WATCH_DIR.name))
    old = load_state()
    new = snapshot()
    changes = diff(old, new)
    n = sum(len(v) for v in changes.values())
    trace("diff", **{k: len(v) for k, v in changes.items()})
    print(f"[見回り] 追加{len(changes['added'])} / 変更{len(changes['changed'])}"
          f" / 削除{len(changes['removed'])}")

    if n == 0:
        save_state(new)
        trace("patrol_end", wrote=False)
        print("[日報] 変化なし。書くことがないので書きません")
        return None

    samples = {}
    for name in (changes["added"] + changes["changed"])[:3]:
        try:
            samples[name] = safe_path(name).read_text(encoding="utf-8")[:200]
        except Exception as e:
            samples[name] = f"（読めません: {e}）"

    report = summarize(changes, samples)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with REPORT_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n## {stamp}\n\n{report}\n")
    save_state(new)
    trace("patrol_end", wrote=True, chars=len(report))
    print(f"[日報]\n{report}")
    return report


def demo():
    """教材用に、変化を作ってから見回る。無人の一晩を早回しで再現する。"""
    WATCH_DIR.mkdir(exist_ok=True)
    for p in (STATE_PATH, REPORT_PATH, TRACE_PATH):
        p.unlink(missing_ok=True)
    for p in WATCH_DIR.rglob("*"):
        if p.is_file():
            p.unlink()

    print("--- 1回目: 初回（全部が新規に見える）")
    (WATCH_DIR / "todo.md").write_text("- 原稿を書く\n- 買い物\n", encoding="utf-8")
    (WATCH_DIR / "log.txt").write_text("起動しました\n", encoding="utf-8")
    patrol()

    print("\n--- 2回目: 何も触らずに見回る")
    patrol()

    print("\n--- 3回目: 1件変更・1件追加してから見回る")
    (WATCH_DIR / "log.txt").write_text("起動しました\nエラーが1件出ました\n",
                                       encoding="utf-8")
    (WATCH_DIR / "memo.txt").write_text("明日の予定を決める\n", encoding="utf-8")
    patrol()

    print("\n--- 足跡")
    print(TRACE_PATH.read_text(encoding="utf-8").rstrip())


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        patrol()
