# dMRV Engine — Scientific Backend

Modular Python backend for digital Monitoring, Reporting & Verification of paddy rice methane reductions. This repository contains the **ingestion, calculation, and fusion pipelines** only — no frontend, no Web3, no blockchain.

## Architecture

```
dmrv_engine/
├── config/
│   └── settings.py              Pydantic-settings env loader with secret redaction
├── utils/
│   └── http.py                  Shared retry-enabled HTTP client
├── services/
│   └── soilgrids.py             ISRIC SoilGrids v2.0 client (SOC + clay)
├── pipelines/
│   ├── optical_indices.py       EVI, NDVI, NDWI (PyTorch + NumPy)
│   └── fusion_weighting.py      SAR ↔ optical redundancy resolver
├── validation/
│   └── sentinel5p_simulator.py  TROPOMI macro-validation emulator
├── .env.example
├── requirements.txt
└── README.md
```

## Module map against the 5 requirements

| Requirement | Module | Key symbols |
|---|---|---|
| 1. Env & API security | `config/settings.py` | `DMRVSettings`, `get_settings()` — uses `SecretStr`, `.redacted_dict()` for safe logging |
| 2. SoilGrids integration | `services/soilgrids.py` | `SoilGridsService.fetch(lat, lon)` → `SoilProperties` dataclass |
| 3. EVI + NDWI | `pipelines/optical_indices.py` | `compute_evi()`, `compute_ndwi()`, `compute_all_indices()` |
| 4. SAR ↔ optical fusion | `pipelines/fusion_weighting.py` | `compute_fusion_weights()`, `fuse_water_detection()`, `REGION_PROFILES` |
| 5. S5P macro-validation | `validation/sentinel5p_simulator.py` | `Sentinel5PSimulator.validate()` → `ValidationResult` |

## Install & run

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in Sentinel Hub + Copernicus credentials as needed
```

## Scientific design notes

### EVI over NDVI
NDVI saturates at LAI ≈ 3, which is typical for heading-stage rice.
EVI (Huete et al., 2002) with the blue-band correction remains
sensitive up to LAI ≈ 5–6 and is essential for dense canopies:

> `EVI = 2.5 × (NIR − RED) / (NIR + 6·RED − 7.5·BLUE + 1)`

### Fusion weighting philosophy
The `compute_fusion_weights` function applies a **smooth logistic
transition** centered at the regional EVI saturation threshold.
Hard-gating at EVI = 0.8 would cause pixel-level discontinuities;
instead, trust in SAR rises smoothly as the canopy thickens:

| EVI | Optical weight | SAR weight |
|---|---|---|
| 0.0 | 1.0 | 0.5 |
| 0.5 | 0.7 | 0.7 |
| 0.8 | 0.3 | 1.0 |
| 1.0 | 0.0 | 1.0 |

### Regional calibration
`REGION_PROFILES` exposes four defensible priors (south_asia,
southeast_asia, east_asia, sub_saharan) plus a `default`. Each has
its own `sar_sensitivity`, `evi_saturation`, and `vh_vv_water_db`.
These are starting values — production deployments should re-calibrate
using local historical SAR histograms against ground-truth flood masks.

### S5P simulator bounds
The TROPOMI simulator uses a first-order mass-balance emission →
column conversion (`CH4_MASS_TO_PPB_FACTOR = 0.0042 ppb per kg/ha/season`).
This approximation is grounded in Lauvaux et al. (2022) and Varon et al.
(2018) but is not a substitute for real plume-detection methods
(wind-corrected 2D Gaussian fits, background-field subtraction). The
simulator's *interface* matches what a real pipeline would return —
replace the `validate()` implementation when moving to production.

## Limitations (honest)

- **SoilGrids**: REST API only returns SOC and clay; bulk density and sand are opportunistic. Network failures → `SoilProperties.is_complete == False`, never an exception.
- **Fusion weights**: calibrated for *paddy rice*; other crop systems need new profiles.
- **S5P simulator**: outputs are statistically realistic but not physically derived from true atmospheric transport. Use only for development; replace with real TROPOMI pipeline before any production validation claim.

## Testing

```bash
python -m pytest tests/ -v
```

Smoke tests cover all 5 modules end-to-end including determinism checks for the simulator.
