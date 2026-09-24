"""生成された第4回を機械で検品する（EXP-112）。

見るのは4つ。
1. 構成 — 指定した見出しが揃っているか
2. コード — Pythonブロックが構文として通るか、こちらが渡していないコードを発明していないか
3. **ログ捏造** — 本文中の実行結果が、渡した実測ログに実在するか（この講座で最重要）
4. 文体 — 半角句読点・長文・地の文への英単語混入

「わかりやすさ」は機械では見られない。EXP-107 の結論どおり、誤りは検算の外に集中する。
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"

REQUIRED = ["前回の復習", "ファイルに書く", "道具を3つ", "関門", "実験",
            "まとめ", "練習問題", "解答例"]

FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)

# 実行結果らしい行。ここに挙げた形のものは実測ログに在らねばならない
LOGLINE = re.compile(r"^\s*(\[ツール実行\]|\[結果\]|最終回答:|\$ python3|=== \$)")

ALLOWED_WORDS = {
    "python", "ollama", "json", "llm", "api", "cli", "os", "urllib", "pathlib",
    "path", "resolve", "workdir", "memo", "txt", "secret", "true", "false",
    "none", "list_files", "read_file", "write_file", "safe_path", "max_rounds",
    "agent_system", "system", "tools", "messages", "content", "name", "role",
    "gemma4", "e4b", "note", "markdown", "py",
}


def plain_text(s):
    s = FENCE.sub("", s)
    s = re.sub(r"`[^`]*`", "", s)
    return s


def check_structure(sec):
    return [f"見出し「{h}」が無い" for h in REQUIRED
            if not re.search(rf"^#+.*{re.escape(h)}", sec, re.M)]


def check_code(sec, sources):
    """Pythonブロックの構文と、発明されたコードの検出。

    **無いことを合格にしない。** 初回の実測（Nemotron MLX）はコードブロックを
    1つも出さず、それを「コード OK」と報告した。0件は最大の違反として扱う。
    """
    issues = []
    n_py = sum(1 for lang, _ in FENCE.findall(sec) if lang in ("python", "py"))
    if n_py == 0:
        issues.append("Pythonのコードブロックが1つも無い（コード講座として不成立）")
    known = set()
    for src in sources:
        known |= {ln.strip() for ln in src.splitlines() if ln.strip()}
    for i, (lang, body) in enumerate(FENCE.findall(sec), 1):
        if lang not in ("python", "py"):
            continue
        try:
            ast.parse(body)
        except SyntaxError as e:
            issues.append(f"ブロック{i}: 構文エラー {e.msg}(L{e.lineno})")
            continue
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()
                 and not ln.strip().startswith("#")]
        stray = [ln for ln in lines if ln not in known]
        # 3行以上が素材に無いなら、コードを発明している疑い
        if len(stray) >= 3:
            issues.append(
                f"ブロック{i}: 素材に無い行が{len(stray)}行（例: {stray[0][:40]}）")
    return issues


def check_log_fabrication(sec, log_text):
    """本文の実行結果が実測ログに在るか。無ければ捏造。

    こちらも**引用が0件なら合格にしない**。捏造していないが素材も使っていない、
    という状態は「実測を見せる」という講座の設計を満たさない。
    """
    issues = []
    have = {ln.strip() for ln in log_text.splitlines() if ln.strip()}
    quoted = 0
    # 本文全体を見る。フェンスの中だけ見ていたら、``` を使わずに貼られた
    # 正しい引用を「0件」と誤報告した（EXP-112 run3）。同じ穴は捏造も見逃す
    for ln in sec.splitlines():
        if not LOGLINE.match(ln):
            continue
        s = ln.strip()
        quoted += 1
        if s not in have:
            issues.append(f"実測ログに無い出力: {s[:70]}")
    if quoted == 0:
        issues.append("実測ログの引用が1行も無い（捏造は無いが素材を使っていない）")
    return issues


def check_leakage(sec):
    """仕様書の言葉が本文に漏れていないか（「素材3から〜貼ります」など）。"""
    issues = []
    for m in re.finditer(r"素材[123]|上の構成|指示どおり|仕様書", sec):
        issues.append(f"仕様書の言葉が本文に漏れている: {m.group(0)}")
    return issues


def check_duplication(sec):
    """同じ見出し列が2度出ていないか（下書きが本文に混ざる型）。"""
    # 引用したログの中の見出し（日報の「## 時刻」など）を数えると誤検出になる。
    # コードブロックを外してから数える
    heads = [ln.strip() for ln in FENCE.sub("", sec).splitlines()
             if ln.startswith("#")]
    dup = [h for h in set(heads) if heads.count(h) > 1]
    return [f"見出しが重複: {', '.join(sorted(dup)[:4])}（下書きの混入を疑う）"] if dup else []


def check_volume(sec, floor=4000):
    """分量。第3回は約6,000字。極端に短い要約になっていないか。"""
    n = len(re.sub(r"\s", "", sec))
    return [] if n >= floor else [f"本文が{n:,}字（目安{floor:,}字未満）。要約になっている疑い"]


def check_style(sec):
    issues = []
    text = plain_text(sec)
    han = re.findall(r"[ぁ-んァ-ヴ一-龥][,\.](?=\s|$|[ぁ-んァ-ヴ一-龥])", text)
    if han:
        issues.append(f"半角の句読点が{len(han)}箇所")
    long_s = [s for s in re.split(r"[。\n]", text) if len(s.strip()) > 100]
    if long_s:
        issues.append(f"100字超の文が{len(long_s)}件（最長{max(len(s) for s in long_s)}字）")
    bare = re.sub(r"[（(][A-Za-z][A-Za-z \-_.]*[）)]", "", text)
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z_\.]{2,}", bare)}
    stray = sorted(words - ALLOWED_WORDS)
    if stray:
        issues.append("地の文に英単語: " + ", ".join(stray[:6])
                      + ("…" if len(stray) > 6 else ""))
    # 数と表現の間に助数詞が入る型（「100件を超える」）を落としていたので幅を持たせる。
    # 数学講座の版は「10を超えると」しか拾えず、selftest で発覚した
    for m in re.finditer(r"\d+[^\s。、]{0,3}(?:を超え|以上|未満|を下回)", text):
        issues.append(f"根拠の要る閾値表現: {m.group(0)}")
    return issues


def verify(label):
    """label は outputs/ のラベル、またはファイルパスそのもの。

    採用稿は講座直下（第4回_….md）へ移すので、移動後もその場で検品できるように
    パス指定を受け付ける。
    """
    p = Path(label)
    if not p.exists():
        p = OUT / f"04__{label}__section.md"
    sec = p.read_text(encoding="utf-8")
    log = (OUT / "04_demo_log.txt").read_text(encoding="utf-8")
    sources = [(ROOT / "code" / f).read_text(encoding="utf-8")
               for f in ("04_file_agent.py", "04_path_guard_test.py")]

    groups = [
        ("構成", check_structure(sec)),
        ("重複", check_duplication(sec)),
        ("指示の漏れ", check_leakage(sec)),
        ("分量", check_volume(sec)),
        ("コード", check_code(sec, sources)),
        ("ログ", check_log_fabrication(sec, log)),
        ("文体", check_style(sec)),
    ]
    print(f"=== {label} — 本文 {len(sec):,}字 ===")
    total = 0
    for name, issues in groups:
        total += len(issues)
        mark = "OK" if not issues else f"{len(issues)}件"
        print(f"[{name}] {mark}")
        for x in issues:
            print("   -", x)
    print(f"\n合計 {total}件")
    return total


if __name__ == "__main__":
    sys.exit(1 if verify(sys.argv[1] if len(sys.argv) > 1 else "nemotron_mlx") else 0)
