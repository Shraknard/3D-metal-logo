#!/usr/bin/env python3
"""CLI batch: generate several backing variants for side-by-side comparison.

  ./.venv/bin/python pipeline/build.py test_logo.png
Produces out/compare/<variant>/logo.stl for none / offset / hull / rect.
For the interactive tool use server.py instead.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate as gen  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--outdir", default="out/compare")
    ap.add_argument("--target-w", type=float, default=120)
    ap.add_argument("--nozzle", type=float, default=0.4)
    ap.add_argument("--thicken", type=float, default=0.0)
    a = ap.parse_args()

    variants = [("none", 0), ("offset", 1.5), ("offset", 8.0),
                ("hull", 0), ("rect", 0)]
    for backing, off in variants:
        name = backing if backing != "offset" else f"offset{off:g}"
        out = os.path.join(a.outdir, name)
        res = gen.generate(a.image, out, target_w=a.target_w, nozzle=a.nozzle,
                           thicken_mm=a.thicken, backing=backing,
                           backing_offset_mm=off)
        d = res["dims"]
        print(f"  {name:10s} -> {out}/logo.stl   X={d[0]} Y={d[1]} Z={d[2]} mm")


if __name__ == "__main__":
    main()
