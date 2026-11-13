#!/usr/bin/env python
"""Check that every SyntheIce file is internally consistent.

    python scripts/check_integrity.py data/full data/xcheck_set/tiles

Checks per file (full radargrams and tiles):
  1. mask is binary and equals (layer_id_map > 0)
  2. skeleton_layer_id_map only marks layer pixels, with the same IDs
  3. sum of fragment pixel_count == number of layer pixels
  4. per layer: pixels in layer_id_map == sum of its fragments' pixel_count
  5. num_fragments in the layers table == fragment rows for that layer
  6. metadata total_fragments / layers_generated / width / depth match the data
  7. (layer_id, fragment_id) is unique; fragments of a layer do not overlap in columns
  8. in every column, layer IDs increase from top to bottom (layers never cross)

Warnings (reported, not failures):
  - layer IDs with gaps (a layer fully hidden by breaks, partial trimming or tilt)
  - derived maps differ from data maps (expected only if layers are thicker than 1 px)

Exit code is 1 if any file fails, so this can run in CI.
"""

import argparse
import glob
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generator import read_h5  # noqa: E402


def check_file(path):
    """Return (errors, warnings) for one file."""
    d = read_h5(path)
    M, L, S, F, LY, meta = (d["mask"], d["layer_id_map"], d["skeleton_layer_id_map"],
                            d["fragments"], d["layers"], d["meta"])
    errs, warns = [], []

    if not set(np.unique(M)).issubset({0, 1}):
        errs.append("mask is not binary")
    if not np.array_equal(M > 0, L > 0):
        errs.append("mask != (layer_id_map > 0)")

    if S is not None:
        on = S > 0
        if np.any(on & (L == 0)):
            errs.append("skeleton marks background pixels")
        if not np.all(S[on] == L[on]):
            errs.append("skeleton IDs differ from layer_id_map")

    n_px = int((L > 0).sum())
    if F.size and int(F[:, 6].sum()) != n_px:
        errs.append(f"fragment pixel_count sum {int(F[:, 6].sum())} != layer pixels {n_px}")

    keys = [(int(r[1]), int(r[0])) for r in F]
    if len(keys) != len(set(keys)):
        errs.append("duplicate (layer_id, fragment_id)")

    counts = Counter(int(r[1]) for r in F)
    for lid, nf in LY:
        lid = int(lid)
        if counts.get(lid, 0) != int(nf):
            errs.append(f"layer {lid}: num_fragments {nf} != {counts.get(lid, 0)} rows")
        fl = F[F[:, 1] == lid]
        if int((L == lid).sum()) != int(fl[:, 6].sum()):
            errs.append(f"layer {lid}: pixel count mismatch")
        fl = fl[np.argsort(fl[:, 2])]
        if np.any(fl[1:, 2] <= fl[:-1, 3]):
            errs.append(f"layer {lid}: fragments overlap in columns")

    ids = np.unique(L)
    ids = ids[ids > 0]
    if set(int(i) for i in LY[:, 0]) != set(int(i) for i in ids):
        errs.append("layers table IDs != layer_id_map IDs")

    H, W = M.shape
    for k, v in [("total_fragments", F.shape[0]), ("layers_generated", len(ids)),
                 ("width", W), ("depth", H)]:
        if k in meta and int(meta[k]) != int(v):
            errs.append(f"metadata {k}={meta[k]} but data has {v}")

    r, c = np.nonzero(L)
    o = np.lexsort((r, c))
    r, c = r[o], c[o]
    v = L[r, c]
    same_col = c[1:] == c[:-1]
    if np.any(v[1:][same_col] <= v[:-1][same_col]):
        errs.append("layer IDs not increasing top to bottom within a column")

    if ids.size and not np.array_equal(ids, np.arange(1, ids.max() + 1)):
        missing = sorted(set(range(1, int(ids.max()) + 1)) - set(int(i) for i in ids))
        warns.append(f"layer IDs skip {missing}")

    C = d["centerline"]
    if C is not None and not np.array_equal(C > 0, M > 0):
        warns.append("derived/centerline differs from data/mask")
    if S is not None and not np.array_equal(S, L):
        warns.append("derived/skeleton_layer_id_map differs from data/layer_id_map")

    return errs, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+")
    args = ap.parse_args()

    files = sorted(f for folder in args.folders
                   for f in glob.glob(os.path.join(folder, "**", "*.h5"), recursive=True))
    if not files:
        sys.exit("No .h5 files found")

    n_bad = n_warn = 0
    for path in files:
        errs, warns = check_file(path)
        if errs:
            n_bad += 1
            print(f"FAIL {path}")
            for e in errs:
                print(f"     - {e}")
        if warns:
            n_warn += 1
            print(f"WARN {path}: " + "; ".join(warns))

    print(f"\nChecked {len(files)} files: {len(files) - n_bad} passed, "
          f"{n_bad} failed, {n_warn} with warnings")
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
