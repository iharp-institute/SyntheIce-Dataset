#!/usr/bin/env python
"""Write a manifest CSV: one row per file with its metadata.

    python scripts/make_manifest.py data --out data/manifest.csv

Columns: path, file, bucket, index, type, height, width, tilt_angle,
layers_generated, total_fragments, parent_radargram, crop_index.

Use the manifest to publish the exact file lists behind each
experiment (for example the 400 radargrams used for TraceLink).
"""

import argparse
import glob
import os
import re
import sys

import h5py
import pandas as pd



def parse_index(name, bucket):
    """Index = digits right after 'synthetic_radargram_output_<bucket>'."""
    prefix = f"synthetic_radargram_output_{bucket}"
    if not name.startswith(prefix):
        return None
    m = re.match(r"\d+", name[len(prefix):])
    return int(m.group()) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--out", default="data/manifest.csv")
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob(os.path.join(args.root, "**", "*.h5"), recursive=True)):
        with h5py.File(path, "r") as f:
            m = dict(f["metadata"].attrs)
        name = os.path.basename(path)
        rows.append({
            "path": os.path.relpath(path, args.root),
            "file": name,
            "bucket": str(m.get("bucket")),
            "index": parse_index(name, str(m.get("bucket"))),
            "type": str(m.get("type")),
            "height": int(m.get("depth")),
            "width": int(m.get("width")),
            "tilt_angle": float(m.get("tilt_angle", 0.0)),
            "layers_generated": int(m.get("layers_generated")),
            "total_fragments": int(m.get("total_fragments")),
            "parent_radargram": str(m.get("parent_radargram", "")),
            "crop_index": int(m["crop_index"]) if "crop_index" in m else None,
        })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(df.groupby(["bucket", "type"]).size().to_string())
    print(f"\n{len(df)} files -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
