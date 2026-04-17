# CarbonKarma dMRV — API Testing Guide
# All endpoints: POST with JSON body, GET with query params
# Base URL: http://localhost:5000
# Start server: cd backend && python app.py

## ── PART 1 ENDPOINTS ─────────────────────────────────────────────────────

### GET /health
curl http://localhost:5000/health

### GET / (endpoint index)
curl http://localhost:5000/

### POST /satellite-data — Raw satellite ingestion
curl -X POST http://localhost:5000/satellite-data \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 10,
    "step_days": 10
  }'

### POST /satellite-data — With GeoJSON polygon
curl -X POST http://localhost:5000/satellite-data \
  -H "Content-Type: application/json" \
  -d '{
    "geojson": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[80.25,13.07],[80.28,13.07],[80.28,13.10],[80.25,13.10],[80.25,13.07]]]
      }
    },
    "n_steps": 8,
    "step_days": 10
  }'

### POST /fusion-data — Multi-source fusion with heatmaps
curl -X POST http://localhost:5000/fusion-data \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 10,
    "step_days": 10,
    "include_heatmaps": true
  }'

### POST /awd-status — AWD cycle detection
curl -X POST http://localhost:5000/awd-status \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 14,
    "step_days": 7
  }'

### POST /methane — Methane flux estimation
curl -X POST http://localhost:5000/methane \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 12,
    "step_days": 10
  }'


## ── PART 2 ENDPOINTS ─────────────────────────────────────────────────────

### POST /verification — dMRV verification (GOLD/SILVER/BRONZE/FAILED)
curl -X POST http://localhost:5000/verification \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 14,
    "step_days": 7,
    "farm_id": "farm_001"
  }'

### POST /credits — Compute + issue carbon credits
curl -X POST http://localhost:5000/credits \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 14,
    "step_days": 7,
    "farm_id": "farm_001",
    "area_ha": 4.5
  }'

### GET /credits/wallet — Current balance + transaction history
curl "http://localhost:5000/credits/wallet?farm_id=farm_001"

### POST /credits/retire — Retire credits for certificate
curl -X POST http://localhost:5000/credits/retire \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": "farm_001",
    "amount": 2.5,
    "reason": "certificate_issuance"
  }'

### POST /analytics — Full 9-module analytics suite
curl -X POST http://localhost:5000/analytics \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 12,
    "step_days": 10,
    "farm_id": "farm_001",
    "region": "south_asia",
    "include_heatmaps": true
  }'

### POST /report — Generate full MRV report
curl -X POST http://localhost:5000/report \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 12,
    "farm_id": "farm_001"
  }'

### GET /report/list — List reports for a farm
curl "http://localhost:5000/report/list?farm_id=farm_001"

### GET /report/download — Download a generated report
curl "http://localhost:5000/report/download?path=carbonkarma_farm_001_20260101_120000.pdf" \
  -o report.pdf

### POST /llm-insights — Free-form AI query about the farm
curl -X POST http://localhost:5000/llm-insights \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 10,
    "farm_id": "farm_001",
    "query": "How can I improve my carbon credits and AWD compliance?"
  }'

### POST /llm-insights/explain — Verbose verification explanation
curl -X POST http://localhost:5000/llm-insights/explain \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 12,
    "farm_id": "farm_001"
  }'

### POST /llm-insights/alerts — LLM-enriched alert narratives
curl -X POST http://localhost:5000/llm-insights/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 10,
    "farm_id": "farm_001"
  }'

### POST /llm-insights/certificate — Generate certificate text
curl -X POST http://localhost:5000/llm-insights/certificate \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 13.0827,
    "lon": 80.2707,
    "n_steps": 12,
    "farm_id": "farm_001",
    "area_ha": 4.5
  }'


## ── EXPECTED RESPONSES ───────────────────────────────────────────────────

### /verification response shape:
# {
#   "status": "success",
#   "farm_id": "farm_001",
#   "location": { "lat": 13.08, "lon": 80.27, "bbox": [...] },
#   "verification": {
#     "status": "verified",
#     "level": "GOLD" | "SILVER" | "BRONZE" | "FAILED",
#     "confidence": 0.87,
#     "data_integrity": { "checks_passed": 6, "checks_total": 7 },
#     "checks": [{ "name": "...", "passed": true, "score": 0.9, "detail": "..." }],
#     "explanation": "...",
#     "fingerprint": "sha256hex"
#   },
#   "llm_explanation": { "explanation": "...", "source": "template" | "llm" },
#   "awd_summary": { "awd_status": "active_awd", "cycles": 3 },
#   "methane_summary": { "mean_daily_flux": 210.5, "total_reduction_pct": 47.2 }
# }

### /credits response shape:
# {
#   "status": "success",
#   "credits_earned": 12.45,
#   "usd_value": 186.75,
#   "total_balance": 47.32,
#   "calculation": {
#     "area_ha": 4.5,
#     "season_days": 120,
#     "baseline_kg_ha": 480.0,
#     "actual_kg_ha": 312.4,
#     "reduction_kg_ha": 167.6,
#     "reduction_pct": 34.9,
#     "reduction_co2e_t": 21.04,
#     "credits_earned": 12.45,
#     "verification_level": "SILVER",
#     "verification_multiplier": 0.85
#   },
#   "impact_metrics": {
#     "co2e_reduced_tonnes": 21.04,
#     "water_saved_m3_total": 7560.0,
#     "trees_equivalent": 1002,
#     "car_km_equivalent": 175333
#   }
# }

### /analytics response shape:
# {
#   "farm_score": {
#     "overall_score": 67.2,
#     "water_efficiency": 72.1,
#     "methane_control": 68.5,
#     "awd_compliance": 61.0,
#     "grade": "C"
#   },
#   "comparative_analysis": {
#     "your_flux_mg_m2_day": 248.3,
#     "regional_mean_mg_m2_day": 340.0,
#     "percentile": 71.2,
#     "performance": "above_average"
#   },
#   "historical_trends": { "windows": {...}, "total_records": 12 },
#   "alerts": { "alerts": [{ "type": "METHANE_WARNING", "severity": "HIGH", ... }] },
#   "predictions": {
#     "daily_forecasts": [{ "date": "...", "rainfall_mm": 3.2, "methane_mg_m2_day": 221.4 }],
#     "irrigation_advice": "...",
#     "forecast_horizon_days": 7
#   },
#   "field_segmentation": { "zones": [{...}], "zone_count": 64 },
#   "impact_metrics": { "co2e_reduced_tonnes": 21.04, "water_saved_m3_total": 7560 },
#   "farm_profile": { "farmer_name": "Ravi Kumar", "farm_area_ha": 4.5, ... },
#   "audit_trail": { "events": [{...}] }
# }
