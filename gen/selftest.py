"""検証器そのものを検品する（EXP-112）。

EXP-107 では自分側の道具が3回壊れていた（切り出し2回・lint 1回）。
lint が「0件」と言ったのに実際は4箇所崩れていた、という型が一番危ない。
そこで**正しいものを通し、誤ったものを落とす**ことを対で確かめる。
落ちたら本番の判定を信じない。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_04 as V  # noqa: E402

GOOD_LOG = """=== $ python3 04_file_agent.py "作業フォルダに何がある？"
[ツール実行] list_files({})
[結果] （空です）
最終回答: 作業フォルダは空です。
"""

SRC = """def safe_path(name):
    target = (WORKDIR / name).resolve()
    if not target.is_relative_to(WORKDIR):
        raise ValueError("外は触れません")
    return target
"""

cases = []


def case(name, fn, want):
    cases.append((name, fn, want))


# ── 切り出し（EXP-112 で3回壊れた。3回目に構造ベースへ変えた）────────
from generate_mlx import split_section as SP  # noqa: E402

ART = "# 見出し\n## 節1\n本文\n## 節2\n本文"
THINK = "考え中\n# これは思考中の見出し\n## たくさん\n## 見出しがある\n</think>"
case("切り出し: 対で囲まれている→本文",
     lambda: SP(f"<<<SECTION>>>\n{ART}\n<<<END>>>")[0], ART)
case("切り出し: 終了マーカー無し→本文",
     lambda: SP(f"<<<SECTION>>>\n{ART}")[0], ART)
case("切り出し: 思考ブロックの見出しに引っ張られない",
     lambda: SP(f"{THINK}\n<<<SECTION>>>\n{ART}\n<<<END>>>")[0], ART)
case("切り出し: 思考中の形式復唱を掴まない",
     lambda: SP(f"復唱: <<<SECTION>>> and\n</think>\n<<<SECTION>>>\n{ART}\n<<<END>>>")[0], ART)
case("切り出し: マーカー無し→生を返す", lambda: SP("マーカー無しの本文")[1], False)

# ── 構成 ────────────────────────────────────────────────
FULL = "\n".join(f"## {h}" for h in V.REQUIRED)
case("構成: 全部ある→0件", lambda: len(V.check_structure(FULL)), 0)
case("構成: 1つ欠け→1件",
     lambda: len(V.check_structure(FULL.replace("## 関門", "## むかしばなし"))), 1)

# ── コード ──────────────────────────────────────────────
case("コード: 素材どおり→0件",
     lambda: len(V.check_code(f"```python\n{SRC}```", [SRC])), 0)
case("コード: 構文エラー→1件",
     lambda: len(V.check_code("```python\ndef f(:\n    pass\n```", [SRC])), 1)
case("コード: 発明された3行→1件",
     lambda: len(V.check_code(
         "```python\nimport requests\nr = requests.get(url)\nprint(r.text)\n```", [SRC])), 1)
# python以外のブロックを検査しないこと。単独だと「0件」規則に触れるので、
# 正しいPythonブロックを一緒に置いて、無視の挙動だけを見る
case("コード: python以外のブロックは見ない→0件",
     lambda: len(V.check_code(
         "```\nどんな文字列でも\nここは検査しない\nはず\n```\n"
         f"```python\n{SRC}```", [SRC])), 0)

# ── ログ捏造（この講座で最重要）────────────────────────
case("ログ: 実在する引用→0件",
     lambda: len(V.check_log_fabrication(
         "```\n[ツール実行] list_files({})\n[結果] （空です）\n```", GOOD_LOG)), 0)
case("ログ: 捏造された結果→1件",
     lambda: len(V.check_log_fabrication(
         "```\n[結果] memo.txt に 42 文字を書きました\n```", GOOD_LOG)), 1)
case("ログ: 捏造された最終回答→1件",
     lambda: len(V.check_log_fabrication(
         "```\n最終回答: 3件のファイルが見つかりました。\n```", GOOD_LOG)), 1)
# 実行結果らしくない行を拾わないこと。こちらも実在する引用を一緒に置く
case("ログ: 実行結果でない地の文は見ない→0件",
     lambda: len(V.check_log_fabrication(
         "```\nこれは説明のための擬似的な図です\n[結果] （空です）\n```", GOOD_LOG)), 0)

# ── 無いことを合格にしない（EXP-112 初回で踏んだ）────────
case("コード: 1つも無い→1件", lambda: len(V.check_code("本文だけ", [SRC])), 1)
case("ログ: 引用が1つも無い→1件",
     lambda: len(V.check_log_fabrication("本文だけ", GOOD_LOG)), 1)

# ── 下書きの混入 ────────────────────────────────────────
case("重複: 見出しが1回ずつ→0件",
     lambda: len(V.check_duplication("# A\n## B\n## C")), 0)
case("重複: 見出し列が2度→1件",
     lambda: len(V.check_duplication("# A\n## B\n# A\n## B")), 1)
case("重複: 引用ログ内の見出しは数えない→0件",
     lambda: len(V.check_duplication("# A\n## B\n```\n## 00:55\n## 00:55\n```")), 0)

# ── フェンス外の引用も見る（EXP-112 run3 で踏んだ）────────
case("ログ: フェンス外の正しい引用→0件",
     lambda: len(V.check_log_fabrication("[結果] （空です）", GOOD_LOG)), 0)
case("ログ: フェンス外の捏造→1件",
     lambda: len(V.check_log_fabrication("[結果] 3件見つかりました", GOOD_LOG)), 1)

# ── 指示文の漏れ ────────────────────────────────────────
case("漏れ: 無い→0件", lambda: len(V.check_leakage("ログを貼ります。")), 0)
case("漏れ: 素材Nが本文に→1件", lambda: len(V.check_leakage("素材3からログを貼ります。")), 1)

# ── 分量 ────────────────────────────────────────────────
case("分量: 足りる→0件", lambda: len(V.check_volume("あ" * 4200)), 0)
case("分量: 短すぎる→1件", lambda: len(V.check_volume("あ" * 2000)), 1)

# ── 文体 ────────────────────────────────────────────────
case("文体: 正しい日本語→0件",
     lambda: len(V.check_style("道具を足します。ループは変わりません。")), 0)
case("文体: 半角句読点→1件",
     lambda: len(V.check_style("道具を足します. ループは変わりません.")), 1)
case("文体: 100字超→1件",
     lambda: len(V.check_style("あ" * 120 + "。")), 1)
case("文体: 地の文の英単語→1件",
     lambda: len(V.check_style("この tool を呼び出します。")), 1)
case("文体: 括弧内の英語併記は通す→0件",
     lambda: len(V.check_style("道具（tool）を呼び出します。")), 0)
case("文体: コード中の英語は見ない→0件",
     lambda: len(V.check_style("`requests.get` を使います。")), 0)
case("文体: 根拠のない閾値→1件",
     lambda: len(V.check_style("ファイルが100件を超えると遅くなります。")), 1)


def main():
    ng = 0
    for name, fn, want in cases:
        try:
            got = fn()
        except Exception as e:
            got = f"例外 {e}"
        ok = got == want
        if not ok:
            ng += 1
        print(f"  {'OK ' if ok else 'NG '} {name:<38} 期待{want} / 実際{got}")
    print(f"\n{len(cases)}件中 {len(cases)-ng}件合格")
    if ng:
        print("検証器が壊れている。本番の判定を信じないこと")
        sys.exit(1)


if __name__ == "__main__":
    main()
