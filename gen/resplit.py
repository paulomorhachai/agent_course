"""保存済みの生出力を、直した切り出しでもう一度切る。

再生成せずに切り直せるようにしておく（EXP-107 で同じ道具を作っている）。
切り出しは壊れやすい部品で、EXP-112 でも初回に1回壊れた。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_mlx import OUT, split_section  # noqa: E402

label = sys.argv[1] if len(sys.argv) > 1 else "nemotron_mlx"
raw = (OUT / f"04__{label}__raw.txt").read_text(encoding="utf-8")
sec, marked = split_section(raw)
(OUT / f"04__{label}__section.md").write_text(sec, encoding="utf-8")
print(f"生 {len(raw):,}字 → 本文 {len(sec):,}字 / マーカー {'あり' if marked else 'なし'}")
