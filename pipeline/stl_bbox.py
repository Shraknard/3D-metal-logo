#!/usr/bin/env python3
"""Read the bounding box (mm) of a binary or ASCII STL file."""
import struct
import sys


def stl_bbox(path):
    with open(path, "rb") as f:
        head = f.read(5)
        f.seek(0)
        if head == b"solid":
            # could still be binary with 'solid' prefix; try ascii then fallback
            data = f.read()
            try:
                txt = data.decode("ascii", "strict")
                if "facet normal" in txt:
                    xs = ys = zs = None
                    lo = [float("inf")] * 3
                    hi = [float("-inf")] * 3
                    for line in txt.splitlines():
                        line = line.strip()
                        if line.startswith("vertex"):
                            _, x, y, z = line.split()
                            for i, v in enumerate((float(x), float(y), float(z))):
                                lo[i] = min(lo[i], v)
                                hi[i] = max(hi[i], v)
                    return lo, hi
            except UnicodeDecodeError:
                pass
        # binary STL
        f.seek(80)
        (ntri,) = struct.unpack("<I", f.read(4))
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        for _ in range(ntri):
            f.read(12)  # normal
            for _v in range(3):
                x, y, z = struct.unpack("<3f", f.read(12))
                for i, val in enumerate((x, y, z)):
                    lo[i] = min(lo[i], val)
                    hi[i] = max(hi[i], val)
            f.read(2)  # attr
        return lo, hi


def dims(path):
    lo, hi = stl_bbox(path)
    return [round(hi[i] - lo[i], 3) for i in range(3)]


if __name__ == "__main__":
    p = sys.argv[1]
    lo, hi = stl_bbox(p)
    d = [round(hi[i] - lo[i], 3) for i in range(3)]
    print(f"bbox min={[round(v,3) for v in lo]} max={[round(v,3) for v in hi]}")
    print(f"dims  X={d[0]}  Y={d[1]}  Z={d[2]}  (mm)")
