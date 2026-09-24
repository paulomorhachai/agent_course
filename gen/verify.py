"""各回の検品。検査そのものは verify_04.py に置いたものを回ごとに当て直す。

必須見出しだけが回ごとに変わるので、そこだけ差し替える。
検査の中身（0件を合格にしない、フェンス外も見る、等）は EXP-112 で
本番を3回踏んで直したものなので、共有して育てる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_04 as V  # noqa: E402
from lessons import LESSONS  # noqa: E402
from check_scripts import issues_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def groups_for(sec, n):
    L = LESSONS[n]
    log = (OUT / L["log"]).read_text(encoding="utf-8")
    sources = [(ROOT / "code" / f).read_text(encoding="utf-8") for f in L["code"]]
    required = L["required"]
    structure = [f"見出し「{h}」が無い" for h in required
                 if not any(h in ln for ln in sec.splitlines() if ln.startswith("#"))]
    return [
        ("構成", structure),
        ("重複", V.check_duplication(sec)),
        ("指示の漏れ", V.check_leakage(sec)),
        ("分量", V.check_volume(sec)),
        ("コード", V.check_code(sec, sources)),
        ("ログ", V.check_log_fabrication(sec, log)),
        ("文体", V.check_style(sec)),
        ("文字化け", issues_for(sec)),
    ]


def verify(path_or_label, n):
    p = Path(path_or_label)
    if not p.exists():
        p = OUT / f"{n:02d}__{path_or_label}__section.md"
    sec = p.read_text(encoding="utf-8")
    groups = groups_for(sec, n)
    print(f"=== 第{n}回 {p.name} — 本文 {len(sec):,}字 ===")
    total = 0
    for name, issues in groups:
        total += len(issues)
        print(f"[{name}] {'OK' if not issues else f'{len(issues)}件'}")
        for x in issues:
            print("   -", x)
    print(f"\n合計 {total}件")
    return total


if __name__ == "__main__":
    n = int(sys.argv[1])
    verify(sys.argv[2] if len(sys.argv) > 2 else "nemotron_mlx", n)
