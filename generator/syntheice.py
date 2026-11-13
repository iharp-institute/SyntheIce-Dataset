"""
SyntheIce generator (Algorithm 1 in the paper).

Generates synthetic englacial-layer annotation radargrams with exact,
per-layer ground truth: a binary mask, a layer-identity map, a
per-layer skeleton map, and fragment / layer tables.

Reproducibility note
--------------------
The released dataset was generated with NumPy's legacy global RNG,
seeded once (seed 42) before the first category. Every random draw
below happens in exactly the same order as in the original notebook
(Synthetic_G_FinalScript_April_V5.ipynb). Do not reorder the calls,
switch to ``np.random.default_rng`` or add new random draws, or the
regenerated files will no longer match the released ones.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline
from skimage.morphology import skeletonize

FRAGMENT_COLUMNS = [
    "fragment_id",
    "layer_id",
    "col_start",
    "col_end",
    "row_min",
    "row_max",
    "pixel_count",
]

LAYER_COLUMNS = [
    "layer_id",
    "num_fragments",
]

# Minimum vertical gap (px) between consecutive layers; stops layers crossing.
ENFORCED_GAP = 3


# ----------------------------------------------------------------------
# Step 4a: breaks
# ----------------------------------------------------------------------

def apply_layer_breaks(curve, break_prob,
                       breaks_per_layer=(0, 0),
                       breaks_per_layer_length=(0, 0)):
    """Return (curve, visible). ``visible[x]`` is False inside a break.

    With probability ``1 - break_prob`` the layer stays unbroken.
    Otherwise it gets ``breaks_per_layer`` gaps (inclusive range), each
    ``breaks_per_layer_length`` columns long (inclusive range). Gaps may
    overlap.
    """
    visible = np.ones_like(curve, dtype=bool)

    if np.random.rand() > break_prob:
        return curve, visible

    num_breaks = np.random.randint(breaks_per_layer[0],
                                   breaks_per_layer[1] + 1)

    for _ in range(num_breaks):
        start = np.random.randint(0, len(curve) - 10)
        gap_len = np.random.randint(breaks_per_layer_length[0],
                                    breaks_per_layer_length[1] + 1)
        end = min(start + gap_len, len(curve))
        visible[start:end] = False

    return curve, visible


# ----------------------------------------------------------------------
# Steps 1 to 4: one radargram
# ----------------------------------------------------------------------

def generate_synthetic_radargram(
    depth_m,
    distance_pixels,
    num_layers,
    gap_range,
    break_prob,
    jitter_strength,
    depth_range=(50, 1000),
    layer_undulation_scale=0.0,
    breaks_per_layer=(0, 0),
    breaks_per_layer_length=(0, 0),
    allow_partial_layers=False,
    partial_min=0,
    partial_max=0,
):
    """Generate one untilted radargram.

    Returns
    -------
    mask : (H, W) uint8
        1 where a layer pixel is drawn.
    base_depths : (K,) float
        Base depth of every layer that fit above ``depth_range[1]``.
    layer_id_map : (H, W) int32
        Layer ID (1..K, top to bottom) per pixel, 0 = background.
    """
    start_depth, max_depth = depth_range
    min_gap, max_gap = gap_range

    # 1. Base layer depths, surface downward with random spacing.
    base_depths = []
    current_depth = np.random.uniform(start_depth, start_depth + 5)

    for i in range(num_layers):
        if i == 0:
            base_depths.append(current_depth)
        else:
            gap = np.random.uniform(min_gap, max_gap)
            next_depth = current_depth + gap
            if next_depth > max_depth:
                break
            base_depths.append(next_depth)
            current_depth = next_depth

    base_depths = np.array(base_depths)
    if len(base_depths) == 0:
        base_depths = np.array([start_depth + 10])

    mask = np.zeros((depth_m, distance_pixels), dtype=np.uint8)
    layer_id_map = np.zeros((depth_m, distance_pixels), dtype=np.int32)

    # 2. Shared deformation field: one zero-mean cubic spline that every
    #    layer follows, so layers bend together as in real ice.
    num_knots = np.random.randint(8, 15)
    x_knots = np.linspace(0, distance_pixels - 1, num_knots)
    y_knots = np.random.randn(num_knots) * jitter_strength
    spline = CubicSpline(x_knots, y_knots)
    shared_undulation = spline(np.arange(distance_pixels))
    shared_undulation -= np.mean(shared_undulation)

    previous_curve = None

    for layer_index, depth in enumerate(base_depths, start=1):

        offset = np.random.uniform(-1, 1) * layer_undulation_scale * jitter_strength
        curve = (depth + shared_undulation + offset).astype(float)

        # 3. No crossing: stay at least ENFORCED_GAP px below the layer above.
        if previous_curve is not None:
            curve = np.maximum(curve, previous_curve + ENFORCED_GAP)

        curve = np.clip(curve, 0, depth_m - 1).astype(int)
        previous_curve = curve.copy()

        # 4. Breaks, then optional partial layers (trimmed ends).
        curve, visibility = apply_layer_breaks(
            curve, break_prob, breaks_per_layer, breaks_per_layer_length
        )

        if allow_partial_layers and partial_max > 0:
            if np.random.rand() < 0.5:
                cut = np.random.randint(partial_min, partial_max + 1)
                visibility[:cut] = False
            if np.random.rand() < 0.5:
                cut = np.random.randint(partial_min, partial_max + 1)
                if cut > 0:  # guard: visibility[-0:] would hide the whole layer
                    visibility[-cut:] = False

        # Thickness interpolates from 2 px (top) to 1 px (bottom), but the
        # int() truncation makes it 1 px everywhere in practice. Kept as is
        # so regenerated files match the released data.
        thickness = max(1, int(np.interp(depth, [start_depth, max_depth], [2, 1])))

        for x, y in enumerate(curve):
            if visibility[x]:
                y0 = max(0, y - thickness // 2)
                y1 = min(depth_m, y + (thickness + 1) // 2)
                mask[y0:y1, x] = 1
                layer_id_map[y0:y1, x] = layer_index

    return mask, base_depths, layer_id_map


# ----------------------------------------------------------------------
# Step 5: terrain tilt (wide radargrams only)
# ----------------------------------------------------------------------

def apply_radar_tilt(mask, layer_id_map, tilt_angle):
    """Per-column vertical shift: column c moves down by round(tan(theta) * c).

    Column 0 is unshifted; the rightmost column moves furthest. Content
    pushed below the last row is dropped (deep ice leaving the window).
    """
    slope = np.tan(np.deg2rad(tilt_angle))
    H, W = mask.shape

    tilted_mask = np.zeros_like(mask)
    tilted_layers = np.zeros_like(layer_id_map)
    shifts = np.round(slope * np.arange(W)).astype(np.int32)

    for c, s in enumerate(shifts):
        if s == 0:
            tilted_mask[:, c] = mask[:, c]
            tilted_layers[:, c] = layer_id_map[:, c]
        elif s > 0:
            n = H - s
            if n > 0:
                tilted_mask[s:s + n, c] = mask[:n, c]
                tilted_layers[s:s + n, c] = layer_id_map[:n, c]
        else:
            s_abs = -s
            n = H - s_abs
            if n > 0:
                tilted_mask[:n, c] = mask[s_abs:s_abs + n, c]
                tilted_layers[:n, c] = layer_id_map[s_abs:s_abs + n, c]

    return tilted_mask, tilted_layers


# ----------------------------------------------------------------------
# Step 6: fragments, tables, skeleton
# ----------------------------------------------------------------------

def extract_layer_fragments(layer_id_map, layer_id):
    """Fragments of one layer: maximal runs of columns where the layer is present.

    Returns a list of rows in FRAGMENT_COLUMNS order. ``fragment_id``
    restarts at 1 for every layer; ``col_end`` and ``row_max`` are inclusive.
    """
    fragments = []
    column_presence = np.any(layer_id_map == layer_id, axis=0)
    fragment_id = 1
    start = None

    def _row(s, e, fid):
        rows = np.where(layer_id_map[:, s:e + 1] == layer_id)[0]
        return [fid, int(layer_id), int(s), int(e),
                int(rows.min()), int(rows.max()), int(len(rows))]

    for i, present in enumerate(column_presence):
        if present and start is None:
            start = i
        elif not present and start is not None:
            fragments.append(_row(start, i - 1, fragment_id))
            fragment_id += 1
            start = None

    if start is not None:
        fragments.append(_row(start, len(column_presence) - 1, fragment_id))

    return fragments


def build_tables(layer_id_map):
    """Return (fragments (N,7) int64, layers (K,2) int64, layer_ids)."""
    unique_layers = np.unique(layer_id_map)
    unique_layers = unique_layers[unique_layers > 0]

    fragment_rows, layer_rows = [], []
    for lid in unique_layers:
        frags = extract_layer_fragments(layer_id_map, lid)
        fragment_rows.extend(frags)
        layer_rows.append([int(lid), len(frags)])

    fragments = (np.array(fragment_rows, dtype=np.int64)
                 if fragment_rows else np.empty((0, 7), dtype=np.int64))
    layers = (np.array(layer_rows, dtype=np.int64)
              if layer_rows else np.empty((0, 2), dtype=np.int64))
    return fragments, layers, unique_layers


def make_skeleton_layer_id_map(layer_id_map):
    """Skeletonize each layer separately and keep its integer ID."""
    skel_map = np.zeros_like(layer_id_map, dtype=np.int32)
    ids = np.unique(layer_id_map)
    for lid in ids[ids > 0]:
        skel_map[skeletonize(layer_id_map == lid)] = lid
    return skel_map


# ----------------------------------------------------------------------
# One full sample (random part only)
# ----------------------------------------------------------------------

def sample_radargram(params, is_wide, sizes, tilt_range):
    """Draw one radargram for a category. Consumes the global RNG.

    Parameters
    ----------
    params : dict
        One category config (see configs/categories/*.yaml).
    is_wide : bool
    sizes : dict
        {"normal": (H, W), "wide": (H, W)}
    tilt_range : (float, float)
        Tilt in degrees, drawn uniformly for wide radargrams.

    Returns
    -------
    mask, layer_id_map, base_depths, tilt_angle, (H, W)
    """
    H, W = sizes["wide"] if is_wide else sizes["normal"]

    # Keyword arguments are evaluated left to right, which fixes the draw
    # order: num_layers, then break_prob, then jitter_strength.
    # num_layers uses randint, so its upper bound is EXCLUSIVE.
    mask, base_depths, layer_id_map = generate_synthetic_radargram(
        depth_m=H,
        distance_pixels=W,
        num_layers=np.random.randint(*params["num_layers"]),
        gap_range=tuple(params["gap_range"]),
        break_prob=np.random.uniform(*params["break_prob"]),
        jitter_strength=np.random.uniform(*params["jitter_strength"]),
        depth_range=tuple(params["depth_range"]),
        layer_undulation_scale=params["layer_undulation_scale"],
        breaks_per_layer=tuple(params["breaks_per_layer"]),
        breaks_per_layer_length=tuple(params["breaks_per_layer_length"]),
        allow_partial_layers=params["allow_partial_layers"],
        partial_min=params["partial_min"],
        partial_max=params["partial_max"],
    )

    if is_wide:
        tilt_angle = np.random.uniform(*tilt_range)
        mask, layer_id_map = apply_radar_tilt(mask, layer_id_map, tilt_angle)
    else:
        tilt_angle = 0.0

    return mask, layer_id_map, base_depths, float(tilt_angle), (H, W)
