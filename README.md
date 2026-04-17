# CarbonKarma dMRV Carbon Intelligence Platform — Part 1 Backend

## Overview

Production-grade satellite data ingestion, preprocessing, AI model inference, and geospatial
fusion pipeline for paddy-field methane monitoring and AWD (Alternate Wetting & Drying) detection.

```
backend/
├── app.py                        # Flask application factory + entry point
├── config/
│   └── settings.py               # Environment config (dotenv)
├── routes/
│   ├── satellite.py              # POST /satellite-data
│   ├── fusion.py                 # POST /fusion-data
│   ├── awd.py                    # POST /awd-status
│   └── methane.py                # POST /methane
├── services/
│   ├── sentinel1.py              # SAR backscatter simulator (VV/VH, Lee filter, water prob)
│   ├── sentinel2.py              # Optical simulator (NDVI, true colour, cloud mask)
│   ├── sentinel3_landsat.py      # LST simulator (Kelvin → Celsius → normalised)
│   ├── weather.py                # Open-Meteo API + physics-based mock fallback
│   ├── fusion_engine.py          # Multi-source fusion + CRS alignment + CNN
│   ├── awd_engine.py             # LSTM + rule-based AWD cycle detection
│   ├── methane_engine.py         # Per-step + aggregate methane estimation
│   └── pipeline.py               # Master orchestrator + model registry
├── models/
│   ├── cnn_water.py              # 3-block CNN (PyTorch) + numpy fallback
│   ├── lstm_awd.py               # Bidirectional LSTM (PyTorch) + numpy fallback
│   └── methane_model.py          # GELU MLP (PyTorch) + physics numpy fallback
└── utils/
    ├── geo.py                    # GeoJSON parsing, pixel↔latlon, heatmap grid
    ├── preprocessing.py          # Lee filter, NDVI, LST norm, soil moisture
    ├── time_series.py            # Date range, DataFrame structuring, normalisation
    └── torch_compat.py           # PyTorch / numpy compatibility shim
```

---

## Quick Start

### 1. Clone / create the project

```bash
cd carbonkarma/backend
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**Core dependencies:**
```
flask>=3.0
torch>=2.0          # Falls back to numpy if unavailable
numpy>=1.24
pandas>=2.0
opencv-python-headless>=4.8
requests>=2.31
python-dotenv>=1.0
shapely>=2.0        # Falls back to ray-casting if unavailable
scipy>=1.11
Pillow>=10.0
geojson>=3.0
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env as needed — defaults work out of the box
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `USE_MOCK_WEATHER` | `true` | Use mock weather (no network needed) |
| `MODEL_DEVICE` | `cpu` | `cpu` or `cuda` for GPU |
| `PATCH_SIZE` | `64` | Spatial resolution of simulated patches |
| `PORT` | `5000` | Flask port |

### 5. Run

```bash
python app.py
```

Output:
```
🌾 CarbonKarma Part-1 starting…
Building CNN model on cpu…
Building LSTM model on cpu…
Building Methane model on cpu…
All models loaded and ready.
 * Running on http://0.0.0.0:5000
```

---

## API Reference

All endpoints accept `Content-Type: application/json`.

### `POST /satellite-data`

Returns raw ingested satellite observations (no AI models).

**Request:**
```json
{
  "lat": 13.0827,
  "lon": 80.2707,
  "n_steps": 10,
  "step_days": 10,
  "start_date": "2025-06-01"
}
```

**Response:** Sentinel-1 (VV/VH/water_prob), Sentinel-2 (NDVI), LST, weather per timestep.

---

### `POST /fusion-data`

Full ingestion → preprocessing → CNN → fusion pipeline.

**Request:** Same as `/satellite-data` + `"include_heatmaps": true`.

**Response schema per fusion step:**
```json
{
  "timestamp": "2025-06-01",
  "water_level": 0.82,
  "ndvi": 0.45,
  "temperature": 31.4,
  "rainfall": 12.0,
  "soil_moisture": 0.63,
  "flood_type": "irrigated",
  "cnn_water_score": 0.79,
  "phenology_stage": "tillering"
}
```

Heatmaps (when `include_heatmaps: true`):
```json
{
  "heatmaps": {
    "water_prob": { "label": "...", "data": [{"lat": 13.08, "lon": 80.27, "value": 0.91}, ...] },
    "ndvi":       { ... },
    "lst_norm":   { ... },
    "soil_moisture": { ... }
  }
}
```

---

### `POST /awd-status`

AWD detection using LSTM + rule-based cycle counting.

**Request:** lat/lon + `n_steps` (recommend ≥ 12 for reliable detection).

**Response:**
```json
{
  "awd_status": "active_awd",
  "confidence": 0.71,
  "lstm_signal": 0.78,
  "cycles": 3,
  "irrigation_events": [{"timestamp": "...", "water_level": 0.68, "rainfall_mm": 0.5}],
  "rain_events": [{"timestamp": "...", "water_level": 0.72, "rainfall_mm": 15.2}],
  "flood_dry_sequence": [{"timestamp": "...", "state": "flooded", "water_level": 0.81}],
  "per_step_status": [{"timestamp": "...", "state": "flooded", "flood_type": "irrigated"}]
}
```

**AWD status values:**
- `active_awd` — LSTM signal > 0.65 AND ≥ 2 cycles detected
- `conventional` — signal < 0.35 AND ≤ 1 cycle (continuously flooded)
- `uncertain` — intermediate evidence

---

### `POST /methane`

CH₄ flux estimation using multimodal neural network.

**Request:** lat/lon + GeoJSON polygon (optional) + n_steps.

**GeoJSON polygon input:**
```json
{
  "geojson": {
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[80.25, 13.07], [80.28, 13.07], [80.28, 13.10], [80.25, 13.10], [80.25, 13.07]]]
    }
  },
  "n_steps": 12
}
```

**Response:**
```json
{
  "awd_status": "active_awd",
  "methane": {
    "latest": {
      "timestamp": "2025-09-01",
      "methane": 198.4,
      "category": "medium",
      "reduction_percent": 50.3
    },
    "aggregate": {
      "season_days": 120,
      "mean_daily_flux": 210.5,
      "season_total_kg_ha": 252.6,
      "baseline_kg_ha": 480.0,
      "total_reduction_pct": 47.4,
      "category_distribution": {"low": 3, "medium": 7, "high": 2}
    }
  },
  "units": {
    "methane": "mg CH4 / m² / day",
    "season_total_kg_ha": "kg CH4 / ha",
    "reduction_percent": "% vs conventional flooding baseline"
  }
}
```

**Methane categories:**
- `low` — < 150 mg CH₄/m²/day
- `medium` — 150–350 mg CH₄/m²/day
- `high` — > 350 mg CH₄/m²/day

---

## AI Models

### CNN Water Extractor (`models/cnn_water.py`)
- **Input:** `(B, 2, H, W)` — VV and VH SAR bands
- **Architecture:** 3× ConvBlock (Conv→BN→ReLU→MaxPool) + GlobalAvgPool + Linear projection
- **Output:** `(B, 32)` water feature vector + `(B, 1)` water probability score
- **Fallback:** Multi-scale spatial statistics extracted via numpy/OpenCV

### LSTM AWD Detector (`models/lstm_awd.py`)
- **Input:** `(B, seq_len, 6)` — [water_prob, NDVI, LST_norm, rainfall_norm, VV, VH]
- **Architecture:** 2-layer LSTM + LayerNorm + 2-layer MLP head
- **Output:** `(B, 1)` AWD signal ∈ [0,1] + `(B, 64)` hidden state
- **Fallback:** Exponential-weighted smoothing + variance-based alternation scoring

### Methane Estimator (`models/methane_model.py`)
- **Input:** CNN features (32) + LSTM hidden (64) + scalars (4) = 100 dims
- **Architecture:** 2-layer GELU MLP (128→64) + Softplus flux head + Sigmoid reduction head
- **Output:** CH₄ flux (mg/m²/day) + reduction percentage vs CF baseline
- **Fallback:** Q10 temperature-scaled physics model

---

## Data Pipeline

```
lat/lon or GeoJSON
        │
        ▼
   parse_location()
        │
        ▼
   generate_date_range()
        │
   ┌────┴──────────────────────┐
   │  Parallel ingestion        │
   │  • fetch_sentinel1()       │  SAR backscatter (VV/VH) + Lee filter
   │  • fetch_sentinel2()       │  NDVI + true colour + cloud mask
   │  • fetch_lst()             │  Land Surface Temperature
   │  • fetch_weather()         │  Rainfall + air temp (Open-Meteo / mock)
   └────────────────┬──────────┘
                    │
                    ▼
             run_fusion()
          ┌──────────────────┐
          │ align_to_grid()  │  CRS alignment (resize to patch_size×patch_size)
          │ estimate_soil()  │  SAR + NDVI → soil moisture proxy
          │ run_cnn()        │  → water feature vector + water score
          └────────┬─────────┘
                   │  fused_records (per timestep)
          ┌────────┴──────────┐
          │                   │
          ▼                   ▼
     detect_awd()      estimate_methane()
     ┌──────────┐      ┌──────────────┐
     │ run_lstm │      │ run_methane  │
     │ state-   │      │ _model()     │
     │ machine  │      │ + aggregate  │
     └──────────┘      └──────────────┘
          │                   │
          └─────────┬─────────┘
                    │
              build_heatmaps()
                    │
                    ▼
              JSON Response
```

---

## Testing

Run the built-in end-to-end test suite:

```bash
cd backend
python3 -m pytest tests/ -v          # (add tests/ for Part 2)
```

Or smoke-test manually:

```bash
curl -X POST http://localhost:5000/satellite-data \
  -H "Content-Type: application/json" \
  -d '{"lat": 13.08, "lon": 80.27, "n_steps": 5}'

curl -X POST http://localhost:5000/methane \
  -H "Content-Type: application/json" \
  -d '{"lat": 20.59, "lon": 78.96, "n_steps": 12}'
```

---

## Part 2 (Not implemented here)

- Analytics dashboard (carbon credit calculation)
- LLM-powered agronomic insights
- Report generation (PDF/docx)
- Credit issuance + blockchain anchoring
- Multi-field portfolio management
