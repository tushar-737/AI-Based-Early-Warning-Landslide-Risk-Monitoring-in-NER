"""FastAPI service: AI-Based Early Warning & Landslide Risk Monitoring in NER."""
import os
import json
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from districts import SITES, SITES_BY_ID
from simulator import Network

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL_PATH = os.path.join(ROOT, "models", "landslide_model.joblib")
METRICS_PATH = os.path.join(ROOT, "models", "metrics.json")
FRONTEND = os.path.join(ROOT, "frontend")

bundle = joblib.load(MODEL_PATH)
MODEL, FEATURES, LABELS = bundle["model"], bundle["features"], bundle["labels"]
METRICS = json.load(open(METRICS_PATH))

LEVEL_COLOR = {"Low": "#22c55e", "Moderate": "#eab308", "High": "#f97316", "Critical": "#ef4444"}
ACTIONS = {
    "Low": "Routine monitoring. No action required.",
    "Moderate": "Increase sensor polling. Advise caution to road users.",
    "High": "Issue public warning. Pre-position NDRF/SDRF. Restrict night travel.",
    "Critical": "EVACUATE vulnerable slopes. Close highway segment. Activate district EOC.",
}

app = FastAPI(title="NER Landslide Early Warning System", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

NETWORK = Network()
HISTORY: Dict[str, deque] = defaultdict(lambda: deque(maxlen=120))
ALERTS: deque = deque(maxlen=200)
_LAST_LEVEL: Dict[str, str] = {}


# ---------------- core inference ----------------
def _predict(rows: List[dict]) -> List[dict]:
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    proba = MODEL.predict_proba(X)
    idx = proba.argmax(axis=1)
    out = []
    for p, i in zip(proba, idx):
        # continuous 0-100 risk score = probability-weighted class severity
        score = float(np.dot(p, [12, 40, 70, 95]))
        out.append({
            "level": LABELS[int(i)],
            "confidence": round(float(p[int(i)]), 4),
            "risk_score": round(score, 1),
            "probabilities": {l: round(float(v), 4) for l, v in zip(LABELS, p)},
        })
    return out


def _explain(t: dict, level: str) -> List[dict]:
    """Rule-grounded contributing factors (transparent to district officers)."""
    f = []
    if t["rain_24h"] > 100: f.append(("Extreme 24h rainfall", f"{t['rain_24h']:.0f} mm", "high"))
    elif t["rain_24h"] > 50: f.append(("Heavy 24h rainfall", f"{t['rain_24h']:.0f} mm", "med"))
    if t["api_14d"] > 200: f.append(("Saturated antecedent conditions", f"API {t['api_14d']:.0f} mm", "high"))
    if t["soil_moisture"] > 70: f.append(("Soil near saturation", f"{t['soil_moisture']:.0f}%", "high"))
    if t["pore_pressure"] > 75: f.append(("Elevated pore-water pressure", f"{t['pore_pressure']:.0f} kPa", "high"))
    if t["displacement_rate"] > 3: f.append(("Accelerating slope creep", f"{t['displacement_rate']:.1f} mm/day", "high"))
    elif t["displacement_rate"] > 1.2: f.append(("Measurable slope movement", f"{t['displacement_rate']:.1f} mm/day", "med"))
    if t["ground_tilt"] > 1.5: f.append(("Tiltmeter deviation", f"{t['ground_tilt']:.2f}°", "high"))
    if t["slope"] > 35: f.append(("Steep terrain gradient", f"{t['slope']:.0f}°", "med"))
    if t["ndvi"] < 0.5: f.append(("Sparse vegetation cover", f"NDVI {t['ndvi']:.2f}", "med"))
    if t["road_cut"] > 0.75: f.append(("Dense road-cut destabilisation", f"index {t['road_cut']:.2f}", "med"))
    if t["rock_strength"] < 4: f.append(("Weak lithology", f"strength {t['rock_strength']:.1f}/10", "med"))
    if not f: f.append(("Stable conditions across all sensors", "nominal", "low"))
    return [{"factor": a, "value": b, "severity": c} for a, b, c in f[:6]]


def _forecast(t: dict, site: dict) -> List[dict]:
    """6/12/24h outlook by projecting rainfall accumulation trends."""
    out = []
    for h, mult in ((6, 1.10), (12, 1.22), (24, 1.40)):
        proj = dict(t)
        proj["rain_24h"] = t["rain_24h"] * mult
        proj["rain_72h"] = t["rain_72h"] * (1 + (mult - 1) * 0.6)
        proj["api_14d"] = t["api_14d"] * (1 + (mult - 1) * 0.4)
        proj["soil_moisture"] = min(100, t["soil_moisture"] * (1 + (mult - 1) * 0.8))
        proj["pore_pressure"] = min(140, t["pore_pressure"] * (1 + (mult - 1) * 0.9))
        p = _predict([proj])[0]
        out.append({"horizon_h": h, "level": p["level"], "risk_score": p["risk_score"]})
    return out


def snapshot() -> List[dict]:
    reads = NETWORK.read_all()
    preds = _predict([r["telemetry"] for r in reads])
    ts = time.time()
    result = []
    for r, p in zip(reads, preds):
        site, t = r["site"], r["telemetry"]
        rec = {
            "id": site["id"], "name": site["name"], "state": site["state"],
            "lat": site["lat"], "lon": site["lon"],
            "telemetry": t, **p,
            "color": LEVEL_COLOR[p["level"]],
            "action": ACTIONS[p["level"]],
            "factors": _explain(t, p["level"]),
            "timestamp": ts,
        }
        result.append(rec)
        HISTORY[site["id"]].append({"t": ts, "risk_score": p["risk_score"],
                                    "rain_1h": t["rain_1h"], "pore_pressure": t["pore_pressure"],
                                    "displacement_rate": t["displacement_rate"]})
        prev = _LAST_LEVEL.get(site["id"])
        order = {l: i for i, l in enumerate(LABELS)}
        if prev and order[p["level"]] > order[prev] and order[p["level"]] >= 2:
            ALERTS.appendleft({
                "id": f"{site['id']}-{int(ts)}", "site_id": site["id"], "site": site["name"],
                "state": site["state"], "level": p["level"], "from_level": prev,
                "risk_score": p["risk_score"], "action": ACTIONS[p["level"]],
                "timestamp": ts,
                "message": f"{p['level'].upper()} landslide risk at {site['name']}, {site['state']} "
                           f"(risk {p['risk_score']}). {ACTIONS[p['level']]}",
            })
        _LAST_LEVEL[site["id"]] = p["level"]
    return result


# ---------------- schemas ----------------
class PredictIn(BaseModel):
    rain_1h: float = Field(0, ge=0); rain_24h: float = Field(0, ge=0)
    rain_72h: float = Field(0, ge=0); api_14d: float = Field(0, ge=0)
    soil_moisture: float = Field(30, ge=0, le=100)
    slope: float = Field(30, ge=0, le=90); soil_depth: float = Field(3, ge=0)
    rock_strength: float = Field(4.5, ge=0, le=10); ndvi: float = Field(0.6, ge=0, le=1)
    drainage: float = Field(2.5, ge=0); seismic_zone: int = Field(5, ge=1, le=5)
    road_cut: float = Field(0.6, ge=0, le=1); pore_pressure: float = Field(40, ge=0)
    ground_tilt: float = Field(0.3, ge=0); displacement_rate: float = Field(0.5, ge=0)


# ---------------- routes ----------------
@app.get("/api/health")
def health():
    return {"status": "ok", "sites": len(SITES), "model": METRICS["algorithm"]}


@app.get("/api/metrics")
def metrics():
    return METRICS


@app.get("/api/sites")
def sites():
    return snapshot()


@app.get("/api/summary")
def summary():
    snap = snapshot()
    counts = {l: 0 for l in LABELS}
    for s in snap:
        counts[s["level"]] += 1
    by_state: Dict[str, list] = defaultdict(list)
    for s in snap:
        by_state[s["state"]].append(s["risk_score"])
    return {
        "counts": counts,
        "total_sites": len(snap),
        "avg_risk": round(sum(s["risk_score"] for s in snap) / len(snap), 1),
        "max_risk_site": max(snap, key=lambda s: s["risk_score"])["name"],
        "active_alerts": len([s for s in snap if s["level"] in ("High", "Critical")]),
        "by_state": {k: round(sum(v) / len(v), 1) for k, v in sorted(by_state.items())},
        "updated": time.time(),
    }


@app.get("/api/site/{site_id}")
def site_detail(site_id: str):
    if site_id not in SITES_BY_ID:
        raise HTTPException(404, "unknown site")
    rec = next(s for s in snapshot() if s["id"] == site_id)
    rec["forecast"] = _forecast(rec["telemetry"], SITES_BY_ID[site_id])
    rec["history"] = list(HISTORY[site_id])
    return rec


@app.get("/api/alerts")
def alerts(limit: int = 25):
    snapshot()
    return list(ALERTS)[:limit]


@app.post("/api/predict")
def predict(payload: PredictIn):
    t = payload.model_dump()
    p = _predict([t])[0]
    return {**p, "color": LEVEL_COLOR[p["level"]], "action": ACTIONS[p["level"]],
            "factors": _explain(t, p["level"]),
            "forecast": _forecast(t, {})}


if os.path.isdir(FRONTEND):
    app.mount("/assets", StaticFiles(directory=FRONTEND), name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(FRONTEND, "index.html"))
