"""HDF5 / PNG writers and config loading for SyntheIce."""

from __future__ import annotations

import json
import os

import h5py
import numpy as np

from .syntheice import (FRAGMENT_COLUMNS, LAYER_COLUMNS, build_tables,
                        make_skeleton_layer_id_map)


# ----------------------------------------------------------------------
# Configs
# ----------------------------------------------------------------------

def load_yaml(path):
    import yaml  # pyyaml
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_dataset_config(config_dir="configs"):
    """Return (dataset_cfg, {bucket_name: params}) in generation order."""
    ds = load_yaml(os.path.join(config_dir, "dataset.yaml"))
    buckets = {}
    for name in ds["generation_order"]:
        cat = load_yaml(os.path.join(config_dir, "categories", f"{name}.yaml"))
        buckets[cat["bucket"]] = cat["params"]
    return ds, buckets


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------

def radargram_filename(bucket, index, is_wide):
    """synthetic_radargram_output_<bucket><index:02d>[_wide].h5"""
    stem = f"synthetic_radargram_output_{bucket}{index:02d}"
    return stem + ("_wide.h5" if is_wide else ".h5")


def tile_filename(parent_stem, crop_index):
    return f"{parent_stem}_cropped_{crop_index:02d}.h5"


# ----------------------------------------------------------------------
# Writers
# ----------------------------------------------------------------------

def _write_tables(f, fragments, layers):
    g = f.create_group("tables")
    ds = g.create_dataset("fragments", data=fragments)
    ds.attrs["columns"] = json.dumps(FRAGMENT_COLUMNS)
    ds = g.create_dataset("layers", data=layers)
    ds.attrs["columns"] = json.dumps(LAYER_COLUMNS)


def write_radargram_h5(path, mask, layer_id_map, *, bucket, is_wide,
                       base_depths, tilt_angle, random_seed):
    """Write one full radargram in the released format."""
    from skimage.morphology import skeletonize

    fragments, layers, unique_layers = build_tables(layer_id_map)
    total_fragments = int(fragments.shape[0])
    H, W = mask.shape

    centerline = skeletonize(mask > 0).astype(np.uint8)
    skel_map = make_skeleton_layer_id_map(layer_id_map)

    with h5py.File(path, "w") as f:
        g = f.create_group("data")
        g.create_dataset("mask", data=mask, compression="gzip")
        g.create_dataset("layer_id_map", data=layer_id_map, compression="gzip")

        g = f.create_group("derived")
        g.create_dataset("centerline", data=centerline, compression="gzip")
        g.create_dataset("skeleton_layer_id_map", data=skel_map, compression="gzip")

        _write_tables(f, fragments, layers)

        m = f.create_group("metadata")
        m.attrs["bucket"] = bucket
        m.attrs["width"] = int(W)
        m.attrs["depth"] = int(H)
        # NOTE: "layers_requested" is the number of base depths that fit
        # inside depth_range, not the sampled num_layers. Name kept for
        # compatibility with the released files.
        m.attrs["layers_requested"] = int(len(base_depths))
        m.attrs["layers_generated"] = int(len(unique_layers))
        m.attrs["total_fragments"] = total_fragments
        m.attrs["fragment_ratio"] = float(total_fragments / (len(unique_layers) + 1e-6))
        m.attrs["type"] = "wide" if is_wide else "normal"
        m.attrs["tilt_angle"] = float(tilt_angle)
        m.attrs["random_seed"] = int(random_seed)

    return fragments, layers


def write_tile_h5(path, mask, layer_id_map, centerline, skel_map, *,
                  parent_meta, parent_stem, crop_index, start, end):
    """Write one cropped tile. ``end`` is exclusive."""
    fragments, layers, unique_layers = build_tables(layer_id_map)

    with h5py.File(path, "w") as f:
        g = f.create_group("data")
        g.create_dataset("mask", data=mask)
        g.create_dataset("layer_id_map", data=layer_id_map)

        g = f.create_group("derived")
        g.create_dataset("centerline", data=centerline.astype(np.uint8))
        g.create_dataset("skeleton_layer_id_map", data=skel_map.astype(np.int32))

        _write_tables(f, fragments, layers)

        m = f.create_group("metadata")
        m.attrs["bucket"] = parent_meta.get("bucket", "unknown")
        m.attrs["parent_radargram"] = parent_stem
        m.attrs["crop_index"] = int(crop_index)
        m.attrs["crop_start_col"] = int(start)
        m.attrs["crop_end_col"] = int(end)
        m.attrs["width"] = int(mask.shape[1])
        m.attrs["depth"] = int(mask.shape[0])
        m.attrs["layers_generated"] = int(len(unique_layers))
        m.attrs["total_fragments"] = int(fragments.shape[0])
        m.attrs["type"] = "cropped_radargram"
        m.attrs["tilt_angle"] = float(parent_meta.get("tilt_angle", 0.0))
        m.attrs["random_seed"] = int(parent_meta.get("random_seed", -1))


def write_png(path, mask):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 6))
    plt.imshow(mask, cmap="gray", origin="upper", aspect="auto")
    plt.axis("off")
    plt.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0)
    plt.close()


def read_h5(path):
    """Load everything from one SyntheIce file into a dict."""
    with h5py.File(path, "r") as f:
        out = {
            "mask": f["data/mask"][:],
            "layer_id_map": f["data/layer_id_map"][:],
            "centerline": f["derived/centerline"][:] if "derived/centerline" in f else None,
            "skeleton_layer_id_map": (f["derived/skeleton_layer_id_map"][:]
                                      if "derived/skeleton_layer_id_map" in f else None),
            "fragments": f["tables/fragments"][:],
            "layers": f["tables/layers"][:],
            "fragment_columns": json.loads(f["tables/fragments"].attrs.get(
                "columns", json.dumps(FRAGMENT_COLUMNS))),
            "layer_columns": json.loads(f["tables/layers"].attrs.get(
                "columns", json.dumps(LAYER_COLUMNS))),
            "meta": dict(f["metadata"].attrs),
        }
    return out
