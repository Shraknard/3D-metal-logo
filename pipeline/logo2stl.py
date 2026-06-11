#!/usr/bin/env python3
"""Image -> black-on-white SVG(s) via potrace, with fast distance-transform dilation.

Emits the relief SVG (ink grown by --grow-px) and optionally a wider backing SVG
(grown by --backing-grow-px). Both rasters share the SAME padded canvas and the
SAME upscale, so the two potrace SVGs have identical width/height/viewBox and can
be placed in the SAME OpenSCAD coordinate frame (no per-object recentering).

All diagnostics go to stderr. stdout receives ONLY a JSON metadata blob, e.g.:
  {"canvas_px":[W,H],"k":0.35278,"content_cx":..,"content_cy":..,
   "content_w_px":..,"content_h_px":..,"otsu":..,"bg_is_dark":..,..}
where k = mm per SVG unit (OpenSCAD import: 1pt -> 25.4/72 mm), and content_*
are measured on the RELIEF, in upscaled px, already converted to SVG (y-up) space.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

K_MM_PER_PT = 25.4 / 72.0  # OpenSCAD treats 1 SVG pt as 1/72 inch


def log(*a):
    print(*a, file=sys.stderr)


def otsu_threshold(gray: np.ndarray) -> int:
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    total = gray.size
    sum_total = float(np.dot(np.arange(256), hist))
    w_b = sum_b = 0.0
    max_var = -1.0
    thr = 127
    for i in range(256):
        w_b += hist[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += i * hist[i]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > max_var:
            max_var = var
            thr = i
    return thr


def load_fg(path, invert):
    """Return (fg boolean array where True == ink, diag dict). Robust polarity:
    corners are assumed background; ink = the other class. A minority-class guard
    catches mislabeled cases (ink should normally cover < half the image)."""
    img = ImageOps.autocontrast(Image.open(path).convert("L"))
    g = np.asarray(img)
    h, w = g.shape
    thr = otsu_threshold(g)

    cs = int(min(h, w) * 0.05) + 1
    corners = np.concatenate([
        g[:cs, :cs].ravel(), g[:cs, -cs:].ravel(),
        g[-cs:, :cs].ravel(), g[-cs:, -cs:].ravel()])
    bg_is_dark = corners.mean() < thr

    if invert == "yes":
        fg = g <= thr
    elif invert == "no":
        fg = g > thr
    else:
        # ink = the class the corners do NOT belong to
        fg = (g > thr) if bg_is_dark else (g <= thr)
        # guard: if 'ink' is the majority, polarity is almost certainly flipped
        if fg.mean() > 0.5:
            log(f"[warn] ink covered {fg.mean():.0%} -> flipping polarity")
            fg = ~fg
    return fg, {"otsu": int(thr), "bg_is_dark": bool(bg_is_dark),
                "corners_mean": round(float(corners.mean()), 1),
                "ink_fraction": round(float(fg.mean()), 4)}


def dilate(fg, px):
    if px <= 0:
        return fg
    # distance transform: any background pixel within `px` of ink becomes ink.
    return ndimage.distance_transform_edt(~fg) <= px


def despeckle(fg, frac):
    if frac <= 0:
        return fg
    lbl, n = ndimage.label(fg)
    if n == 0:
        return fg
    sizes = ndimage.sum(np.ones_like(lbl), lbl, index=range(1, n + 1))
    keep = np.where(sizes >= frac * sizes.max())[0] + 1
    return np.isin(lbl, keep)


def trace(fg, out_svg, upscale, turdsize, alphamax, opttol, debug=None):
    """Rasterize ink=black, trace with potrace. Returns (canvas_w, canvas_h) px."""
    raster = np.where(fg, 0, 255).astype(np.uint8)
    bmp = Image.fromarray(raster, "L")
    if upscale and upscale != 1.0:
        h, w = raster.shape
        bmp = bmp.resize((int(w * upscale), int(h * upscale)), Image.LANCZOS)
        bmp = bmp.point(lambda p: 0 if p < 128 else 255)
    if debug:
        bmp.save(debug)
    cw, ch = bmp.size
    tmp = tempfile.NamedTemporaryFile(suffix=".bmp", delete=False).name
    try:
        bmp.convert("1").save(tmp)
        r = subprocess.run(
            ["potrace", tmp, "-s", "-o", out_svg, "--turdsize", str(turdsize),
             "--alphamax", str(alphamax), "--opttolerance", str(opttol)],
            capture_output=True, text=True)
    finally:
        os.unlink(tmp)
    if r.returncode != 0:
        log(r.stderr)
        sys.exit(r.returncode)
    return cw, ch


def content_bbox(fg):
    rows = np.where(np.any(fg, axis=1))[0]
    cols = np.where(np.any(fg, axis=0))[0]
    if rows.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inp")
    ap.add_argument("out_svg")
    ap.add_argument("--grow-px", type=float, default=0.0)
    ap.add_argument("--backing-svg", default=None)
    ap.add_argument("--backing-grow-px", type=float, default=0.0)
    ap.add_argument("--despeckle", type=float, default=0.01)
    ap.add_argument("--upscale", type=float, default=2.0)
    ap.add_argument("--turdsize", type=int, default=12)
    ap.add_argument("--alphamax", type=float, default=1.0)
    ap.add_argument("--opttolerance", type=float, default=0.2)
    ap.add_argument("--invert", choices=["auto", "yes", "no"], default="auto")
    ap.add_argument("--debug-bmp", default=None)
    ap.add_argument("--meta", default=None)
    a = ap.parse_args()

    fg, diag = load_fg(a.inp, a.invert)
    fg = despeckle(fg, a.despeckle)

    pad = int(np.ceil(max(a.grow_px, a.backing_grow_px))) + 6
    base = np.pad(fg, pad)

    relief = dilate(base, a.grow_px)
    cw, ch = trace(relief, a.out_svg, a.upscale, a.turdsize, a.alphamax,
                   a.opttolerance, debug=a.debug_bmp)

    if a.backing_svg and a.backing_grow_px > 0:
        backing = dilate(base, a.backing_grow_px)
        trace(backing, a.backing_svg, a.upscale, a.turdsize, a.alphamax,
              a.opttolerance)

    bb = content_bbox(relief)  # padded source px
    x0, y0, x1, y1 = (v * a.upscale for v in bb)  # -> upscaled px (== SVG units)
    meta = {
        "canvas_px": [cw, ch],
        "k": K_MM_PER_PT,
        "content_cx": (x0 + x1) / 2.0,
        "content_cy": ch - (y0 + y1) / 2.0,   # flip to SVG y-up
        "content_w_px": x1 - x0,
        "content_h_px": y1 - y0,
        "grow_px": a.grow_px,
        "backing_grow_px": a.backing_grow_px,
        **diag,
    }
    if a.meta:
        json.dump(meta, open(a.meta, "w"))
    log(f"[ok] {os.path.basename(a.out_svg)} canvas={cw}x{ch} "
        f"otsu={diag['otsu']} ink={diag['ink_fraction']:.2%} grow_px={a.grow_px:.1f}")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
