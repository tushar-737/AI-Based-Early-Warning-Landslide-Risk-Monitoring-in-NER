"""Generate a physically-grounded synthetic training dataset for landslide risk in NER.

NOTE: real deployment should replace this with IMD rainfall, ISRO Bhuvan/BHUKOSH
landslide inventory, Sentinel-1 InSAR displacement and in-situ piezometer feeds.
The generator encodes accepted geotechnical relationships so the model learns
realistic decision boundaries for the prototype.
"""
import numpy as np
import pandas as pd
import os

RNG = np.random.default_rng(42)
N = 24000
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "training_data.csv")

FEATURES = [
    "rain_1h", "rain_24h", "rain_72h", "api_14d", "soil_moisture",
    "slope", "soil_depth", "rock_strength", "ndvi", "drainage",
    "seismic_zone", "road_cut", "pore_pressure", "ground_tilt", "displacement_rate",
]


def make() -> pd.DataFrame:
    n = N
    # --- Terrain / static predisposition ---
    slope = np.clip(RNG.normal(33, 8, n), 8, 60)
    soil_depth = np.clip(RNG.normal(3.4, 0.9, n), 0.8, 6.5)
    rock_strength = np.clip(RNG.normal(4.3, 1.0, n), 1.5, 8.0)
    ndvi = np.clip(RNG.normal(0.60, 0.13, n), 0.05, 0.95)
    drainage = np.clip(RNG.normal(2.6, 0.6, n), 0.8, 4.5)
    seismic_zone = RNG.choice([4, 5], n, p=[0.25, 0.75])
    road_cut = np.clip(RNG.normal(0.70, 0.18, n), 0.0, 1.0)

    # --- Rainfall (monsoon-heavy, long tail typical of NER) ---
    rain_24h = RNG.gamma(1.6, 28, n)                      # mm
    rain_1h = np.clip(rain_24h * RNG.uniform(0.05, 0.45, n), 0, None)
    rain_72h = rain_24h * RNG.uniform(1.0, 3.0, n)
    api_14d = rain_72h * RNG.uniform(0.6, 2.2, n)         # antecedent precipitation index

    # --- Hydrology responds to rain + terrain ---
    soil_moisture = np.clip(
        18 + 0.10 * rain_24h + 0.035 * api_14d - 3.0 * (drainage - 2.6)
        + RNG.normal(0, 4, n), 5, 100)
    pore_pressure = np.clip(
        0.45 * soil_moisture + 0.09 * rain_72h / 2 + 2.5 * soil_depth
        + RNG.normal(0, 6, n), 0, 140)                    # kPa

    # --- Slope movement instrumentation ---
    instability = (
        0.055 * pore_pressure
        + 0.075 * (slope - 25)
        - 0.55 * rock_strength
        + 1.6 * road_cut
        - 1.9 * ndvi
        + 0.28 * (seismic_zone - 4)
    )
    ground_tilt = np.clip(0.35 * np.maximum(instability, 0) + RNG.gamma(1.1, 0.35, n), 0, None)
    displacement_rate = np.clip(0.9 * np.maximum(instability, 0) ** 1.25
                                + RNG.gamma(1.2, 0.7, n), 0, None)  # mm/day

    # --- Latent factor of safety -> label ---
    score = (
        0.030 * rain_24h + 0.014 * rain_72h + 0.010 * api_14d
        + 0.050 * soil_moisture + 0.045 * pore_pressure
        + 0.115 * slope + 0.42 * soil_depth
        - 0.75 * rock_strength - 3.1 * ndvi
        + 2.4 * road_cut + 0.55 * (seismic_zone - 4)
        + 0.95 * ground_tilt + 0.62 * displacement_rate
        - 0.45 * drainage
        + RNG.normal(0, 1.6, n)
    )
    q = np.quantile(score, [0.55, 0.80, 0.94])
    label = np.digitize(score, q)  # 0 Low, 1 Moderate, 2 High, 3 Critical

    df = pd.DataFrame(dict(
        rain_1h=rain_1h, rain_24h=rain_24h, rain_72h=rain_72h, api_14d=api_14d,
        soil_moisture=soil_moisture, slope=slope, soil_depth=soil_depth,
        rock_strength=rock_strength, ndvi=ndvi, drainage=drainage,
        seismic_zone=seismic_zone, road_cut=road_cut, pore_pressure=pore_pressure,
        ground_tilt=ground_tilt, displacement_rate=displacement_rate, risk=label))
    return df.round(4)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df = make()
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}  rows={len(df)}")
    print(df.risk.value_counts().sort_index().to_string())
