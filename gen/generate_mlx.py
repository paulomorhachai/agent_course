"""Nemotron MLX 4bit に第4回の本文を書かせる（EXP-112）。

thinking は既定で切る。EXP-107 では GGUF 版で thinking が分離されず、
下書きが回答欄を食って予算を4段（12k→20k→36k→45k）積む羽目になった。
MLX 版はテンプレートで制御できるので、長文生成では切って全予算を本文に回す。
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_prompt import MARK_BEGIN, MARK_END, build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
REPO = "mlx-community/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-4bit"


def split_section(text):
    """マーカーの対から本文を切り出す。

    EXP-107 で切り出しが2回壊れている（形式の復唱、下書きの飲み込み）。
    そこで対を全部拾い、Markdown見出しを最も多く含む区間を採る。
    """
    # ここは EXP-112 で3回壊れた。壊れ方が毎回違ったので、規則の当て方が間違っていた。
    #   (a) 開始と終了の対を要求 → 終了を出さない型を取り落とした
    #   (b) 最後の開始マーカーを採る → 思考中の形式復唱の断片(3字)を掴んだ
    #   (c) 見出しが最多の区間を採る → 思考ブロックの方が見出しが多く、思考を掴んだ
    # 3回目で、推測（マーカーの数え方）ではなく構造を使うことにした。
    # 思考は </think> で閉じる。閉じた後ろだけが答えで、そこにマーカーを当てる。
    # 閉じていなければ本文に到達していない（=予算切れ）ので、切り出す対象が無い。
    THINK_END = "</think>"
    answer = text.split(THINK_END, 1)[1] if THINK_END in text else text

    starts = [i for i in range(len(answer)) if answer.startswith(MARK_BEGIN, i)]
    ends = [i for i in range(len(answer)) if answer.startswith(MARK_END, i)]
    if not starts:
        return answer.strip(), False
    s = starts[-1]
    after = [e for e in ends if e > s]
    body = answer[s + len(MARK_BEGIN):after[0]] if after else answer[s + len(MARK_BEGIN):]
    return body.strip(), True


def thinking_closed(text):
    """思考が閉じたか。閉じていないのに thinking を有効にしていたら予算切れ。"""
    return "</think>" in text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", type=int, default=4)
    ap.add_argument("--label", default="nemotron_mlx")
    ap.add_argument("--max-tokens", type=int, default=12000)
    ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--think", action="store_true", help="thinking を有効にする")
    args = ap.parse_args()

    import mlx.core as mx
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler

    OUT.mkdir(exist_ok=True)
    n = args.lesson
    prompt = build(n)
    (OUT / f"{n:02d}_prompt.txt").write_text(prompt, encoding="utf-8")

    print(f"モデル読み込み: {REPO}", flush=True)
    t0 = time.time()
    model, tok = load(REPO)
    print(f"  {time.time()-t0:.1f}秒", flush=True)

    mx.random.seed(args.seed)
    text_in = tok.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True, enable_thinking=args.think)
    n_in = len(tok.encode(text_in))
    print(f"プロンプト {len(prompt):,}字 / {n_in:,}トークン / thinking={args.think}"
          f" / 予算{args.max_tokens:,}", flush=True)

    t0 = time.time()
    raw = generate(model, tok, prompt=text_in, max_tokens=args.max_tokens,
                   sampler=make_sampler(temp=args.temp), verbose=False)
    el = time.time() - t0
    n_out = len(tok.encode(raw))

    (OUT / f"{n:02d}__{args.label}__raw.txt").write_text(raw, encoding="utf-8")
    section, marked = split_section(raw)
    (OUT / f"{n:02d}__{args.label}__section.md").write_text(section, encoding="utf-8")

    meta = {
        "lesson": n, "label": args.label, "repo": REPO, "think": args.think,
        "max_tokens": args.max_tokens, "temp": args.temp, "seed": args.seed,
        "prompt_chars": len(prompt), "prompt_tokens": n_in,
        "raw_chars": len(raw), "section_chars": len(section),
        "out_tokens": n_out, "sec": round(el, 1),
        "tok_per_sec": round(n_out / el, 1) if el else None,
        # 予算いっぱいで止まったなら打ち切りの疑い。EXP-100 の教訓どおり
        # モデルの性質と決めつける前に予算を上げて撮り直す
        # 再エンコードした概算なので、ぴったり一致しない。相対で見る
        # （32,000に対し31,975を「余裕あり」と誤判定した実測がある）
        "budget_exhausted": n_out >= args.max_tokens * 0.98,
        "markers_found": marked,
        "thinking_closed": thinking_closed(raw),
    }
    (OUT / f"{n:02d}__{args.label}__meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1), flush=True)
    if meta["budget_exhausted"]:
        print("  ⚠ 予算切れの疑い。--max-tokens を上げて再走のこと", flush=True)
    if not marked:
        print("  ⚠ 区切りマーカーが見つからない。生を確認のこと", flush=True)
    if args.think and not meta["thinking_closed"]:
        print("  ⚠ 思考が閉じていない（</think> が無い）＝本文に到達していない。"
              "予算を上げて撮り直すこと", flush=True)


if __name__ == "__main__":
    main()
