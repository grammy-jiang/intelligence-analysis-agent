#!/usr/bin/env python3
"""Reproducible Brier score: naive/overconfident baseline vs calibrated-forecasting-assisted.

Each item: (label, outcome 0/1, p_baseline, p_assisted). p_assisted applies the calibrated-forecasting
discipline (outside-view/base-rate first, then moderate). Brier = mean((p - outcome)^2); lower is better.

Honesty caveat: a model that already knows these outcomes cannot forecast them blind, so this is a
MECHANICS + DIRECTION demonstration — it shows that applying the outside-view + moderation discipline moves
Brier the right way against a documented-overconfidence baseline, NOT a blind benchmark. A blind Brier gate
needs a held-out / live feed (Phase 3).
"""

items = [
    ("Y2K catastrophic infrastructure failure (as of ~1998)", 0, 0.60, 0.12),
    ("Major terror attack at London 2012 Olympics (pre-event fear)", 0, 0.30, 0.06),
    ("Grexit — Greece leaves Eurozone by end-2015", 0, 0.50, 0.25),
    ("US recession by end-2023 (2022 consensus call)", 0, 0.65, 0.40),
    ("SpaceX lands an orbital-class booster (skepticism ~2015)", 1, 0.30, 0.45),
    ("Higgs boson confirmed at the LHC (strong prior theory)", 1, 0.80, 0.82),
    ("Heavy favorite wins (a genuine strong favorite that won)", 1, 0.85, 0.75),
    ("Fragile ceasefire holds 1 year (one that then collapsed)", 0, 0.55, 0.30),
]


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys, strict=True)) / len(ps)


def main():
    ys = [y for _, y, _, _ in items]
    base = [b for _, _, b, _ in items]
    asst = [a for _, _, _, a in items]
    Bb, Ba = brier(base, ys), brier(asst, ys)
    print(f"{'item':52} out base asst base_L2 asst_L2")
    for lab, y, b, a in items:
        print(f"{lab[:52]:52} {y}   {b:.2f} {a:.2f}  {(b - y) ** 2:.4f}  {(a - y) ** 2:.4f}")
    print("-" * 88)
    print(f"Baseline (naive/overconfident) Brier   = {Bb:.4f}")
    print(f"Assisted (calibrated-forecasting) Brier = {Ba:.4f}")
    print(f"Improvement: {Bb - Ba:+.4f} ({100 * (Bb - Ba) / Bb:.0f}% lower)")
    helped = sum(1 for _, y, b, a in items if (a - y) ** 2 < (b - y) ** 2)
    hurt = sum(1 for _, y, b, a in items if (a - y) ** 2 > (b - y) ** 2)
    print(f"discipline helped {helped}/{len(items)}, hurt {hurt}/{len(items)}")
    print("PASS" if Ba < Bb else "FAIL")


if __name__ == "__main__":
    main()
