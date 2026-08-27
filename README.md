# AI-Based Early Warning & Landslide Risk Monitoring in NER

A working prototype of an AI early-warning system that continuously monitors landslide-prone
slopes across India's **North Eastern Region (NER)**, predicts risk in real time, forecasts the
next 24 hours, explains *why* a slope is unsafe, and auto-dispatches actionable alerts to
district authorities.

Built for **Smart India Hackathon**.

---

## The Problem

The NER accounts for a disproportionate share of India's landslide fatalities. Extreme monsoon
rainfall (Cherrapunji), young fragile Himalayan lithology, Seismic Zone V, aggressive road-cutting
and deforestation combine so that slopes fail with almost no warning — cutting off NH-10, the
Tupul rail corridor and entire districts. Existing monitoring is manual, fragmented and reactive.

## The Solution

| Layer | What it does |
|---|---|
| **Data sources** | IMD/AWS rain gauges · IoT piezometers & tiltmeters · Sentinel-1 InSAR displacement · GSI landslide inventory · DEM-derived slope & NDVI |
| **Ingestion** | Streaming telemetry, validation, feature engineering (rainfall accumulations, 14-day Antecedent Precipitation Index) |
| **AI engine** | Gradient-boosted ensemble → 4-level risk class + continuous 0-100 risk index + 6/12/24h forecast |
| **Explainability** | Rule-grounded contributing factors so a district officer sees the reasoning, not a black box |
| **Dissemination** | Live dashboard · auto-escalation alert feed (SMS/IVR-ready) · recommended action per risk level |

### Risk levels & protocol
| Level | Action |
|---|---|
| 🟢 Low | Routine monitoring |
| 🟡 Moderate | Increase polling, advise caution |
| 🟠 High | Public warning, pre-position NDRF/SDRF, restrict night travel |
| 🔴 Critical | Evacuate slopes, close highway segment, activate district EOC |

---

## Model Performance

Trained on 24,000 samples across 15 hydro-meteorological, geotechnical and terrain features.

| Metric | Score |
|---|---|
| Accuracy | **78.6 %** |
| ROC-AUC (one-vs-rest) | **0.937** |
| 5-fold CV accuracy | 78.5 % ± 0.5 % |
| Critical-class F1 | 0.782 |

Top predictors: pore-water pressure, displacement rate, NDVI, slope angle, 24h rainfall.

> The prototype trains on a **physically-grounded synthetic dataset** (`ml/generate_dataset.py`)
> that encodes accepted geotechnical relationships, since real-time IMD/ISRO feeds are not publicly
> open. The model, API and dashboard are production-shaped — swapping in live feeds requires only
> replacing the ingestion layer in `backend/simulator.py`.

---

## Monitored Sites

12 high-risk slopes across all 8 NER states — Gangtok NH-10, Mangan, Guwahati Hills, Haflong,
Cherrapunji, Shillong–Jowai, Tawang Pass, Itanagar Ridge, Noney–Tupul, Aizawl–Durtlang,
Kohima–Zubza, Jampui Hills.

---

## Quick Start

```bash
./run.sh
```

Then open **http://localhost:8000**.

Manual steps:
```bash
pip install -r requirements.txt
python ml/generate_dataset.py     # build dataset
python ml/train_model.py          # train + save model & metrics
cd backend && uvicorn main:app --reload --port 8000
```

---

## Dashboard

- **Dashboard** — live risk map of the NER, ranked site list, per-site telemetry, forecast, explainability and trend sparkline
- **Alerts** — automated escalation feed with dispatch-ready messages
- **What-If Simulator** — 15 sliders + presets (Monsoon Cloudburst / Dry Season / Post-Seismic) to stress-test the model live
- **Model** — accuracy, ROC-AUC, feature importance, confusion matrix, architecture diagram

---

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Service status |
| `GET /api/sites` | Live risk for all monitored slopes |
| `GET /api/summary` | Network KPIs and per-state averages |
| `GET /api/site/{id}` | Detail + forecast + history + factors |
| `GET /api/alerts` | Escalation alert feed |
| `POST /api/predict` | Score any custom scenario |
| `GET /api/metrics` | Model evaluation metrics |

Example:
```bash
curl -X POST localhost:8000/api/predict -H 'Content-Type: application/json' \
  -d '{"rain_24h":310,"api_14d":700,"soil_moisture":92,"pore_pressure":115,"displacement_rate":7.5,"slope":42}'
# -> {"level":"Critical","confidence":0.999,"risk_score":95.0, ...}
```

---

## Project Structure

```
├── ml/
│   ├── generate_dataset.py   # physics-grounded data generator
│   └── train_model.py        # training + evaluation
├── backend/
│   ├── main.py               # FastAPI service
│   ├── simulator.py          # live telemetry ingestion layer
│   └── districts.py          # NER site geo/terrain profiles
├── frontend/                 # dashboard (map, alerts, simulator, model)
├── models/                   # trained model + metrics.json
├── data/                     # training dataset
└── run.sh
```

## Impact

Early warning of even a few hours enables evacuation and highway closure before failure —
protecting lives, the NH-10 / Tupul lifelines, and reducing post-disaster relief costs.
Scalable to the entire Himalayan belt with the same architecture.
