"""Train the landslide risk classifier (4-class) + persist artefacts."""
import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.inspection import permutation_importance

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "training_data.csv")
MODEL_DIR = os.path.join(HERE, "..", "models")
FEATURES = [
    "rain_1h", "rain_24h", "rain_72h", "api_14d", "soil_moisture",
    "slope", "soil_depth", "rock_strength", "ndvi", "drainage",
    "seismic_zone", "road_cut", "pore_pressure", "ground_tilt", "displacement_rate",
]
LABELS = ["Low", "Moderate", "High", "Critical"]


def main():
    df = pd.read_csv(DATA)
    X, y = df[FEATURES], df["risk"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    clf = HistGradientBoostingClassifier(
        max_iter=350, learning_rate=0.08, max_depth=7,
        min_samples_leaf=25, l2_regularization=0.6, random_state=42)
    clf.fit(Xtr, ytr)

    pred = clf.predict(Xte)
    proba = clf.predict_proba(Xte)
    acc = float((pred == yte).mean())
    auc = float(roc_auc_score(yte, proba, multi_class="ovr"))
    cv = cross_val_score(clf, X, y, cv=5, scoring="accuracy")

    print(classification_report(yte, pred, target_names=LABELS, digits=3))
    print("confusion matrix\n", confusion_matrix(yte, pred))
    print(f"accuracy={acc:.4f} rocauc_ovr={auc:.4f} cv={cv.mean():.4f}+-{cv.std():.4f}")

    imp = permutation_importance(clf, Xte, yte, n_repeats=5, random_state=42, n_jobs=-1)
    importances = sorted(
        ({"feature": f, "importance": round(float(v), 5)}
         for f, v in zip(FEATURES, imp.importances_mean)),
        key=lambda d: -d["importance"])

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({"model": clf, "features": FEATURES, "labels": LABELS},
                os.path.join(MODEL_DIR, "landslide_model.joblib"))
    json.dump({
        "accuracy": round(acc, 4),
        "roc_auc_ovr": round(auc, 4),
        "cv_accuracy_mean": round(float(cv.mean()), 4),
        "cv_accuracy_std": round(float(cv.std()), 4),
        "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
        "labels": LABELS,
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
        "feature_importance": importances,
        "algorithm": "HistGradientBoostingClassifier",
    }, open(os.path.join(MODEL_DIR, "metrics.json"), "w"), indent=2)
    print("saved model + metrics")


if __name__ == "__main__":
    main()
