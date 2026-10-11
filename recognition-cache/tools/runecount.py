#!/usr/bin/env python3
"""Deterministic D2R rune counter for a 10x10 stash screenshot.

Usage (from the repo root):  python3 recognition-cache/tools/runecount.py <image> [--cells]

No manual input: the grid is located automatically, every cell is scored, and
the classification rules are fixed constants. Same image -> same output.

Per cell: keep grey stone pixels, crop to them, grayscale 40x40, mean-centred
and L2-normalised; score = correlation with each of the 33 d2runewizard chart
runes in recognition-cache/rune/. Classes:
  EMPTY   no stone pixels (or too few to be an item)
  RUNE    best >= ACCEPT and best - runner-up >= MARGIN
  OTHER   best < OTHER_MAX (gem, skull, weapon, ...)
  UNSURE  anything else -> exit code 2; the count is not reported as final
"""
import json, os, sys
import numpy as np
from PIL import Image

ROWS = COLS = 10
S = 40
ACCEPT, MARGIN, OTHER_MAX = 0.85, 0.15, 0.75
MIN_STONE = 150          # stone pixels needed before a cell counts as an item
ORDER = "El Eld Tir Nef Eth Ith Tal Ral Ort Thul Amn Sol Shael Dol Hel Io Lum Ko Fal Lem Pul Um Mal Ist Gul Vex Ohm Lo Sur Ber Jah Cham Zod".split()
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def stone_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (abs(r - g) < 25) & (abs(g - b) < 25) & (r > 70)


def glyph(img):
    a = np.asarray(img.convert("RGB"), int)
    m = stone_mask(a)
    if m.sum() < MIN_STONE:
        return None
    ys, xs = np.where(m)
    c = img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    g = np.asarray(c.convert("L").resize((S, S), Image.LANCZOS), float)
    g -= g.mean()
    return g / (np.linalg.norm(g) + 1e-9)


def references():
    idx = json.load(open(os.path.join(CACHE, "index.json")))
    refs = {}
    for e in idx:
        if e["category"] == "rune" and e["source"].startswith("d2runewizard"):
            refs[e["name"]] = glyph(Image.open(os.path.join(CACHE, e["file"])))
    missing = [n for n in ORDER if n not in refs]
    if missing:
        sys.exit(f"missing chart references: {missing}")
    return refs


def find_grid(img):
    """Locate the 10x10 grid: the cell borders are periodic edges, so pick the
    pitch/offset whose 11 lines carry the most edge energy, per axis."""
    g = np.asarray(img.convert("L"), float)
    def axis(profile):
        n = len(profile); best = None
        for p in range(30, n // ROWS + 1):
            for o in range(0, n - ROWS * p):
                s = profile[[o + k * p for k in range(ROWS + 1)]].sum()
                if best is None or s > best[0]:
                    best = (s, o, p)
        return best[1], best[2]
    gx = np.abs(np.diff(g, axis=1)).mean(axis=0)
    gy = np.abs(np.diff(g, axis=0)).mean(axis=1)
    x0, px = axis(gx)
    y0, py = axis(gy)
    return x0, y0, px, py


def classify(v, refs):
    if v is None:
        return "EMPTY", None, []
    sc = sorted(((float((v * refs[n]).sum()), n) for n in refs), reverse=True)
    (b, n), (r, _) = sc[0], sc[1]
    if b >= ACCEPT and b - r >= MARGIN:
        return "RUNE", n, sc[:2]
    if b < OTHER_MAX:
        return "OTHER", None, sc[:2]
    return "UNSURE", n, sc[:2]


def main():
    img = Image.open(sys.argv[1]).convert("RGB")
    refs = references()
    x0, y0, px, py = find_grid(img)
    counts, unsure, lines = {}, [], []
    lo, hi_other = 1.0, 0.0
    for r in range(ROWS):
        for c in range(COLS):
            cell = img.crop((x0 + c * px + 3, y0 + r * py + 3, x0 + (c + 1) * px - 3, y0 + (r + 1) * py - 3))
            kind, name, sc = classify(glyph(cell), refs)
            pos = f"{r+1}-{c+1}"
            if kind == "RUNE":
                counts[name] = counts.get(name, 0) + 1
                lo = min(lo, sc[0][0]); hi_other = max(hi_other, sc[1][0])
            elif kind == "UNSURE":
                unsure.append(f"{pos} {sc[0][1]} {sc[0][0]:.2f} / {sc[1][1]} {sc[1][0]:.2f}")
            lines.append(f"{pos} {kind}{' ' + name if name and kind == 'RUNE' else ''}"
                         + (f"  {sc[0][1]} {sc[0][0]:.2f} / {sc[1][1]} {sc[1][0]:.2f}" if sc else ""))
    print(f"grid x0={x0} y0={y0} cell={px}x{py}")
    if "--cells" in sys.argv:
        print("\n".join(lines))
    total = sum(counts.values())
    print(" · ".join(f"{n} ×{counts[n]}" for n in ORDER if n in counts) + f"  (total {total})")
    if total:
        print(f"rune scores {lo:.2f}+, runner-ups <= {hi_other:.2f}")
    if unsure:
        print("UNSURE (tooltip needed, count not final):\n  " + "\n  ".join(unsure))
        sys.exit(2)


if __name__ == "__main__":
    main()
