"""想定外の文字体系（キリル・ハングル等）の混入を検出する。

私は執筆中に2回、日本語のつもりでキリル文字を打った（U+0442 で始まる語など）。
1回目はコメントに書いたが再発したので、機械で落ちる形にする。
対象は講座のコード・ハーネス・草稿。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 使ってよい範囲: ASCII / ひらがな / カタカナ / 漢字 / 全角記号 / 罫線・絵文字の一部
ALLOWED = re.compile(
    r"[\x00-\x7F\u00D7\u00F7\u00B0\u00B1\u2026\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF"
    # \u2700-\u27BF\uFF08\u2728\u306A\u3069\u306E\u8A18\u53F7\uFF09\u3068\u7570\u4F53\u5B57\u30BB\u30EC\u30AF\u30BF\u30FBZWJ \u306F\u3001\u5B9F\u6E2C\u30ED\u30B0\u306B\u73FE\u308C\u308B
    # gemma4 \u306E\u7D75\u6587\u5B57\u304C\u305D\u306E\u307E\u307E\u5F15\u7528\u3055\u308C\u308B\u305F\u3081\u8A31\u5BB9\u3059\u308B\uFF08\u691C\u67FB\u306E\u8AA4\u691C\u51FA\u3060\u3063\u305F\uFF09
    r"\uFF00-\uFFEF\u2000-\u27BF\u2E80-\u2EFF\uFE0E\uFE0F\u200D\U0001F300-\U0001FAFF]"
)


def scan_text(text):
    """本文用。想定外の文字を「文字→行番号」でまとめて返す。"""
    bad = {}
    for i, line in enumerate(text.splitlines(), 1):
        for ch in line:
            if not ALLOWED.match(ch):
                bad.setdefault(ch, []).append(i)
    return bad


def issues_for(text):
    return [f"想定外の文字 {ch!r} (U+{ord(ch):04X}) が {len(ls)}箇所（L{ls[:3]}）"
            for ch, ls in scan_text(text).items()]


def scan(path):
    bad = {}
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for ch in line:
            if not ALLOWED.match(ch):
                bad.setdefault(ch, []).append(i)
    return bad


def main():
    targets = sorted(ROOT.glob("code/*.py")) + sorted(ROOT.glob("gen/*.py")) \
        + sorted(ROOT.glob("\u7b2c*.md"))
    ng = 0
    for p in targets:
        bad = scan(p)
        if bad:
            ng += 1
            for ch, lines in bad.items():
                print(f"NG {p.name}: {ch!r} (U+{ord(ch):04X}) L{lines[:5]}")
    print(f"{len(targets)}ファイル検査 / 問題 {ng}ファイル")
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()
