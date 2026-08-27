"""Static geo/terrain profile of monitored sites across the North Eastern Region (NER)."""

# lat, lon, state, slope(deg), soil_depth(m), rock_strength(1-10, higher=stronger),
# vegetation_index(0-1), drainage_density(km/km2), seismic_zone(2-5), road_cut_density(0-1)
SITES = [
    # Sikkim
    dict(id="SK-01", name="Gangtok - NH10 Corridor", state="Sikkim", lat=27.3389, lon=88.6065,
         slope=38, soil_depth=3.2, rock_strength=4.0, ndvi=0.52, drainage=2.9, seismic_zone=4, road_cut=0.85),
    dict(id="SK-02", name="Mangan", state="Sikkim", lat=27.5100, lon=88.5300,
         slope=42, soil_depth=2.8, rock_strength=4.5, ndvi=0.61, drainage=3.1, seismic_zone=4, road_cut=0.60),
    # Assam
    dict(id="AS-01", name="Guwahati Hills", state="Assam", lat=26.1445, lon=91.7362,
         slope=24, soil_depth=4.1, rock_strength=5.5, ndvi=0.44, drainage=1.8, seismic_zone=5, road_cut=0.78),
    dict(id="AS-02", name="Haflong (Dima Hasao)", state="Assam", lat=25.1667, lon=93.0167,
         slope=35, soil_depth=3.6, rock_strength=3.8, ndvi=0.66, drainage=2.6, seismic_zone=5, road_cut=0.72),
    # Meghalaya
    dict(id="ML-01", name="Cherrapunji (Sohra)", state="Meghalaya", lat=25.3000, lon=91.7000,
         slope=40, soil_depth=2.5, rock_strength=5.0, ndvi=0.58, drainage=3.6, seismic_zone=5, road_cut=0.55),
    dict(id="ML-02", name="Shillong - Jowai Road", state="Meghalaya", lat=25.5788, lon=91.8933,
         slope=28, soil_depth=3.0, rock_strength=5.2, ndvi=0.63, drainage=2.2, seismic_zone=5, road_cut=0.68),
    # Arunachal Pradesh
    dict(id="AR-01", name="Tawang Pass", state="Arunachal Pradesh", lat=27.5860, lon=91.8590,
         slope=45, soil_depth=2.2, rock_strength=4.2, ndvi=0.38, drainage=2.4, seismic_zone=5, road_cut=0.80),
    dict(id="AR-02", name="Itanagar Ridge", state="Arunachal Pradesh", lat=27.0844, lon=93.6053,
         slope=32, soil_depth=3.9, rock_strength=3.9, ndvi=0.71, drainage=2.7, seismic_zone=5, road_cut=0.64),
    # Manipur
    dict(id="MN-01", name="Noney - Tupul", state="Manipur", lat=24.8300, lon=93.6800,
         slope=37, soil_depth=4.3, rock_strength=3.4, ndvi=0.60, drainage=2.8, seismic_zone=5, road_cut=0.90),
    # Mizoram
    dict(id="MZ-01", name="Aizawl - Durtlang", state="Mizoram", lat=23.7400, lon=92.7200,
         slope=41, soil_depth=3.3, rock_strength=3.6, ndvi=0.69, drainage=3.0, seismic_zone=5, road_cut=0.88),
    # Nagaland
    dict(id="NL-01", name="Kohima - Zubza", state="Nagaland", lat=25.6751, lon=94.1086,
         slope=36, soil_depth=3.7, rock_strength=3.7, ndvi=0.65, drainage=2.5, seismic_zone=5, road_cut=0.76),
    # Tripura
    dict(id="TR-01", name="Jampui Hills", state="Tripura", lat=23.9500, lon=92.2800,
         slope=22, soil_depth=4.5, rock_strength=4.8, ndvi=0.74, drainage=1.9, seismic_zone=5, road_cut=0.42),
]

SITES_BY_ID = {s["id"]: s for s in SITES}
