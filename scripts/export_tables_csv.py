#!/usr/bin/env python
"""Export the fragment and layer tables of every file to CSV.

    python scripts/export_tables_csv.py data/full --out data/csv

For each <name>.h5 writes <name>_fragments.csv and <name>_layers.csv,
with column names taken from the HDF5 'columns' attribute.
"""

import argparse
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generator import read_h5  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--out", default="data/csv")
    args = ap.parse_args()

    files = sorted(f for folder in args.folders
                   for f in glob.glob(os.path.join(folder, "**", "*.h5"), recursive=True))
    os.makedirs(args.out, exist_ok=True)

    for path in files:
        d = read_h5(path)
        stem = os.path.basename(path)[:-3]
        pd.DataFrame(d["fragments"], columns=d["fragment_columns"]).to_csv(
            os.path.join(args.out, f"{stem}_fragments.csv"), index=False)
        pd.DataFrame(d["layers"], columns=d["layer_columns"]).to_csv(
            os.path.join(args.out, f"{stem}_layers.csv"), index=False)

    print(f"Exported tables for {len(files)} files to {args.out}/")


if __name__ == "__main__":
    main()
