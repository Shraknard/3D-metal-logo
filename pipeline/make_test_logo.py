#!/usr/bin/env python3
"""Generate a synthetic 'spiky black-metal' style test logo.

White light-on-dark logo with a connected jagged body PLUS several detached
elements (floating spikes, isolated dots). This exercises the core problem:
detached islands that need a backing plate to print as one piece.
"""
import argparse
import math
import random
from PIL import Image, ImageDraw


def spike(draw, cx, cy, length, width, angle, fill):
    """Draw a thin triangular spike from (cx,cy) pointing at `angle`."""
    ax, ay = math.cos(angle), math.sin(angle)
    px, py = -ay, ax  # perpendicular
    tip = (cx + ax * length, cy + ay * length)
    b1 = (cx + px * width, cy + py * width)
    b2 = (cx - px * width, cy - py * width)
    draw.polygon([tip, b1, b2], fill=fill)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="test_logo.png")
    ap.add_argument("--w", type=int, default=1800)
    ap.add_argument("--h", type=int, default=900)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.seed)

    img = Image.new("L", (a.w, a.h), 0)  # dark background
    d = ImageDraw.Draw(img)
    ink = 255
    cy = a.h // 2

    # --- connected jagged body: 4 'glyph' clusters joined by a thin baseline ---
    baseline_y = cy + 120
    d.rectangle([180, baseline_y, a.w - 180, baseline_y + 18], fill=ink)  # ties glyphs together
    n = 4
    for i in range(n):
        gx = int(a.w * (i + 0.5) / n)
        # vertical jagged stroke
        d.polygon(
            [(gx - 35, baseline_y), (gx - 12, cy - 180),
             (gx + 12, cy - 180), (gx + 35, baseline_y)], fill=ink)
        # radiating spikes from each glyph top
        for _ in range(6):
            ang = random.uniform(-math.pi, 0)
            spike(d, gx, cy - 150, random.uniform(120, 260),
                  random.uniform(5, 13), ang, ink)

    # --- DETACHED elements (the hard part): floating, not touching the body ---
    detached = [
        (220, 120), (a.w - 220, 120),           # top corner accents
        (a.w // 2, 70),                           # floating crown dot
        (120, cy), (a.w - 120, cy),               # side dots
    ]
    for (dx, dy) in detached:
        d.ellipse([dx - 26, dy - 26, dx + 26, dy + 26], fill=ink)
        for _ in range(5):
            ang = random.uniform(0, 2 * math.pi)
            spike(d, dx, dy, random.uniform(60, 130),
                  random.uniform(4, 9), ang, ink)

    img.save(a.out)
    print(f"[ok] wrote {a.out} ({a.w}x{a.h}) — light-on-dark, {len(detached)} detached clusters")


if __name__ == "__main__":
    main()
