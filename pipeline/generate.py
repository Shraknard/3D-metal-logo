#!/usr/bin/env python3
"""Shared pipeline: image + UI params -> STL. Used by server.py and build.py.

Parameter mapping
-----------------
mm_per_px = target_w / source_image_width  (épaississement is expressed in mm
relative to the final logo size, applied at source resolution before upscale).

grow_mm   = max(thicken_mm, nozzle/2)  -> guarantees every stroke gains at least
half a nozzle per side, so thin spikes reach >= one nozzle width and actually print.

Backing is a SECOND, wider dilation of the same shape (so detached islands merge
into a connected base):
  contour -> +1.5 mm   slab -> +7 mm   rect -> rectangular plaque   none -> none
"""
import json
import os
import subprocess
import sys

from PIL import Image

import merge_stl
import stl_bbox

HERE = os.path.dirname(os.path.abspath(__file__))
L2S = os.path.join(HERE, "logo2stl.py")
SCAD = os.path.join(HERE, "logo.scad")

BACKINGS = ("none", "offset", "hull", "rect")  # rect/hull connect everything
FORMATS = ("standard", "magnet", "stamp")

# --- magnet format (neodymium disc, glued into back pockets) ---
MAG_D, MAG_H = 8.0, 3.0      # standard hobby magnet
HOLE_CLR = 0.2               # radial/depth clearance for pockets AND the socket
MAG_FLOOR = 0.8              # wall left above the pocket, hides the magnet
MAG_EDGE = 2.5               # pocket edge -> plate edge gap
# --- stamp format (mirrored relief + handle socket) ---
SOCKET_D, SOCKET_DEPTH = 8.0, 5.0
PEG_LEN = SOCKET_DEPTH - 0.5  # peg stops short of the socket floor
KNOB_D, KNOB_H = 25.0, 18.0   # separate handle grip


def _openscad(stl, defs):
    cmd = ["openscad", "--export-format", "binstl", "-o", stl] + defs + [SCAD]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("openscad failed:\n" + r.stderr)


def generate(image, outdir, *, target_w=120.0, text_h=3.0, base_h=1.6,
             nozzle=0.4, thicken_mm=0.0, backing="offset", backing_offset_mm=1.5,
             work_px=1400, despeckle=0.01, rect_marg=5.0, threshold=-1,
             mirror=False, fmt="standard", magnet_n=2):
    os.makedirs(outdir, exist_ok=True)

    # Format presets override a few params before anything else. Both magnet and
    # stamp need a solid rectangular slab; the holes are computed later (they
    # depend on the traced content size, only known after logo2stl runs).
    relief_z = 0.0
    if fmt == "magnet":
        backing = "rect"
        base_h = max(base_h, MAG_H + HOLE_CLR + MAG_FLOOR)
        rect_marg = max(rect_marg, MAG_D + 2 * MAG_EDGE)
    elif fmt == "stamp":
        backing = "rect"
        mirror = True
        base_h = max(base_h, SOCKET_DEPTH + 1.0)
        relief_z = base_h - 0.2  # relief sits on the slab face; 0.2mm weld overlap

    src_w, _ = Image.open(image).size
    mm_per_px = target_w / src_w
    grow_mm = max(thicken_mm, nozzle / 2.0)
    grow_px = grow_mm / mm_per_px

    # Trace at a capped resolution: more pixels add triangles, not printable
    # quality (120mm @ 0.4mm nozzle resolves ~300 features). upscale<1 = downscale.
    upscale = max(0.05, float(work_px) / src_w)

    svg = os.path.abspath(os.path.join(outdir, "logo.svg"))
    backing_svg = os.path.abspath(os.path.join(outdir, "backing.svg"))

    cmd = [sys.executable, L2S, image, svg,
           "--grow-px", f"{grow_px:.3f}", "--upscale", f"{upscale:.4f}",
           "--despeckle", str(despeckle), "--opttolerance", "0.6",
           "--turdsize", "4", "--threshold", str(int(threshold)),
           "--debug-bmp", os.path.join(outdir, "binarized.png"),
           "--meta", os.path.join(outdir, "meta.json")]
    if mirror:
        cmd.append("--mirror")

    backing_code = 0
    use_backing_file = False
    if backing == "rect":
        backing_code = 3
    elif backing == "hull":
        backing_code = 2
    elif backing == "offset":
        backing_grow_px = (grow_mm + backing_offset_mm) / mm_per_px
        cmd += ["--backing-svg", backing_svg,
                "--backing-grow-px", f"{backing_grow_px:.3f}"]
        backing_code = 1
        use_backing_file = True

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("logo2stl failed:\n" + r.stderr)
    meta = json.loads(r.stdout.strip().splitlines()[-1])

    # Pockets bored from the back (z=0). Placed only where no relief sits above:
    # magnet pockets live in the side margins (|x| > target_w/2); the stamp socket
    # is central but safe because stamp mode lifts the relief onto the slab face.
    holes = []
    content_h_mm = (meta["content_h_px"] / meta["content_w_px"]) * target_w
    if fmt == "magnet":
        d, depth = MAG_D + HOLE_CLR, MAG_H + HOLE_CLR
        xc = target_w / 2.0 + rect_marg / 2.0  # centre of the side margin band
        if magnet_n >= 4:
            yo = content_h_mm * 0.3
            holes = [[-xc, -yo, d, depth], [-xc, yo, d, depth],
                     [xc, -yo, d, depth], [xc, yo, d, depth]]
        else:
            holes = [[-xc, 0.0, d, depth], [xc, 0.0, d, depth]]
    elif fmt == "stamp":
        holes = [[0.0, 0.0, SOCKET_D + HOLE_CLR, SOCKET_DEPTH]]
    holes_scad = "[" + ",".join(
        "[%g,%g,%g,%g]" % tuple(h) for h in holes) + "]"

    geom = [
        "-D", f'file="{svg}"',
        "-D", f'backing_file="{backing_svg if use_backing_file else ""}"',
        "-D", f"target_w={target_w}", "-D", f"text_h={text_h}",
        "-D", f"base_h={base_h}", "-D", f"k={meta['k']}",
        "-D", f"cx={meta['content_cx']}", "-D", f"cy={meta['content_cy']}",
        "-D", f"content_w={meta['content_w_px']}",
        "-D", f"content_h={meta['content_h_px']}",
        "-D", f"rect_marg={rect_marg}",
        "-D", f"relief_z={relief_z}",
        "-D", f"holes={holes_scad}",
    ]
    # Export each part separately (no boolean union -> fast), then concatenate.
    relief_stl = os.path.join(outdir, "_relief.stl")
    _openscad(relief_stl, geom + ["-D", "part=0"])
    parts = [relief_stl]
    if backing_code in (1, 2, 3):
        backing_stl = os.path.join(outdir, "_backing.stl")
        _openscad(backing_stl, geom + ["-D", f"part={backing_code}"])
        parts.append(backing_stl)

    stl = os.path.join(outdir, "logo.stl")
    ntri = merge_stl.merge(parts, stl)

    # Stamp mode also emits a separate, logo-independent handle (printed apart).
    handle_stl = None
    if fmt == "stamp":
        handle_stl = os.path.join(outdir, "handle.stl")
        _openscad(handle_stl, [
            "-D", f"knob_d={KNOB_D}", "-D", f"knob_h={KNOB_H}",
            "-D", f"peg_d={SOCKET_D - HOLE_CLR}", "-D", f"peg_h={PEG_LEN}",
            "-D", "part=4"])

    lo, hi = stl_bbox.stl_bbox(stl)
    dims = [round(hi[i] - lo[i], 2) for i in range(3)]
    return {"stl": stl, "dims": dims, "meta": meta, "triangles": ntri,
            "grow_mm": round(grow_mm, 3), "backing": backing,
            "fmt": fmt, "handle_stl": handle_stl}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--outdir", default="out/single")
    ap.add_argument("--target-w", type=float, default=120)
    ap.add_argument("--nozzle", type=float, default=0.4)
    ap.add_argument("--thicken", type=float, default=0.0)
    ap.add_argument("--backing", default="offset", choices=list(BACKINGS))
    ap.add_argument("--backing-offset", type=float, default=1.5)
    ap.add_argument("--work-px", type=int, default=1400)
    ap.add_argument("--threshold", type=int, default=-1,
                    help="0..255 binarization cutoff; <0 = auto (Otsu)")
    ap.add_argument("--mirror", action="store_true",
                    help="flip horizontally (stamp mode)")
    ap.add_argument("--format", dest="fmt", default="standard",
                    choices=list(FORMATS),
                    help="standard | magnet (back pockets) | stamp (mirror+socket)")
    ap.add_argument("--magnet-n", type=int, default=2, choices=(2, 4),
                    help="number of magnet pockets (magnet format)")
    a = ap.parse_args()
    res = generate(a.image, a.outdir, target_w=a.target_w, nozzle=a.nozzle,
                   thicken_mm=a.thicken, backing=a.backing,
                   backing_offset_mm=a.backing_offset, work_px=a.work_px,
                   threshold=a.threshold, mirror=a.mirror, fmt=a.fmt,
                   magnet_n=a.magnet_n)
    extra = f"  +handle {res['handle_stl']}" if res.get("handle_stl") else ""
    print(f"[ok] {res['stl']}  dims(mm) X={res['dims'][0]} Y={res['dims'][1]} "
          f"Z={res['dims'][2]}  {res['triangles']:,} tris  grow={res['grow_mm']}mm"
          f"  fmt={res['fmt']}{extra}")
