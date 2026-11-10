# SyntheIce: A Synthetic Radargram Annotation Benchmark For Englacial Layer Reconstruction
SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction. Algorithmic/procedural radargram annotation generation with pixel-exact layer masks, fragment-level annotations, and full generation metadata, built to train and evaluate layer-tracing models on Greenland ice-sheet radar data.

Official code and dataset for the paper *SyntheIce: A Synthetic Radargram Annotation
Benchmark for Englacial Layer Reconstruction* 

## Paper

The paper has been accepted in the proceedings of IEEE International Conference on Big Data (BigData) 2026, Phoenix, Arizona, USA, Dec, 2026.

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
- **TraceLink Algorithm:** Reconstructing fragments of layers back together to make layers consistent is a radargram mask.
- **Evaluation:** The Dataset is evaluated on Consistency validation metric 'XCheck' for the wide radargrams. Tracelink is evaluated on real data annotations to reconstruct the fragments, The other metrics used are F1 score, Recall, Precision and Mean IoU.
## Dataset at a glance
| Item | Value |
|---|---|
| Number of radargrams | [600] |
| Image size | [1600 x 1600],[2000 x 3000] |
| Categories | [Close-to-synthetic, Mid-Level, Close-to-real, Noisy-Level] |
| Layers per radargram | [Category Dependent] |
| Format | [HDF5 / PNG + JSON] |
| Size on disk | [6 GB] |

## Dataset access
The dataset is available here. 

## Citation
M. B. Hassan, B. A. Tama, S. Purushotham, and V. P. Janeja, "SyntheIce: A Synthetic Radargram Annotation Benchmark for Englacial Layer Reconstruction," in Proc. 2026 IEEE International Conference on Big Data (BigData), Phoenix, AZ, USA, Dec. 2026, to appear

## Acknowledgments
This work has been funded by the NSF HDR Institute for Harnessing Data and Model Revolution in the Polar Regions (iHARP), Award #2118285. We acknowledge Dr. Nicholas D. Holschuh for providing ice layer expert-labeled dataset.
