"""Live telemetry simulator.

Stands in for the real ingestion layer (IMD/AWS rain gauges, IoT piezometers,
tiltmeters, and Sentinel-1 InSAR displacement). Each site evolves a smooth
stochastic state so the dashboard behaves like a real monitoring feed.
"""
import math
import random
import time
from typing import Dict, List

from districts import SITES


class SiteState:
    def __init__(self, site: dict, rng: random.Random):
        self.site = site
        self.rng = rng
        # storm phase gives each site its own rainfall cycle
        self.phase = rng.uniform(0, 2 * math.pi)
        self.period = rng.uniform(420, 900)          # seconds per storm cycle
        self.intensity = rng.uniform(0.35, 1.35)     # site storm severity multiplier
        self.rain_24h = rng.uniform(5, 60)
        self.rain_72h = self.rain_24h * rng.uniform(1.2, 2.4)
        self.api_14d = self.rain_72h * rng.uniform(0.8, 1.8)
        self.soil_moisture = rng.uniform(25, 55)
        self.pore_pressure = rng.uniform(20, 60)
        self.ground_tilt = rng.uniform(0.05, 0.9)
        self.displacement_rate = rng.uniform(0.1, 2.0)
        self.t0 = time.time()

    def step(self) -> Dict[str, float]:
        s = self.site
        t = time.time() - self.t0
        # storm signal in [0,1]
        storm = max(0.0, math.sin(2 * math.pi * t / self.period + self.phase))
        storm = storm ** 2 * self.intensity
        rain_1h = max(0.0, storm * 32 + self.rng.gauss(0, 2.2))

        # integrate rainfall accumulations with decay
        self.rain_24h = max(0.0, self.rain_24h * 0.985 + rain_1h * 0.35)
        self.rain_72h = max(0.0, self.rain_72h * 0.993 + rain_1h * 0.45)
        self.api_14d = max(0.0, self.api_14d * 0.997 + rain_1h * 0.30)

        # hydrology lags rainfall, modulated by drainage & soil depth
        target_sm = 18 + 0.10 * self.rain_24h + 0.035 * self.api_14d - 3.0 * (s["drainage"] - 2.6)
        self.soil_moisture += (target_sm - self.soil_moisture) * 0.12 + self.rng.gauss(0, 0.6)
        self.soil_moisture = min(100.0, max(5.0, self.soil_moisture))

        target_pp = 0.45 * self.soil_moisture + 0.045 * self.rain_72h + 2.5 * s["soil_depth"]
        self.pore_pressure += (target_pp - self.pore_pressure) * 0.10 + self.rng.gauss(0, 0.8)
        self.pore_pressure = min(140.0, max(0.0, self.pore_pressure))

        instability = (0.055 * self.pore_pressure + 0.075 * (s["slope"] - 25)
                       - 0.55 * s["rock_strength"] + 1.6 * s["road_cut"]
                       - 1.9 * s["ndvi"] + 0.28 * (s["seismic_zone"] - 4))
        tgt_tilt = max(0.0, 0.35 * instability)
        self.ground_tilt += (tgt_tilt - self.ground_tilt) * 0.15 + abs(self.rng.gauss(0, 0.05))
        self.ground_tilt = max(0.0, self.ground_tilt * 0.99)

        tgt_disp = max(0.0, 0.9 * max(instability, 0) ** 1.25)
        self.displacement_rate += (tgt_disp - self.displacement_rate) * 0.15 + abs(self.rng.gauss(0, 0.08))
        self.displacement_rate = max(0.0, self.displacement_rate * 0.99)

        return {
            "rain_1h": round(rain_1h, 2),
            "rain_24h": round(self.rain_24h, 2),
            "rain_72h": round(self.rain_72h, 2),
            "api_14d": round(self.api_14d, 2),
            "soil_moisture": round(self.soil_moisture, 2),
            "slope": s["slope"],
            "soil_depth": s["soil_depth"],
            "rock_strength": s["rock_strength"],
            "ndvi": s["ndvi"],
            "drainage": s["drainage"],
            "seismic_zone": s["seismic_zone"],
            "road_cut": s["road_cut"],
            "pore_pressure": round(self.pore_pressure, 2),
            "ground_tilt": round(self.ground_tilt, 3),
            "displacement_rate": round(self.displacement_rate, 3),
        }


class Network:
    """All monitored sites."""

    def __init__(self, seed: int = 7):
        rng = random.Random(seed)
        self.states = {s["id"]: SiteState(s, random.Random(rng.randint(0, 10**6))) for s in SITES}

    def read_all(self) -> List[dict]:
        out = []
        for sid, st in self.states.items():
            out.append({"site": st.site, "telemetry": st.step()})
        return out
