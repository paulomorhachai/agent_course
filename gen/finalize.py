"""生成物を検品し、**検品結果を草稿の末尾に追記**して講座直下へ置く。

古留茂さんの指示（2026-08-21）: 誤りがあるなら草稿の一番下に書く。
確認は人がやるので、機械が見つけたものを隠さず全部並べる。
機械で見られないもの（説明の嘘、証明の飛躍）が残ることも明記する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lessons import LESSONS  # noqa: E402
from verify import groups_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"

NOTE_HEAD = "## 機械検品の結果（草稿につき、公開前に確認してください）"

PREAMBLE = """この節は自動で付けたものです。公開時は削除してください。

この草稿は Nemotron 3.5 Lightning 30B-A3B（MLX 4bit・thinking有効）が書き、
機械で検品したものです。**コードと実行ログは人が書いて実際に走らせたもの**を
渡しており、モデルには実行結果を書かせていません。
"""

TAIL = """
### 機械では見られないもの

検品が見ているのは形式です。**説明が事実と食い違っていないか、たとえ話が正しいか、
証明や理屈が飛んでいないかは判定できません。** EXP-107・EXP-112 の実測では、
誤りはこちら側（機械の外）に集中しました。第4回の草稿では「道具を2度使う」という
説明がログと食い違っていた例があります。読むときはそこを重点的に見てください。
"""


def finalize(n, label, dry=False):
    L = LESSONS[n]
    sec_path = OUT / f"{n:02d}__{label}__section.md"
    sec = sec_path.read_text(encoding="utf-8")

    groups = groups_for(sec, n)
    total = sum(len(v) for _, v in groups)

    lines = [sec.rstrip(), "", "---", "", NOTE_HEAD, "", PREAMBLE]
    if total == 0:
        lines.append("機械が見つけた問題は **0件** でした。\n")
    else:
        lines.append(f"機械が見つけた問題は **{total}件** です。\n")
        for name, issues in groups:
            if not issues:
                continue
            lines.append(f"**{name}**（{len(issues)}件）\n")
            lines += [f"- {x}" for x in issues]
            lines.append("")
    lines.append(TAIL)

    body = "\n".join(lines)
    dest = ROOT / f"第{n}回_{L['title']}_草稿.md"
    if dry:
        print(body[-1500:])
    else:
        dest.write_text(body, encoding="utf-8")
        print(f"第{n}回 → {dest.name}（本文{len(sec):,}字 / 検品{total}件を末尾に追記）")
    return total


if __name__ == "__main__":
    n = int(sys.argv[1])
    label = sys.argv[2] if len(sys.argv) > 2 else "nemotron_mlx"
    finalize(n, label, dry="--dry" in sys.argv)
