#!/usr/bin/env bash
# One-command launcher for the NER Landslide Early Warning System.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -r requirements.txt 2>/dev/null || pip install -r requirements.txt
if [ ! -f models/landslide_model.joblib ]; then
  echo "==> Generating dataset and training model..."
  python ml/generate_dataset.py
  python ml/train_model.py
fi
echo "==> Starting server on http://localhost:8000"
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000
