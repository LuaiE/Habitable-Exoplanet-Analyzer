import numpy as np
import pandas as pd

HZ_COEFFS = {
    "recent_venus":       (1.776, 2.136e-4, 2.533e-8, -1.332e-11, -3.097e-15),  # optimistic inner
    "runaway_greenhouse": (1.107, 1.332e-4, 1.580e-8, -8.308e-12, -1.931e-15),  # conservative inner
    "max_greenhouse":     (0.356, 6.171e-5, 1.698e-9, -3.198e-12, -5.575e-16),  # conservative outer
    "early_mars":         (0.320, 5.547e-5, 1.526e-9, -2.874e-12, -5.011e-16),  # optimistic outer
}

KNOWN_CANDIDATES = ["TRAPPIST-1 e", "TRAPPIST-1 f", "TRAPPIST-1 g", "Kepler-442 b",
                    "Proxima Cen b", "TOI-700 d", "LHS 1140 b", "Teegarden's Star b",
                    "Kepler-186 f"]
ROCKY_RATIO_MAX = 1.05   # up to ~10% water by mass
WATER_RATIO_MAX = 1.24   # up to ~50% water by mass

def hz_edge (starTemp, edgeType):
    solarV, a, b, c, d = HZ_COEFFS[edgeType]
    normalized_temp=starTemp-5780
    limit = solarV + a*(normalized_temp) + b*(normalized_temp**2) + c*(normalized_temp**3) + d*(normalized_temp**4)
    return limit

def add_hz_edgeData(df):

    #Kopparapu formula only works for these star temps (https://ui.adsabs.harvard.edu/abs/2014ApJ...787L..29K/abstract)
    teff_used = df["st_teff"].clip(2600, 7200)

    for edgeType in HZ_COEFFS:
        df[f"hz_{edgeType}"] = hz_edge(teff_used, edgeType)

    df["not_og_teff"] = ~df["st_teff"].between(2600, 7200) & df["st_teff"].notna()

    #adjusts for planets slightly outside range
    valid = df["st_teff"].between(2500, 7500) #very few planets would be considered fully with a change of range, only Trappist d,e,f,g (outside limit by 34 k, passes required tests with this change)
    #upper limit unchanged as it has no effect
    df["within_conservative"] = (valid & (df["hz_runaway_greenhouse"] >= df["pl_insol"]) & (df["hz_max_greenhouse"] <= df["pl_insol"]))
    df["within_optimistic"] = (valid & (df["hz_recent_venus"] >= df["pl_insol"]) & (df["hz_early_mars"] <= df["pl_insol"]))

    #at initial execution: 184 planets in conservative HZ, 284 in optimistic HZ
    print(f"{df['within_conservative'].sum()} planets in conservative HZ, "
          f"{df['within_optimistic'].sum()} in optimistic HZ")
    print(f"{df['not_og_teff'].sum()} planets outside the initial calibrated range")

    return df

def classify_type(df):
    df["pl_type"] = pd.cut(
        df["pl_rade"],
        bins=[0, 1.5, 2.0, np.inf],
        labels=["rocky", "uncertain", "gaseous"],
    )
    return df

def add_data_quality(df):
    # radius counts as measured only if NASA records an error bar for it
    # high = radius and mass measured, medium = radius measured but mass estimated, low = radius estimated
    radius_measured = df["pl_radeerr1"].notna()
    mass_measured = (df["pl_bmassprov"] == "Mass") & (df["pl_bmasselim"].fillna(0) == 0)

    df["data_quality"] = np.select(
        [radius_measured & mass_measured, radius_measured],
        ["high", "medium"],
        default="low",
    )
    return df

def rocky_radius(mass):
    # radius of an Earth-like rock/iron planet of this mass (Zeng et al. 2016)
    return mass ** (1 / 3.7)


def add_composition(df):
    # only planets with radius AND mass measured can be judged by density
    has_mass = df["data_quality"] == "high"

    ratio = df["pl_rade"] / rocky_radius(df["pl_bmasse"])
    impossible = ratio < 0.8   # denser than pure iron: bad data, not a real planet

    df["radius_ratio"] = ratio.where(has_mass)
    df["composition"] = np.select(
        [~has_mass | impossible, ratio <= ROCKY_RATIO_MAX, ratio <= WATER_RATIO_MAX],
        ["unknown", "rocky", "water_world"],
        default="gas_envelope",
    )
    return df

#planet keeps its atmosphere if its gravity beats the energy its star pours in
def add_atmo_score(df):
    df["esc_vel"] = (df["pl_bmasse"] / df["pl_rade"])**(1/2)
    df["atmo_score"]= (df["esc_vel"]**4) / df["pl_insol"]

    df["atmo_class"] = pd.cut(
        df["atmo_score"],
        bins=[0, 0.01, 0.1, np.inf],
        labels=["likely_lost", "marginal", "likely_retained"],
    )
    return df

def find_candidates(df):
    mask = df["within_optimistic"] & df["pl_type"].isin(["rocky", "uncertain"])
    cols = ["pl_name", "pl_rade", "pl_insol", "st_teff",
            "within_conservative", "pl_type", "pl_bmassprov", "data_quality", "atmo_score", "atmo_class", "composition", "disputed"]
    return df.loc[mask, cols].sort_values(["within_conservative", "pl_rade" ], ascending=[False, True])   

def check_known(candidates):
    #verifies known candidates that could be lost, are not 
    for name in KNOWN_CANDIDATES:
        found = name in candidates["pl_name"].values
        print(f"{name:22} {'FOUND' if found else 'MISSING'}")

if __name__ == "__main__":

    df = pd.read_csv("data/planets_cleaned.csv")

    df = add_hz_edgeData(df)
    df = classify_type(df)
    df = add_data_quality(df)
    df = add_composition(df)
    df = add_atmo_score(df)
    candidates = find_candidates(df)

    print(f"\n{len(candidates)} candidates (optimistic HZ, rocky or uncertain size)\n")
    check_known(candidates)

    df.to_csv("data/planets_scored.csv", index=False)
    candidates.to_csv("data/candidates.csv", index=False)

    