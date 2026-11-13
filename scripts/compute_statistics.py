#!/usr/bin/env python
"""Per-category dataset statistics (the paper's dataset comparison table).

    python scripts/compute_statistics.py --src data/full --subset wide --out docs/statistics

Statistics per radargram, as defined in the notebook's per-bucket cell:
  layers_per_radargram     layers present in the file
  fragments_per_layer      mean fragments per layer (break rate)
  fragment_length_mean     mean of (col_end - col_start + 1), px
  fragment_width_mean      mean per-column thickness of a fragment, px
                           (pixel_count / columns; 1.0 for 1 px layers)
  undulation_range_mean    mean of (row_max - row_min + 1), px
                           (old "width" metric, kept for reference only)
  tilt_angle               degrees (0 for normal radargrams)
  layer_depth_variability  mean over layers of std(per-column row), px

--subset wide reproduces the notebook (statistics on the 148 wide
radargrams). Use --subset all or --subset normal for the other views.

Writes <out>/per_radargram.csv and <out>/per_category.csv.
"""

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generator import read_h5  # noqa: E402


def stats_for_file(path):
    d = read_h5(path)
    L, F, meta = d["layer_id_map"], d["fragments"], d["meta"]
    if F.size == 0:
        return None
    fdf = pd.DataFrame(F, columns=d["fragment_columns"])
    length = fdf["col_end"] - fdf["col_start"] + 1
    # every column of a fragment holds >= 1 pixel, so this equals the
    # mean per-column pixel count used in the notebook
    width = fdf["pixel_count"] / length
    undulation = fdf["row_max"] - fdf["row_min"] + 1

    depth_stds = []
    for lid in np.unique(L):
        if lid == 0:
            continue
        rows, cols = np.where(L == lid)
        if np.unique(cols).size < 5:
            continue
        # mean row per column, then std across columns
        order = np.argsort(cols)
        rows, cols = rows[order], cols[order]
        uc, start = np.unique(cols, return_index=True)
        row_means = np.add.reduceat(rows, start) / np.diff(np.append(start, rows.size))
        if row_means.size > 1:
            depth_stds.append(float(np.std(row_means)))

    return {
        "file": os.path.basename(path),
        "bucket": str(meta.get("bucket")),
        "type": str(meta.get("type")),
        "tilt_angle": float(meta.get("tilt_angle", 0.0)),
        "layers_per_radargram": int(meta.get("layers_generated", fdf["layer_id"].nunique())),
        "fragments_per_layer": float(fdf.groupby("layer_id")["fragment_id"].count().mean()),
        "fragment_length_mean": float(length.mean()),
        "fragment_width_mean": float(width.mean()),
        "undulation_range_mean": float(undulation.mean()),
        "layer_depth_variability": float(np.mean(depth_stds)) if depth_stds else 0.0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="data/full")
    ap.add_argument("--subset", choices=["wide", "normal", "all"], default="wide")
    ap.add_argument("--out", default="docs/statistics")
    args = ap.parse_args()

    pattern = {"wide": "*_wide.h5", "normal": "*.h5", "all": "*.h5"}[args.subset]
    files = sorted(glob.glob(os.path.join(args.src, "synthetic_radargram_output_*", pattern)))
    if args.subset == "normal":
        files = [f for f in files if not f.endswith("_wide.h5")]
    if not files:
        sys.exit(f"No files found under {args.src}")

    rows = [r for r in (stats_for_file(f) for f in files) if r]
    df = pd.DataFrame(rows)
    cols = ["layers_per_radargram", "fragments_per_layer", "fragment_length_mean",
            "fragment_width_mean", "undulation_range_mean", "tilt_angle",
            "layer_depth_variability"]
    summary = df.groupby("bucket")[cols].agg(["mean", "std"]).round(3)

    os.makedirs(args.out, exist_ok=True)
    df.to_csv(os.path.join(args.out, "per_radargram.csv"), index=False)
    summary.to_csv(os.path.join(args.out, "per_category.csv"))

    print(f"{len(df)} radargrams ({args.subset})\n")
    print(summary.to_string())
    print(f"\nSaved to {args.out}/")


if __name__ == "__main__":
    main()
