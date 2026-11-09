import numpy as np
import pandas as pd

from habitable import hz_edge
from pathlib import Path

# Chance a planet is rocky falls smoothly with radius: 50% at 1.6 Earth radii (Rogers 2015)
ROCKY_MIDPOINT = 1.6
ROCKY_WIDTH = 0.1


def rocky_chance(radius):
    return 1 / (1 + np.exp((radius - ROCKY_MIDPOINT) / ROCKY_WIDTH))


def get_sigma(planet, col):
    err_up = planet[f"{col}err1"]
    err_down = planet[f"{col}err2"]

    if pd.notna(err_up) and pd.notna(err_down):
        return (err_up + abs(err_down)) / 2

    if col == "st_teff":
        return 100
    if col == "pl_rade":
        return 0.30 * planet[col]
    if col == "pl_bmasse" and planet["data_quality"] == "medium":
        return 0.50 * planet[col]
    return 0.10 * planet[col]

def simulate(pl, rng):
    N = 10000
    radius = rng.normal(pl["pl_rade"], get_sigma(pl, "pl_rade"), N)
    insol = rng.normal(pl["pl_insol"], get_sigma(pl, "pl_insol"), N)
    teff = rng.normal(pl["st_teff"], get_sigma(pl, "st_teff"), N)

    teff_used = np.clip(teff, 2600, 7200)
    valid = (teff >= 2500) & (teff <= 7500)

    in_conservative = valid & (insol <= hz_edge(teff_used, "runaway_greenhouse")) \
                            & (insol >= hz_edge(teff_used, "max_greenhouse"))
    in_optimistic = valid & (insol <= hz_edge(teff_used, "recent_venus")) \
                          & (insol >= hz_edge(teff_used, "early_mars"))
    rocky = rocky_chance(radius)

    return {
        "p_rocky": rocky.mean(),
        "p_not_gaseous": (radius < 2.0).mean(),
        "p_hz_conservative": in_conservative.mean(),
        "p_hz_optimistic": in_optimistic.mean(),
        "p_candidate": (in_optimistic & (radius < 2.0)).mean(),
        "p_strong": (in_conservative * rocky).mean(),
    }

    


def monte_carlo(df):
    
    rng = np.random.default_rng(77)
    results = []

    for _, planet in df.iterrows():
        if planet[["pl_rade", "pl_insol", "st_teff"]].isna().any():
            results.append({})
        else:
            results.append(simulate(planet, rng))

    probabilities = pd.DataFrame(results, index=df.index)
    return df.join(probabilities)



if __name__ == "__main__":
    df = pd.read_csv("data/planets_scored.csv")
    df = monte_carlo(df)

    cols = ["pl_name", "p_strong", "p_candidate", "p_hz_conservative", "p_rocky", "data_quality"]
    ranked = df[df["p_candidate"] > 0].sort_values(["p_strong", "p_candidate"], ascending=False)

    df.to_csv("data/planets_mc.csv", index=False)


    cand_names = pd.read_csv("data/candidates.csv")["pl_name"]
    print(df[df["pl_name"].isin(cand_names)]["data_quality"].value_counts())
    print(ranked[cols].head(20).round(2).to_string(index=False))

    keep = ["pl_name", "hostname", "discoverymethod", "pl_rade", "pl_insol", "st_teff",
            "pl_radeerr1", "pl_radeerr2", "pl_insolerr1", "pl_insolerr2", "st_tefferr1", "st_tefferr2",
            "pl_type", "data_quality", "within_conservative", "within_optimistic",
            "p_strong", "p_candidate", "p_hz_conservative", "p_rocky"]
    
    Path("results").mkdir(exist_ok=True)
    df[keep].to_csv("results/planets_mc.csv", index=False)