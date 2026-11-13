#!/usr/bin/env python
"""Regenerate the full SyntheIce dataset (600 radargrams, 4 categories).

    python scripts/generate_dataset.py --out data/full

Output (one folder per category, as in the original notebook):

    data/full/synthetic_radargram_output_<bucket>/
        synthetic_radargram_output_<bucket><NN>.h5        normal radargram
        synthetic_radargram_output_<bucket><NN>_wide.h5   wide, tilted radargram
        (+ matching .png previews unless --no-png)

Exact reproduction
------------------
The RNG is seeded once and consumed in generation order, so the released
files are reproduced only by a full run with the shipped configs.
``--only <bucket>`` still draws every earlier category (without writing
it) so the files it writes are identical to a full run.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from generator import (load_dataset_config, radargram_filename,  # noqa: E402
                       sample_radargram, write_png, write_radargram_h5)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config-dir", default="configs")
    ap.add_argument("--out", default="data/full")
    ap.add_argument("--only", default=None,
                    help="write only this bucket (earlier buckets are drawn but not written)")
    ap.add_argument("--no-png", action="store_true", help="skip PNG previews")
    args = ap.parse_args()

    ds, buckets = load_dataset_config(args.config_dir)
    if args.only and args.only not in buckets:
        sys.exit(f"Unknown bucket {args.only!r}. Choose from: {list(buckets)}")

    sizes = {k: tuple(v) for k, v in ds["sizes"].items()}
    n_images = int(ds["images_per_category"])
    n_wide = int(n_images * ds["wide_fraction"])
    seed = int(ds["random_seed"])

    np.random.seed(seed)

    for bucket, params in buckets.items():
        write = args.only is None or args.only == bucket
        out_dir = os.path.join(args.out, f"synthetic_radargram_output_{bucket}")
        if write:
            os.makedirs(out_dir, exist_ok=True)
            print(f"\n=== {bucket}: {n_images} radargrams ({n_wide} wide) -> {out_dir}")
        else:
            print(f"\n=== {bucket}: drawing only (not written)")

        wide_indices = np.random.choice(n_images, size=n_wide, replace=False)

        for i in range(n_images):
            is_wide = i in wide_indices
            mask, lid_map, base_depths, tilt, _ = sample_radargram(
                params, is_wide, sizes, ds["tilt_range_deg"])

            if not write:
                continue

            name = radargram_filename(bucket, i, is_wide)
            path = os.path.join(out_dir, name)
            frags, _ = write_radargram_h5(
                path, mask, lid_map, bucket=bucket, is_wide=is_wide,
                base_depths=base_depths, tilt_angle=tilt, random_seed=seed)
            if not args.no_png:
                write_png(path.replace(".h5", ".png"), mask)

            extra = f"  tilt={tilt:.2f} deg" if is_wide else ""
            print(f"  {name}: {len(np.unique(lid_map)) - 1} layers, "
                  f"{frags.shape[0]} fragments{extra}")

    print("\nDone.")


if __name__ == "__main__":
    main()
