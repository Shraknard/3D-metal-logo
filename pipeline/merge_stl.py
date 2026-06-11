#!/usr/bin/env python3
"""Concatenate several STL files (ASCII or binary) into one binary STL.

The parts may overlap; we do NOT compute a boolean union (that's the slow step).
Slicers union overlapping solid volumes at slice time, so the result prints as
one solid piece. This keeps generation fast enough for an interactive UI.
"""
import struct
import sys


def read_triangles(path):
    """Return a flat list of (12 floats) tuples: nx,ny,nz, v1x..v3z per triangle."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:5] == b"solid" and b"facet normal" in raw[:2048]:
        return _read_ascii(raw.decode("ascii", "replace"))
    return _read_binary(raw)


def _read_binary(raw):
    (ntri,) = struct.unpack_from("<I", raw, 80)
    tris = []
    off = 84
    for _ in range(ntri):
        vals = struct.unpack_from("<12f", raw, off)
        tris.append(vals)
        off += 50  # 12 floats (48) + 2 attr bytes
    return tris


def _read_ascii(txt):
    tris = []
    n = (0.0, 0.0, 0.0)
    verts = []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("facet normal"):
            n = tuple(float(x) for x in line.split()[2:5])
            verts = []
        elif line.startswith("vertex"):
            verts.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith("endfacet") and len(verts) == 3:
            tris.append(n + verts[0] + verts[1] + verts[2])
    return tris


def write_binary(path, tris):
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<12f", *t))
            f.write(b"\0\0")


def merge(inputs, output):
    tris = []
    for p in inputs:
        tris.extend(read_triangles(p))
    write_binary(output, tris)
    return len(tris)


if __name__ == "__main__":
    out = sys.argv[1]
    n = merge(sys.argv[2:], out)
    print(f"[ok] {out}  ({n} triangles from {len(sys.argv) - 2} parts)")
