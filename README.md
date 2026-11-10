# SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction

**Dataset and generator** for the paper *SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction* 



Muhammad Behroze Hassan, Bayu Adhi Tama, Sanjay Purushotham, Vandana P. Janeja
Department of Information Systems and NSF HDR Institute iHARP, University of Maryland, Baltimore County

> Looking for the experiments (XCheck, TraceLink, evaluation)? They live in the companion repository: **[SyntheIce-Experiments](https://github.com/iharp-institute/SyntheIce-Synthetic-Radargram-Annotation-Benchmark-for-Englacial-Layer-Reconstruction)**.

---

## Why SyntheIce dataset exists

Englacial layers in ice-penetrating radar record the history of the Greenland and Antarctic ice sheets. Tracing them automatically is hard to evaluate because:

- **Real labels are noisy.** Expert annotations disagree, and automatic tracers produce broken, fragmented layers.
- **There is no exact answer to score against.** You can't tell whether a method linked the right fragments if the ground truth itself is uncertain.
- **Generative image models don't help.** Current models hallucinate layers and provide no ground truth.

SyntheIce fixes this by **generating layer annotations where the answer is known exactly**. Every pixel and every fragment carries the identity of the layer it belongs to, so fragment linking, consistency checking and layer reconstruction can be scored against the true geometry instead of another noisy label.

---

## What the generator does

SyntheIce is a parametric generator (Algorithm 1 in the paper). Given an image size, a layer count, and spacing, break, jitter and tilt parameters, it:

1. Samples layer depths from the surface downward with random spacing.
2. Adds a shared, smooth undulation (zero-mean cubic spline) so layers bend together, as real layers do.
3. Keeps layers from crossing by enforcing a minimum vertical gap.
4. Breaks each layer into fragments, with optional partial layers that stop short of the edge.
5. Applies terrain tilt to wide radargrams.
6. Extracts the fragment and layer tables.

Because the labels come from the same curve as the drawn geometry, **every annotation is exact**.

---

## Difficulty categories

The dataset has four categories, with layer count and fragmentation increasing from top to bottom. Each category includes a fixed share of wide, tilted radargrams.

| Paper name | `bucket` value in files | What it represents |
|---|---|---|
| **Close-to-Synthetic** | `close_To_synthetic0` | Clean profiles with few breaks |
| **Mid-Level** | `mid_level0` | Moderate density and fragmentation |
| **Close-to-Real** | `close_To_real0` | Density and breakage within the range of real Greenland radar data |
| **Noisy-Level** | `noisybucket0` | Deliberately denser and more broken than real data; a stress test |

Across the categories, layers per radargram range from about **17 to 41**, and fragments per layer range from about **2.2 to 4.1**. The paper's dataset comparison table gives full statistics alongside real Greenland snow-radar and depth-sounder datasets.

<!-- TODO: add a figure with one example per category: docs/categories.png -->

---

## Dataset splits

| Subset | Size | Used for |
|---|---|---|
| `tracelink_set/` | 400 radargrams (100 per category) | Fragment-linking evaluation |
| `xcheck_set/wide/` | 150 wide radargrams | Ground truth for the cross-tile check |
| `xcheck_set/tiles/` | 600 tiles (each wide radargram cropped into 4 adjacent tiles) | XCheck consistency evaluation |

---

## File format

Each radargram is stored as one HDF5 file:

```
synthetic_radargram_output_<bucket><NNN>.h5
```

Example: `synthetic_radargram_output_close_To_real003.h5`

### HDF5 structure

```
<file>.h5
├── data/
│   ├── mask                    (H, W)  uint8   0 = background, 1 = layer pixel
│   └── layer_id_map            (H, W)  int32   0 = background, 1..K = layer ID (top to bottom)
├── derived/
│   ├── centerline              (H, W)  uint8   one-pixel centerline of every layer
│   └── skeleton_layer_id_map   (H, W)  int32   layer ID on the centerline pixels
├── tables/
│   ├── fragments               (N, 7)  int64   one row per fragment
│   └── layers                  (K, 2)  int64   one row per layer
└── metadata/                   (group attributes only, no datasets)
```

- Image arrays are 1600 x 1600 and gzip-compressed.
- Layers are one pixel thick, so `derived/centerline` is identical to `data/mask`, and `derived/skeleton_layer_id_map` is identical to `data/layer_id_map`. The `derived/` group is kept so the format stays the same if thicker layers are added later.
- `data/mask` is exactly the set of pixels where `layer_id_map > 0`.

<!-- TODO: confirm the image size of wide radargrams and tiles, and update the line above if it differs -->

### `tables/fragments`

| Column | Meaning |
|---|---|
| `fragment_id` | Fragment index **within its layer** (restarts at 1 for each layer) |
| `layer_id` | Parent layer ID (matches `layer_id_map`) |
| `col_start` | First column of the fragment |
| `col_end` | Last column of the fragment (inclusive) |
| `row_min` | Top row of the fragment |
| `row_max` | Bottom row of the fragment |
| `pixel_count` | Number of pixels in the fragment |

A fragment is uniquely identified by the pair `(layer_id, fragment_id)`, not by `fragment_id` alone.

### `tables/layers`

| Column | Meaning |
|---|---|
| `layer_id` | Layer ID, 1 to K, ordered top to bottom |
| `num_fragments` | Number of fragments the layer is broken into |

Column names are also stored as a JSON list in each table's `columns` attribute.

### `metadata` attributes

| Attribute | Type | Meaning |
|---|---|---|
| `bucket` | str | Category, e.g. `close_To_real0` (see the category table above) |
| `type` | str | `normal` for standard radargrams, [wide value] for wide radargrams |
| `width` | int | Image width in pixels |
| `depth` | int | Image height in pixels |
| `layers_requested` | int | Number of layers asked for |
| `layers_generated` | int | Number of layers that fit inside the image |
| `total_fragments` | int | Total fragments in the file |
| `fragment_ratio` | float | Mean fragments per layer (`total_fragments / layers_generated`) |
| `tilt_angle` | float | Terrain tilt in degrees (0 for normal radargrams) |
| `random_seed` | int | Seed used for generation |

<!-- TODO: open a wide file and replace [wide value] with its exact `type` string -->

### Integrity guarantees

Every file satisfies these checks:

- The sum of `pixel_count` in `tables/fragments` equals the number of layer pixels in `data/mask`.
- For every layer, the pixel count in `layer_id_map` equals the sum of its fragments' `pixel_count`.
- `num_fragments` in `tables/layers` matches the number of rows for that layer in `tables/fragments`.
- `total_fragments` and `layers_generated` in the metadata match the tables.

---

## Repository layout

```
SyntheIce-Dataset/
├── generator/            # SyntheIce generator (Algorithm 1)
├── configs/              # Parameter settings for each category
├── data/
│   ├── tracelink_set/    # 400 radargrams, 4 categories
│   └── xcheck_set/
│       ├── wide/         # 150 wide radargrams
│       └── tiles/        # 600 cropped tiles
├── scripts/              # Regenerate the dataset, run integrity checks, compute statistics
└── docs/                 # Figures and format details
```
<!-- TODO: match this tree to your actual folders -->

---

## Quick start

```bash
git clone https://github.com/USER/SyntheIce-Dataset.git
cd SyntheIce-Dataset
pip install h5py numpy
```

Load one radargram:

```python
import json
import h5py

path = "synthetic_radargram_output_close_To_real003.h5"

with h5py.File(path, "r") as f:
    mask      = f["data/mask"][:]            # (H, W) binary mask
    layer_ids = f["data/layer_id_map"][:]    # (H, W) layer ID per pixel
    fragments = f["tables/fragments"][:]     # (N, 7)
    layers    = f["tables/layers"][:]        # (K, 2)
    frag_cols = json.loads(f["tables/fragments"].attrs["columns"])
    meta      = dict(f["metadata"].attrs)

print(meta["bucket"], meta["layers_generated"], "layers,",
      meta["total_fragments"], "fragments")
```

Get all pixels of one fragment:

```python
import numpy as np

layer_id, fragment_id = 1, 2
row = fragments[(fragments[:, 0] == fragment_id) & (fragments[:, 1] == layer_id)][0]
_, _, c0, c1, r0, r1, _ = row
sub = layer_ids[r0:r1 + 1, c0:c1 + 1] == layer_id   # col_end and row_max are inclusive
```

---

## Known limitations

- **Annotations only, not radar images.** The dataset provides layer annotations and their exact ground truth. It does not include simulated radar backscatter images.
- **Mild tilt.** Synthetic terrain tilt is small compared with some real Greenland layers, so steeply dipping layers are under-tested.
- **Metadata is a summary, not a full recipe.** Each file stores its seed, layer count, tilt and summary statistics. The spacing, break and jitter settings for each category are in `configs/`, not in the individual files.
- **Pixel-based statistics.** Values like fragment length depend on image resolution, so compare them as trends within the dataset, not as absolute matches to other datasets.

---

## Citation

If you use this dataset, please cite:

M. B. Hassan, B. A. Tama, S. Purushotham, and V. P. Janeja, "SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction," in Proc. 2026 IEEE International Conference on Big Data (BigData), Phoenix, AZ, USA, Dec. 2026, to appear

```bibtex
@inproceedings{hassan2026syntheice,
  title     = {{SyntheIce}: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction},
  author    = {Hassan, Muhammad Behroze and Tama, Bayu Adhi and Purushotham, Sanjay and Janeja, Vandana P.},
  booktitle = {2026 IEEE International Conference on Big Data (BigData)},
  address   = {Phoenix, AZ, USA},
  month     = dec,
  year      = {2026}
}
```

---

## License

- **Data:** [CC BY 4.0]
- **Code:** [MIT]


## Acknowledgments
This work has been funded by the NSF HDR Institute for Harnessing Data and Model Revolution in the Polar Regions (iHARP), Award #2118285. We acknowledge Dr. Nicholas D. Holschuh for providing ice layer expert-labeled dataset.
