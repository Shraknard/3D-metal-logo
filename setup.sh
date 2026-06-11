#!/usr/bin/env bash
# One-shot setup: Python venv + dependencies + vendored Three.js.
# System packages (potrace, openscad, xvfb) must be installed separately — see README.
set -euo pipefail
cd "$(dirname "$0")"

echo ">> Python venv (.venv)"
python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

echo ">> Three.js (vendored for the offline 3D viewer)"
V=0.160.0
B="https://unpkg.com/three@${V}"
mkdir -p pipeline/static/vendor/jsm/controls pipeline/static/vendor/jsm/loaders
curl -fsSL -o pipeline/static/vendor/three.module.js                 "$B/build/three.module.js"
curl -fsSL -o pipeline/static/vendor/jsm/controls/OrbitControls.js   "$B/examples/jsm/controls/OrbitControls.js"
curl -fsSL -o pipeline/static/vendor/jsm/loaders/STLLoader.js        "$B/examples/jsm/loaders/STLLoader.js"

echo ""
echo "Done. Make sure the system tools are installed:"
echo "    sudo apt install -y potrace openscad xvfb"
echo "Then launch:  ./.venv/bin/python pipeline/server.py"
