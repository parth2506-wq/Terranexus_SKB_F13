# Terranexus_SKB_F13
Sankalp Bharat Hackathon, SVPCOE, Nagpur
# 🌍 TerraNexus — dMRV Carbon Intelligence Engine

## 🚀 Overview

**TerraNexus** is an AI-powered, multi-modal **digital Monitoring, Reporting, and Verification (dMRV)** platform designed to transform carbon governance in agriculture.

The system leverages **satellite data fusion**, **deep learning**, and **weather intelligence** to provide **cloud-proof monitoring**, **methane emission estimation**, and **trust-based carbon credit verification** at the farm level.

---

## 🎯 Problem Statement

Current carbon markets lack reliable farm-level MRV systems due to:

* ❌ Dependence on manual reporting
* ❌ Cloud obstruction in optical satellite data
* ❌ High verification cost and delays
* ❌ Lack of trust in carbon credits

TerraNexus solves this by enabling:

✅ Automated monitoring using SAR + Optical data
✅ Accurate AWD (Alternate Wetting & Drying) detection
✅ Methane emission estimation
✅ Transparent and auditable verification

---

## 🧠 Core Features

### 🛰️ Multi-Sensor Satellite Fusion

* Sentinel-1 (SAR) → Water detection (cloud-proof)
* Sentinel-2 (Optical) → NDVI (crop health)
* Sentinel-3 / Landsat → Land Surface Temperature
* Weather (Open-Meteo) → Rainfall & temperature context

---

### 🔥 Fusion Intelligence Engine

* Combines all satellite + weather data
* Generates pixel-level insights:

  * Water level
  * NDVI
  * Temperature
  * Rainfall
  * Soil moisture
  * Flood type (rain vs irrigation)

---

### 🌾 AWD Detection (AI-powered)

* CNN + LSTM architecture
* Detects wetting-drying cycles over time
* Identifies sustainable irrigation practices

---

### 🌡️ Methane Emission Estimation

* Predicts CH₄ emissions using:

  * Water levels
  * Crop density (NDVI)
  * Temperature
  * Weather patterns

---

### 🏆 Verification & Trust Engine

* Validates farming practices
* Provides:

  * Confidence score
  * Explainable reasoning
  * Satellite-backed proof

---

### 🟢 Carbon Credits & Certification

* Calculates carbon credit earnings
* Generates:

  * 🌿 Green Compliance Badge
  * Verified low-methane farming certificate

---

### 🤖 AI Explanation Layer

* Powered by OpenRouter (LLM)
* Generates:

  * Reports
  * Insights
  * Explanations

---

### 🧠 Memory & Insights

* ChromaDB + LangChain
* Stores:

  * Historical data
  * Reports
  * Predictions

---

## 🧩 System Architecture

```
Satellite Data (Sentinel 1/2/3, Landsat)
        + Weather Data (Open-Meteo)
                        ↓
                Data Preprocessing
                        ↓
            CNN (Spatial Feature Extraction)
                        ↓
            LSTM (Temporal Pattern Detection)
                        ↓
              Fusion Intelligence Engine
                        ↓
      AWD Detection + Methane Estimation
                        ↓
     Verification + Carbon Credit System
                        ↓
            API Layer (Flask Backend)
                        ↓
          Frontend Dashboard (React)
```

---

## ⚙️ Tech Stack

### 🔹 Backend

* Python (Flask)
* PyTorch (CNN + LSTM)
* Rasterio / GDAL
* OpenCV

### 🔹 AI & Data

* Multi-modal data fusion
* Time-series modeling
* NDVI computation

### 🔹 APIs & Services

* Open-Meteo (weather)
* OpenRouter (LLM)

### 🔹 Database

* ChromaDB + LangChain (vector storage)

### 🔹 Frontend (Planned)

* React.js
* Mapbox / Leaflet
* Recharts

---

## 📊 API Endpoints

| Endpoint          | Description                  |
| ----------------- | ---------------------------- |
| `/satellite-data` | Raw satellite + weather data |
| `/fusion-data`    | Combined processed data      |
| `/awd-status`     | AWD detection result         |
| `/methane`        | Methane emission prediction  |
| `/verification`   | Trust + explanation          |
| `/credits`        | Carbon credit system         |
| `/report`         | AI-generated report          |

---

## 🧪 How to Run the Backend

```bash
# Clone the repository
git clone <repo-url>
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

---

## 🔍 Example Output

### Fusion Data

```
Water Level: 0.82
NDVI: 0.67
Temperature: 32°C
Rainfall: 0 mm
Flood Type: Irrigation
AWD Status: Active
```

---

### Methane Output

```
Methane Emission: 1.8 kg CH4 / hectare / day
Category: Medium
Reduction: 32%
```

---

### Verification

```
Status: VERIFIED ✅
Confidence: 91%
Explanation:
Flooding detected without rainfall → irrigation confirmed
```

---

### Carbon Credits

```
Credits Earned: +12.5 CO₂e
Total Balance: 48.7
```

---

## 👨‍💻 Team TerraNexus

* **Aniruddha Akhare**
* **Parth Deshmukh**
* **Abhang Vyavhare**
* **Sarthak Pundlik**
* **Pranav Gujar**

---

## 🌟 Vision

To build a **transparent, scalable, and AI-driven carbon governance system** that empowers farmers, builds trust in carbon markets, and accelerates climate-positive agriculture.

---

## 🏁 Final Note

TerraNexus is not just a project — it is a step toward **data-driven sustainability and climate accountability**.

---

**Built with ❤️ for innovation, sustainability, and impact.**
