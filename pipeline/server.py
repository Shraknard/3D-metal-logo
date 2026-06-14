#!/usr/bin/env python3
"""Local Flask server for the metal-logo -> STL tool.

Endpoints:
  GET  /                 -> the single-page UI
  GET  /vendor/<path>    -> vendored three.js
  GET  /out/<path>       -> generated artifacts (logo.stl, binarized.png)
  POST /upload           -> store the source image
  POST /generate         -> run the pipeline with given params, return dims + STL url

Run:  ./.venv/bin/python pipeline/server.py   then open http://127.0.0.1:5000
"""
import os
import sys
import time
import traceback

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate as gen  # noqa: E402
import logo2stl as l2s  # noqa: E402

ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, "out")
STATIC = os.path.join(HERE, "static")
UPLOAD = os.path.join(WORK, "upload.png")
os.makedirs(WORK, exist_ok=True)

app = Flask(__name__)


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/vendor/<path:p>")
def vendor(p):
    return send_from_directory(os.path.join(STATIC, "vendor"), p)


@app.get("/out/<path:p>")
def out(p):
    return send_from_directory(WORK, p)


@app.post("/upload")
def upload():
    f = request.files.get("image")
    if not f:
        return jsonify(ok=False, error="no file"), 400
    img = Image.open(f.stream)
    # flatten transparency onto white so thresholding sees a real background
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
    else:
        img = img.convert("RGB")
    img.save(UPLOAD)
    return jsonify(ok=True, width=img.width, height=img.height)


@app.post("/preview")
def preview():
    """Fast binarization-only pass (no potrace/openscad) so the threshold slider
    stays interactive. Returns a downscaled black-on-white PNG + the auto cutoff
    so the UI can seed the slider."""
    if not os.path.exists(UPLOAD):
        return jsonify(ok=False, error="Charge d'abord une image."), 400
    p = request.get_json(force=True) or {}
    thr = int(p.get("threshold", -1))
    inv = str(p.get("invert", "auto"))
    try:
        fg, diag = l2s.load_fg(UPLOAD, inv, thr)
        fg = l2s.despeckle(fg, 0.01)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return jsonify(ok=False, error=str(e)), 500

    raster = np.where(fg, 0, 255).astype(np.uint8)
    img = Image.fromarray(raster, "L")
    if img.width > 1000:  # keep the browser preview light
        ratio = 1000.0 / img.width
        img = img.resize((1000, max(1, round(img.height * ratio))), Image.NEAREST)
    img.save(os.path.join(WORK, "preview.png"))

    t = int(time.time() * 1000)
    return jsonify(ok=True, preview_url=f"/out/preview.png?t={t}",
                   otsu=diag["otsu"], threshold=diag["threshold"],
                   ink_fraction=diag["ink_fraction"])


@app.post("/generate")
def do_generate():
    if not os.path.exists(UPLOAD):
        return jsonify(ok=False, error="Charge d'abord une image."), 400
    p = request.get_json(force=True) or {}
    try:
        res = gen.generate(
            UPLOAD, WORK,
            target_w=float(p.get("target_w", 120)),
            text_h=float(p.get("text_h", 3.0)),
            base_h=float(p.get("base_h", 1.6)),
            nozzle=float(p.get("nozzle", 0.4)),
            thicken_mm=float(p.get("thicken_mm", 0.0)),
            backing=str(p.get("backing", "offset")),
            backing_offset_mm=float(p.get("backing_offset_mm", 1.5)),
            work_px=int(p.get("work_px", 1400)),
            threshold=int(p.get("threshold", -1)),
            mirror=bool(p.get("mirror", False)),
            fmt=str(p.get("fmt", "standard")),
            magnet_n=int(p.get("magnet_n", 2)),
            mag_h_mm=float(p.get("mag_h_mm", 2.0)),
            mag_gap_mm=float(p.get("mag_gap_mm", 60.0)),
            invert=str(p.get("invert", "auto")),
        )
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return jsonify(ok=False, error=str(e)), 500

    t = int(time.time() * 1000)
    handle_url = f"/out/handle.stl?t={t}" if res.get("handle_stl") else None
    return jsonify(ok=True,
                   stl_url=f"/out/logo.stl?t={t}",
                   binarized_url=f"/out/binarized.png?t={t}",
                   handle_url=handle_url, fmt=res["fmt"],
                   dims=res["dims"], triangles=res["triangles"],
                   grow_mm=res["grow_mm"], backing=res["backing"],
                   otsu=res["meta"].get("otsu"),
                   threshold=res["meta"].get("threshold"))


if __name__ == "__main__":
    print("metal-logo studio -> http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
