# CarbonKarma dMRV — Frontend

Production-grade React dashboard for the CarbonKarma Carbon Intelligence Platform.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment (optional — defaults proxy to localhost:5000)
cp .env.example .env

# 3. Start backend (in a separate terminal)
cd ../backend && python app.py

# 4. Start frontend
npm run dev
# → Open http://localhost:3000
```

## Features

| Panel | Endpoint | Description |
|-------|----------|-------------|
| 🛰 Satellite | `/satellite-data` | SAR water prob, NDVI, LST, Weather charts |
| 🔀 Fusion | `/fusion-data` | All layers merged, pixel-level inspection |
| 🌾 AWD | `/awd-status` | Cycle timeline, irrigation vs rain events |
| 🔥 Methane | `/methane` | CH₄ flux charts, reduction %, category |
| 🛡 Verification | `/verification` | dMRV checks, GOLD/SILVER/BRONZE/FAILED |
| 💰 Credits | `/credits` | Credit calculation, wallet, impact metrics |
| 📊 Analytics | `/analytics` | 9-module dashboard (score, trends, alerts…) |
| 🤖 AI Insights | `/llm-insights` | Free-form queries, certificates, explanations |
| 📄 Report | `/report` | PDF report generation and download |

## Map Controls

- **Draw tool** (top-right on map): Draw polygon → auto-sets farm boundary + GeoJSON
- **Click**: Click map location → sets lat/lon
- **Enter Coords**: Manual lat/lon input
- **Auto-detect**: Browser geolocation

## Fallback System

If the backend is unavailable or returns an error:
1. **Cache hit**: Returns the last successful response from memory
2. **Synthetic data**: Generates realistic physics-informed demo data

The UI never breaks or shows empty states — fallback data is visually identical to live data, with a `◎ DEMO` indicator in the sidebar.

## Multilingual Support

Use the language switcher at the bottom of the sidebar:
- **EN** — English
- **हि** — Hindi  
- **म** — Marathi

## Tech Stack

- **React 18** + **Vite 5** — Build tooling
- **Tailwind CSS** — Utility-first styling with custom earth/sky palette
- **Framer Motion** — Animations and transitions
- **Leaflet** + **leaflet-draw** — Interactive map with polygon drawing
- **Recharts** — Time-series, bar, and radial charts
- **Axios** — API client with retry + cache
- **i18next** — EN/HI/MR localisation
- **lucide-react** — Icon library

## Folder Structure

```
src/
├── App.jsx                    Root component
├── index.css                  Tailwind + glassmorphism utilities
├── main.jsx                   Entry point
├── components/
│   ├── charts/
│   │   ├── BarMetric.jsx      Animated progress bars
│   │   ├── GaugeChart.jsx     Radial gauge
│   │   └── TimeSeriesChart.jsx  Recharts line charts
│   ├── layout/
│   │   ├── Sidebar.jsx        Navigation + language switcher
│   │   └── TopBar.jsx         Header with status indicator
│   ├── map/
│   │   ├── FarmMap.jsx        Leaflet map + draw controls + heatmaps
│   │   └── LocationControls.jsx  Lat/lon input + geolocation
│   ├── panels/
│   │   ├── SatellitePanel.jsx
│   │   ├── FusionPanel.jsx
│   │   ├── AWDPanel.jsx
│   │   ├── MethanePanel.jsx
│   │   ├── VerificationPanel.jsx
│   │   ├── CreditsPanel.jsx
│   │   ├── AnalyticsPanel.jsx
│   │   ├── AIPanel.jsx
│   │   └── ReportPanel.jsx
│   └── ui/
│       ├── LoadingSpinner.jsx
│       ├── MetricCard.jsx
│       └── StatusBadge.jsx
├── context/AppContext.jsx      Global state
├── hooks/useApiData.js         Data fetch hook
├── i18n/
│   ├── i18n.js
│   └── locales/{en,hi,mr}.json
├── pages/Dashboard.jsx         Main page layout
├── services/api.js             Centralized API layer
└── utils/fallbackData.js       Synthetic data generator
```

## Production Build

```bash
npm run build
# Output in ./dist — serve with any static host
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `` (proxy) | Backend URL. Empty = proxy via Vite |
