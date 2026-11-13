# SyntheIce file format

This page describes every file in the dataset. The [README](../README.md) has a short version.

## Contents

1. [Two kinds of file](#1-two-kinds-of-file)
2. [File names](#2-file-names)
3. [Coordinates and conventions](#3-coordinates-and-conventions)
4. [HDF5 structure](#4-hdf5-structure)
5. [Tables](#5-tables)
6. [Metadata](#6-metadata)
7. [Tiles (XCheck set)](#7-tiles-xcheck-set)
8. [How the data was generated](#8-how-the-data-was-generated)
9. [Reproducing the released files](#9-reproducing-the-released-files)
10. [Things to know before you use the data](#10-things-to-know-before-you-use-the-data)

---

## 1. Two kinds of file

| Kind | Count | Size (rows x columns) | `metadata.type` |
|---|---|---|---|
| Normal radargram | 452 (113 per category) | 1600 x 1600 | `normal` |
| Wide radargram | 148 (37 per category) | 2000 x 3000 | `wide` |
| Tile cut from a wide radargram | 592 (4 per wide radargram) | 2000 x 750 | `cropped_radargram` |

Full radargrams: 4 categories x 150 = **600**. Wide radargrams are tilted; normal radargrams are not.

---

## 2. File names

```
synthetic_radargram_output_<bucket><NN>.h5                  normal radargram
synthetic_radargram_output_<bucket><NN>_wide.h5             wide radargram
synthetic_radargram_output_<bucket><NN>_wide_cropped_<K>.h5 tile K (00 to 03)
```

- `<bucket>` is the category name: `close_To_synthetic0`, `mid_level0`, `close_To_real0` or `noisybucket0`. The trailing `0` is part of the name.
- `<NN>` is the index within the category, 0 to 149, written with at least two digits.

Because the bucket name ends in `0`, the index is easy to misread. `close_To_real003` is **index 03** of `close_To_real0`, and `close_To_real0101` is **index 101**. To get the index, strip `synthetic_radargram_output_<bucket>` and read the digits that follow. `scripts/make_manifest.py` does this for you.

Each `.h5` file may have a `.png` preview with the same name.

---

## 3. Coordinates and conventions

- **Arrays are `[row, column]`.** Row 0 is the top (the surface side) and rows grow with depth. Column 0 is the left edge.
- **Layer IDs** are integers `1..K`, numbered from the top down. `0` is background.
- **Layers never cross.** In every column, a layer with a higher ID sits below every layer with a lower ID, at least 3 px lower.
- **Layers are 1 px thick.** Each layer has at most one pixel per column.
- **Inclusive ranges in tables.** `col_end` and `row_max` are inclusive. A fragment spans `col_end - col_start + 1` columns.
- **Exclusive range in tile metadata.** `crop_end_col` is exclusive, matching Python slicing: a tile holds parent columns `[crop_start_col, crop_end_col)`.

---

## 4. HDF5 structure

```
<file>.h5
├── data/
│   ├── mask                    (H, W)  uint8   0 = background, 1 = layer pixel
│   └── layer_id_map            (H, W)  int32   0 = background, 1..K = layer ID
├── derived/
│   ├── centerline              (H, W)  uint8   skeleton of mask (all layers)
│   └── skeleton_layer_id_map   (H, W)  int32   per-layer skeleton, layer ID kept
├── tables/
│   ├── fragments               (N, 7)  int64   attrs: columns (JSON list)
│   └── layers                  (K, 2)  int64   attrs: columns (JSON list)
└── metadata/                   attributes only
```

- In full radargrams the image arrays are gzip-compressed. In tiles they are not.
- `data/mask` equals `layer_id_map > 0` exactly.
- Because layers are 1 px thick, skeletonizing changes nothing. `derived/centerline` equals `data/mask`, and `derived/skeleton_layer_id_map` equals `data/layer_id_map`. The `derived/` group is kept because the XCheck code reads from it. `scripts/check_integrity.py` warns if a file breaks this.

---

## 5. Tables

### `tables/fragments`: one row per fragment

A **fragment** is a maximal run of consecutive columns in which a layer is present. A break of even one column starts a new fragment.

| # | Column | Type | Meaning |
|---|---|---|---|
| 0 | `fragment_id` | int | Index of the fragment **within its layer**, 1, 2, 3, ... left to right. Restarts for each layer |
| 1 | `layer_id` | int | Parent layer, same ID as in `layer_id_map` |
| 2 | `col_start` | int | First column (inclusive) |
| 3 | `col_end` | int | Last column (inclusive) |
| 4 | `row_min` | int | Highest point of the fragment (smallest row) |
| 5 | `row_max` | int | Lowest point of the fragment (largest row) |
| 6 | `pixel_count` | int | Pixels in the fragment. With 1 px layers this equals the number of columns |

- **The unique key is `(layer_id, fragment_id)`.** `fragment_id` on its own repeats across layers.
- Rows are sorted by `layer_id`, then by `fragment_id`.
- `row_max - row_min + 1` is the vertical **undulation range** of the fragment, not its thickness.

### `tables/layers`: one row per layer

| # | Column | Type | Meaning |
|---|---|---|---|
| 0 | `layer_id` | int | Layer ID |
| 1 | `num_fragments` | int | Number of fragments the layer is broken into (1 = unbroken) |

Both tables store their column names as a JSON list in the dataset attribute `columns`:

```python
cols = json.loads(f["tables/fragments"].attrs["columns"])
```

---

## 6. Metadata

All values are attributes on the `/metadata` group.

### Full radargrams (`normal` and `wide`)

| Attribute | Type | Meaning |
|---|---|---|
| `bucket` | str | Category, e.g. `close_To_real0` |
| `type` | str | `normal` or `wide` |
| `width` | int | Columns |
| `depth` | int | Rows (image height, **not** a physical depth) |
| `layers_requested` | int | Layers placed before reaching the bottom of `depth_range`. See the note below |
| `layers_generated` | int | Distinct layer IDs actually present in `layer_id_map` |
| `total_fragments` | int | Rows in `tables/fragments` |
| `fragment_ratio` | float | `total_fragments / layers_generated` (with a 1e-6 term to avoid division by zero) |
| `tilt_angle` | float | Tilt in degrees. 0.0 for normal radargrams, 1 to 3 for wide |
| `random_seed` | int | Global seed of the whole run (42). **Not a per-file seed** |

**About `layers_requested`:** the generator first draws a target layer count from the category's `num_layers` range, then stops adding layers once they would fall below `depth_range[1]`. `layers_requested` records how many layers were actually placed, not the target count. The target count is not stored. `layers_generated` can be smaller than `layers_requested` if a layer is fully hidden by breaks, by trimmed ends, or by tilt pushing it off the bottom of the image.

### Tiles (`cropped_radargram`)

| Attribute | Type | Meaning |
|---|---|---|
| `bucket` | str | Category of the parent |
| `type` | str | `cropped_radargram` |
| `parent_radargram` | str | Parent file name without `.h5` |
| `crop_index` | int | 0 to 3, left to right |
| `crop_start_col` | int | First parent column in the tile (inclusive) |
| `crop_end_col` | int | End parent column (**exclusive**) |
| `width`, `depth` | int | 750, 2000 |
| `layers_generated` | int | Distinct layer IDs present in the tile |
| `total_fragments` | int | Rows in the tile's fragment table |
| `tilt_angle` | float | Copied from the parent |
| `random_seed` | int | Copied from the parent |

Tiles have no `layers_requested` or `fragment_ratio`.

---

## 7. Tiles (XCheck set)

Each wide radargram (2000 x 3000) is cut into 4 adjacent, equal tiles of 750 columns:

| `crop_index` | Parent columns |
|---|---|
| 0 | `[0, 750)` |
| 1 | `[750, 1500)` |
| 2 | `[1500, 2250)` |
| 3 | `[2250, 3000)` |

- **Layer IDs keep the parent's numbering.** Layer 7 in tile 2 is layer 7 in the parent. This is the ground truth XCheck is scored against.
- **The image arrays are sliced, not recomputed.** That includes `centerline` and `skeleton_layer_id_map`, so tile pixels line up exactly with the parent.
- **The tables are recomputed per tile.** A parent fragment that crosses a tile boundary appears as two fragments, one in each tile, and `fragment_id` restarts inside each tile.
- To map a tile column `c` back to the parent, use `parent_col = crop_start_col + c`.

---

## 8. How the data was generated

Per category, 150 radargrams. Of those, 37 indices are chosen at random to be wide, and the other 113 are normal. For each radargram:

1. **Draw the per-radargram settings** from the category config: the target layer count, the break probability and the jitter strength.
2. **Place layer depths.** The first layer starts at a random row in `[depth_range[0], depth_range[0] + 5]`. Each following layer is a random `gap_range` distance lower. Placement stops at `depth_range[1]`.
3. **Shared undulation.** One zero-mean cubic spline through 8 to 14 random knots, scaled by the jitter strength. Every layer follows it, plus a small random offset of its own (`layer_undulation_scale`).
4. **No crossing.** Each layer is pushed to at least 3 px below the one above it, in every column.
5. **Breaks.** With probability `break_prob`, a layer gets `breaks_per_layer` gaps, each `breaks_per_layer_length` columns long. Gaps can overlap.
6. **Partial layers.** If the category allows them, each end of a layer is trimmed with probability 0.5, by `partial_min` to `partial_max` columns.
7. **Tilt (wide only).** Column `c` is shifted down by `round(tan(tilt) * c)` rows, with tilt drawn from 1 to 3 degrees. Anything shifted past the last row is dropped.
8. **Tables.** Fragments and layer tables are extracted from the final `layer_id_map`.

The parameters for each category are in [`configs/categories/`](../configs/categories), and the dataset-wide settings are in [`configs/dataset.yaml`](../configs/dataset.yaml).

**Layers occupy only part of the image.** Layers are placed only inside `depth_range` (for example rows 100 to 900 for Close-to-Real). In a 1600-row normal radargram the bottom part is empty, and wide radargrams add up to about 160 extra rows of shift from tilt.

---

## 9. Reproducing the released files

```bash
python scripts/generate_dataset.py --out data/full
```

The run uses NumPy's legacy global RNG, seeded **once** with 42, and draws the categories in the order given in `configs/dataset.yaml`. A full run with the shipped configs reproduces the released files exactly. We checked this array by array against the released `close_To_real003`.

- **You can't regenerate one file on its own.** Every file depends on all the random draws before it. `random_seed` in the metadata is the seed for the whole run.
- `--only <bucket>` draws the earlier categories without writing them, so the files it writes still match a full run.
- **Any change shifts everything after it:** editing a config, reordering categories, or changing counts.

---

## 10. Things to know before you use the data

- **Use `(layer_id, fragment_id)` as the fragment key,** not `fragment_id` alone.
- **Don't use `row_max - row_min + 1` as thickness.** It measures undulation. Layer thickness is 1 px.
- **`depth` means image height.** It is a row count, not metres.
- **Layer IDs can skip a number** if a layer was hidden entirely. Use `np.unique(layer_id_map)` or `tables/layers`, not `range(1, K + 1)`. `scripts/check_integrity.py` reports these cases.
- **Dataset statistics** in the original notebook are computed on the 148 wide radargrams only. `scripts/compute_statistics.py --subset wide` reproduces that, and `--subset all` covers all 600.
