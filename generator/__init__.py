"""SyntheIce: synthetic englacial-layer annotation generator (Algorithm 1)."""

from .syntheice import (FRAGMENT_COLUMNS, LAYER_COLUMNS, apply_layer_breaks,
                        apply_radar_tilt, build_tables, extract_layer_fragments,
                        generate_synthetic_radargram, make_skeleton_layer_id_map,
                        sample_radargram)
from .io import (load_dataset_config, radargram_filename, read_h5, tile_filename,
                 write_png, write_radargram_h5, write_tile_h5)

__all__ = [
    "FRAGMENT_COLUMNS", "LAYER_COLUMNS",
    "apply_layer_breaks", "apply_radar_tilt", "build_tables",
    "extract_layer_fragments", "generate_synthetic_radargram",
    "make_skeleton_layer_id_map", "sample_radargram",
    "load_dataset_config", "radargram_filename", "read_h5", "tile_filename",
    "write_png", "write_radargram_h5", "write_tile_h5",
]
