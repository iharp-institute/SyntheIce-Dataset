# SyntheIce-Synthetic-Radargram-Annotation-Benchmark-for-Englacial-Layer-Reconstruction
SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction. Algorithmic/procedural radargram annotation generation with pixel-exact layer masks, fragment-level annotations, and full generation metadata, built to train and evaluate layer-tracing models on Greenland ice-sheet radar data.

Official code and dataset for the paper *SyntheIce: A Synthetic Radargram Annotation
Benchmark for Englacial Layer Reconstruction* [IEEE International Conference on Big Data (BigData) 2026, Phoenix, Arizona, USA, Dec, 2026].

## Why SyntheIce
Deep learning models for englacial layer tracing need dense, accurate labels. Real
radargram annotations are sparse, broken into fragments, and costly to produce by hand.
SyntheIce fixes this by generating synthetic radargrams together with exact ground
truth, so models can be trained and tested against labels that are known to be correct.

## What's inside
- **Generator code:** a Algorithmic/procedural pipeline that renders different complexities of radargrams calibrated
  against real CReSIS Greenland radar frames
- **Layer masks:** binary englacial layer masks, accurate to within 1 pixel
- **Annotation tables:** per-layer and per-fragment records
- **Metadata:** a JSON file per sample with every generation parameter, so any sample
  can be reproduced exactly
- **Evaluation tools:** scripts to benchmark layer-tracing models on the dataset

## Dataset at a glance
| Item | Value |
|---|---|
| Number of radargrams | [N] |
| Image size | [H x W] |
| Layers per radargram | [range] |
| Format | [HDF5 / PNG + JSON] |
| Size on disk | [GB] |

## Dataset access
The dataset is also available here. 

## Citation
M. B. Hassan, B. A. Tama, S. Purushotham, and V. P. Janeja, "SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction," in Proc. 2026 IEEE International Conference on Big Data (BigData), Phoenix, AZ, USA, Dec. 2026, to appear

## Acknowledgments
This work is supported by the NSF HDR Institute for Harnessing Data and Model
Revolution in the Polar Regions (iHARP).
