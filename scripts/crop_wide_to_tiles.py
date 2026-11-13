#!/usr/bin/env python
"""Crop every wide radargram into 4 equal, adjacent tiles (XCheck set).

    python scripts/crop_wide_to_tiles.py --src data/full --out data/xcheck_set/tiles

Each 2000 x 3000 wide radargram becomes 4 tiles of 2000 x 750:
columns [0, 750), [750, 1500), [1500, 2250), [2250, 3000).

The centerline and skeleton maps are SLICED from the parent, not
recomputed, so tile pixels line up exactly with the parent's ground
truth. Fragment and layer tables are recomputed per tile, so a parent
fragment that crosses a tile boundary appears as one fragment in each
tile. Layer IDs keep the parent's numbering.
"""

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generator import make_skeleton_layer_id_map, read_h5, tile_filename, write_png, write_tile_h5  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data/full", help="folder containing the category folders")
    ap.add_argument("--out", default="data/xcheck_set/tiles")
    ap.add_argument("--n-tiles", type=int, default=4)
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()

    wide_files = sorted(glob.glob(os.path.join(args.src, "synthetic_radargram_output_*", "*_wide.h5")))
    if not wide_files:
        sys.exit(f"No *_wide.h5 files found under {args.src}")
    os.makedirs(args.out, exist_ok=True)
    print(f"Found {len(wide_files)} wide radargrams")

    for path in wide_files:
        d = read_h5(path)
        H, W = d["mask"].shape
        tile_w = W // args.n_tiles
        if W % args.n_tiles:
            print(f"  warning: width {W} not divisible by {args.n_tiles}; "
                  f"last {W % args.n_tiles} columns dropped")
        stem = os.path.basename(path)[:-3]

        center = d["centerline"]
        skel = d["skeleton_layer_id_map"]

        for k in range(args.n_tiles):
            s, e = k * tile_w, (k + 1) * tile_w
            lid = d["layer_id_map"][:, s:e]
            c_tile = center[:, s:e] if center is not None else (lid > 0)
            s_tile = skel[:, s:e] if skel is not None else make_skeleton_layer_id_map(lid)

            out = os.path.join(args.out, tile_filename(stem, k))
            write_tile_h5(out, d["mask"][:, s:e], lid, c_tile, s_tile,
                          parent_meta=d["meta"], parent_stem=stem,
                          crop_index=k, start=s, end=e)
            if not args.no_png:
                write_png(out.replace(".h5", ".png"), d["mask"][:, s:e])
        print(f"  {stem}: {args.n_tiles} tiles")

    print(f"\nWrote {len(wide_files) * args.n_tiles} tiles to {args.out}")


if __name__ == "__main__":
    main()
