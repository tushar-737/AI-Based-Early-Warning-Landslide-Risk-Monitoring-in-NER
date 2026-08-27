#!/usr/bin/env python3
"""
System verification script for NER Landslide Early Warning System.
Tests Python environment, ML model, simulator, and live API endpoints.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
MODELS_DIR = os.path.join(ROOT, "models")
DATA_DIR = os.path.join(ROOT, "data")
FRONTEND_DIR = os.path.join(ROOT, "frontend")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(name: str):
    print(f"\n{BOLD}{CYAN}=== {name} ==={RESET}")


def log_pass(msg: str):
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def log_fail(msg: str):
    print(f"  {RED}[FAIL]{RESET} {msg}")


def log_warn(msg: str):
    print(f"  {YELLOW}[WARN]{RESET} {msg}")


def check_dependencies():
    print_step("1. Checking Python Dependencies")
    deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sklearn", "scikit-learn"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("joblib", "joblib"),
        ("pydantic", "pydantic"),
    ]
    all_ok = True
    for module_name, display_name in deps:
        try:
            mod = __import__(module_name)
            ver = getattr(mod, "__version__", "installed")
            log_pass(f"{display_name} ({ver})")
        except ImportError as e:
            log_fail(f"{display_name} not found: {e}")
            all_ok = False
    return all_ok


def check_files():
    print_step("2. Checking Project Files & Artefacts")
    required_files = [
        ("data/training_data.csv", os.path.join(DATA_DIR, "training_data.csv")),
        ("models/landslide_model.joblib", os.path.join(MODELS_DIR, "landslide_model.joblib")),
        ("models/metrics.json", os.path.join(MODELS_DIR, "metrics.json")),
        ("backend/main.py", os.path.join(BACKEND_DIR, "main.py")),
        ("backend/districts.py", os.path.join(BACKEND_DIR, "districts.py")),
        ("backend/simulator.py", os.path.join(BACKEND_DIR, "simulator.py")),
        ("frontend/index.html", os.path.join(FRONTEND_DIR, "index.html")),
        ("frontend/app.js", os.path.join(FRONTEND_DIR, "app.js")),
        ("frontend/style.css", os.path.join(FRONTEND_DIR, "style.css")),
    ]
    all_ok = True
    for name, path in required_files:
        if os.path.isfile(path):
            size_kb = os.path.getsize(path) / 1024
            log_pass(f"{name} ({size_kb:.1f} KB)")
        else:
            log_fail(f"{name} is missing at {path}")
            all_ok = False
    return all_ok


def check_model_inference():
    print_step("3. Checking ML Model & Direct Inference")
    model_path = os.path.join(MODELS_DIR, "landslide_model.joblib")
    metrics_path = os.path.join(MODELS_DIR, "metrics.json")
    try:
        import joblib
        import numpy as np

        bundle = joblib.load(model_path)
        model = bundle.get("model")
        features = bundle.get("features", [])
        labels = bundle.get("labels", [])

        log_pass(f"Model loaded: {type(model).__name__}")
        log_pass(f"Features ({len(features)}): {', '.join(features[:5])}...")
        log_pass(f"Labels: {labels}")

        with open(metrics_path) as f:
            metrics = json.load(f)
        log_pass(f"Metrics: Accuracy = {metrics.get('accuracy') * 100:.1f}%, ROC-AUC = {metrics.get('roc_auc_ovr', 0):.3f}")

        # Test safe scenario (dry weather, flat slope)
        import pandas as pd
        safe_scenario = pd.DataFrame([[0, 5, 10, 15, 20, 10, 2, 8.0, 0.8, 4.0, 2, 0.1, 15, 0.05, 0.1]], columns=features)
        p_safe = model.predict_proba(safe_scenario)[0]
        pred_safe_label = labels[int(p_safe.argmax())]
        log_pass(f"Safe scenario prediction: {pred_safe_label} (P(Low)={p_safe[0]:.2f})")

        # Test extreme storm scenario (intense rain, saturated pore pressure, steep slope)
        crit_scenario = pd.DataFrame([[45, 320, 600, 750, 95, 45, 6, 2.0, 0.2, 1.0, 5, 0.9, 125, 2.5, 9.0]], columns=features)
        p_crit = model.predict_proba(crit_scenario)[0]
        pred_crit_label = labels[int(p_crit.argmax())]
        log_pass(f"Extreme storm scenario prediction: {pred_crit_label} (P(Critical)={p_crit[-1]:.2f})")

        return True
    except Exception as e:
        log_fail(f"Model inference failed: {e}")
        return False


def check_simulator():
    print_step("4. Checking Telemetry Simulator")
    try:
        sys.path.insert(0, BACKEND_DIR)
        from simulator import Network
        from districts import SITES

        net = Network()
        readings = net.read_all()
        log_pass(f"Simulating network of {len(readings)} sites across {len(SITES)} configured districts")
        sample = readings[0]
        log_pass(f"Sample site: '{sample['site']['name']}' in {sample['site']['state']}")
        t = sample["telemetry"]
        log_pass(f"Sample telemetry: rain_24h={t['rain_24h']}mm, pore_pressure={t['pore_pressure']}kPa, tilt={t['ground_tilt']}°")
        return True
    except Exception as e:
        log_fail(f"Simulator check failed: {e}")
        return False


def check_live_api(base_url: str = "http://127.0.0.1:8000"):
    print_step(f"5. Checking Live API & Dashboard ({base_url})")

    # Helper to test GET
    def test_get(endpoint: str, description: str):
        url = f"{base_url}{endpoint}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SystemChecker/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                data = response.read()
                if status == 200:
                    try:
                        parsed = json.loads(data.decode("utf-8"))
                        return True, parsed
                    except Exception:
                        return True, data
                else:
                    return False, f"Status {status}"
        except urllib.error.URLError as e:
            return False, str(e.reason)
        except Exception as e:
            return False, str(e)

    # Helper to test POST
    def test_post(endpoint: str, payload: dict, description: str):
        url = f"{base_url}{endpoint}"
        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "SystemChecker/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                data = response.read()
                if status == 200:
                    return True, json.loads(data.decode("utf-8"))
                return False, f"Status {status}"
        except Exception as e:
            return False, str(e)

    # 1. Health check
    ok, res = test_get("/api/health", "Health endpoint")
    if not ok:
        log_warn(f"Server is not reachable on {base_url} ({res})")
        log_warn("Start the server using: ./run.sh or 'cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000'")
        return False

    log_pass(f"GET /api/health -> status: '{res.get('status')}', sites: {res.get('sites')}")

    # 2. Frontend index
    ok, _ = test_get("/", "Frontend Index")
    if ok:
        log_pass("GET / -> 200 OK (Dashboard Web App)")
    else:
        log_fail("GET / failed")

    # 3. Static assets
    ok_js, _ = test_get("/assets/app.js", "Frontend app.js")
    ok_css, _ = test_get("/assets/style.css", "Frontend style.css")
    if ok_js and ok_css:
        log_pass("GET /assets/app.js and /assets/style.css -> 200 OK")
    else:
        log_fail("Static assets failed to serve")

    # 4. Summary endpoint
    ok, res = test_get("/api/summary", "Summary endpoint")
    if ok and "counts" in res and "avg_risk" in res:
        log_pass(f"GET /api/summary -> Avg Risk: {res['avg_risk']}, Max Risk Site: '{res.get('max_risk_site')}'")
    else:
        log_fail(f"GET /api/summary failed: {res}")

    # 5. Sites endpoint
    ok, res = test_get("/api/sites", "Sites endpoint")
    if ok and isinstance(res, list) and len(res) > 0:
        log_pass(f"GET /api/sites -> Successfully returned {len(res)} monitored sites")
    else:
        log_fail(f"GET /api/sites failed: {res}")

    # 6. Detail endpoint
    sample_id = "SK-01"
    ok, res = test_get(f"/api/site/{sample_id}", "Site Detail endpoint")
    if ok and "forecast" in res and "factors" in res:
        log_pass(f"GET /api/site/{sample_id} -> detail with {len(res['forecast'])}-horizon forecast & {len(res['factors'])} factors")
    else:
        log_fail(f"GET /api/site/{sample_id} failed: {res}")

    # 7. Alerts endpoint
    ok, res = test_get("/api/alerts", "Alerts endpoint")
    if ok and isinstance(res, list):
        log_pass(f"GET /api/alerts -> {len(res)} active alerts in feed")
    else:
        log_fail(f"GET /api/alerts failed: {res}")

    # 8. Metrics endpoint
    ok, res = test_get("/api/metrics", "Metrics endpoint")
    if ok and "accuracy" in res and "feature_importance" in res:
        log_pass(f"GET /api/metrics -> Algorithm: {res.get('algorithm')}, Accuracy: {res.get('accuracy')}")
    else:
        log_fail(f"GET /api/metrics failed: {res}")

    # 9. Predict endpoint (POST)
    post_payload = {
        "rain_1h": 35.0,
        "rain_24h": 280.0,
        "rain_72h": 450.0,
        "api_14d": 620.0,
        "soil_moisture": 90.0,
        "slope": 42.0,
        "soil_depth": 5.0,
        "rock_strength": 3.0,
        "ndvi": 0.35,
        "drainage": 1.5,
        "seismic_zone": 5,
        "road_cut": 0.85,
        "pore_pressure": 110.0,
        "ground_tilt": 2.1,
        "displacement_rate": 6.8,
    }
    ok, res = test_post("/api/predict", post_payload, "Predict endpoint")
    if ok and "level" in res and "risk_score" in res:
        log_pass(f"POST /api/predict -> Level: {res['level']}, Risk Score: {res['risk_score']}, Action: '{res['action']}'")
    else:
        log_fail(f"POST /api/predict failed: {res}")

    return True


def main():
    print(f"\n{BOLD}{GREEN}======================================================{RESET}")
    print(f"{BOLD}{GREEN}  NER Landslide Early Warning System — Health Check   {RESET}")
    print(f"{BOLD}{GREEN}======================================================{RESET}")

    ok_deps = check_dependencies()
    ok_files = check_files()
    ok_model = check_model_inference()
    ok_sim = check_simulator()
    ok_api = check_live_api()

    print_step("Summary")
    results = [
        ("Dependencies", ok_deps),
        ("Files & Artefacts", ok_files),
        ("Model & Inference", ok_model),
        ("Telemetry Simulator", ok_sim),
        ("Live Server & APIs", ok_api),
    ]

    all_passed = all(status for _, status in results)
    for name, status in results:
        if status:
            print(f"  {GREEN}✔{RESET} {name}")
        else:
            print(f"  {RED}✘{RESET} {name}")

    if all_passed:
        print(f"\n{BOLD}{GREEN}All checks passed! The system is fully operational.{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{BOLD}{YELLOW}Some checks did not pass. Please review the output above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
