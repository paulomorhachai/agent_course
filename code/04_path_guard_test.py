"""第4回: 関門 safe_path の単体テスト。

エージェントを走らせなくても、身体の範囲が正しいかはここで確かめられる。
本文で「パス制限はこう設計する」と書く以上、その主張は機械で検証できる形にしておく。
"""
import importlib.util
import sys
from pathlib import Path

# ファイル名が数字で始まるので普通の import は使えない。パス指定で読み込む
spec = importlib.util.spec_from_file_location(
    "file_agent", Path(__file__).resolve().parent / "04_file_agent.py")
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)

OK = "通った"
NG = "落ちた"


def allowed(name):
    """関門を通るべきもの。"""
    try:
        fa.safe_path(name)
        return True
    except ValueError:
        return False


def main():
    通すべき = ["memo.txt", "notes/today.txt", "./memo.txt", "a/../memo.txt"]
    弾くべき = ["../secret.txt", "../../etc/passwd", "/etc/passwd",
                "notes/../../outside.txt"]

    失敗 = []
    for name in 通すべき:
        got = allowed(name)
        print(f"  通すべき {name!r:28} → {OK if got else NG}")
        if not got:
            失敗.append(f"通すべき {name} が弾かれた")
    for name in 弾くべき:
        got = allowed(name)
        print(f"  弾くべき {name!r:28} → {NG if not got else OK}")
        if got:
            失敗.append(f"弾くべき {name} が通ってしまった")

    print()
    if 失敗:
        for f in 失敗:
            print("NG:", f)
        sys.exit(1)
    print(f"全{len(通すべき) + len(弾くべき)}件 合格")


if __name__ == "__main__":
    main()
