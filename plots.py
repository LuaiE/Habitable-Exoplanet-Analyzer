import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from habitable import hz_edge   # reuse your formula; don't copy it

df = pd.read_csv("data/planets_scored.csv")
candidates = pd.read_csv("data/candidates.csv")

# Candidates: darker = more reliable data; shapes differ too, so colour isn't the only cue
quality_style = {
    "high":   ("#184f95", "o"),   # dark blue circle   - mass and radius measured
    "medium": ("#2a78d6", "s"),   # mid blue square    - mass estimated from radius
    "low":    ("#86b6ef", "^"),   # light blue triangle - radius estimated from minimum mass
}


#HABITABLE ZONE GRAPH

fig_hz, ax_hz = plt.subplots(figsize=(9, 6))

teff = np.linspace(2500, 7200, 300)
teff_used = np.clip(teff, 2600, 7200)

edges = {}
for name in ["recent_venus", "runaway_greenhouse", "max_greenhouse", "early_mars"]:
    edges[name] = hz_edge(teff_used, name)   # calculates inner and outer limits at each temp.

ax_hz.fill_betweenx(teff, edges["recent_venus"], edges["early_mars"],
                    color="#1baf7a", alpha=0.15, label="Optimistic HZ")
ax_hz.fill_betweenx(teff, edges["runaway_greenhouse"], edges["max_greenhouse"],
                    color="#1baf7a", alpha=0.35, label="Conservative HZ")

for quality, (color, marker) in quality_style.items():
    subset = candidates[candidates["data_quality"] == quality]
    ax_hz.scatter(subset["pl_insol"], subset["st_teff"], s=45, color=color, marker=marker,
                  edgecolor="white", linewidth=1,
                  label=f"Candidate with {quality} data quality", zorder=3)

ax_hz.scatter(1, 5780, marker="*", s=150, color="#1a1a19", zorder=4, label="Earth")

ax_hz.set_xlim(5, 0.1)
ax_hz.set_ylim(2500, 7200)
ax_hz.scatter(df["pl_insol"], df["st_teff"], s=5, color="#c3c2b7", label="All planets", zorder=1)    # x = insolation, y = star temp
ax_hz.set_xscale("log")
ax_hz.set_xlabel("Insolation (Earth = 1)")
ax_hz.set_ylabel("Star temperature (K)")

ax_hz.set_title("Potentially habitable exoplanets (NASA Exoplanet Archive)")
ax_hz.legend(loc="best", fontsize=8, labelspacing=1.2, frameon=False)

fig_hz.tight_layout()
fig_hz.savefig("hz_diagram.png", dpi=200, bbox_inches="tight")


#PLANET TYPE GRAPH

fig_size, ax_size = plt.subplots(figsize=(9, 6))

ax_size.axhline(1.5, color="#898781", linewidth=1, linestyle="--", zorder=2)
ax_size.axhline(2.0, color="#898781", linewidth=1, linestyle="--", zorder=2)
ax_size.text(4.5, 1.2, "Rocky", fontsize=8, color="#5f5e5a")
ax_size.text(4.5, 1.65, "Uncertain", fontsize=8, color="#5f5e5a")
ax_size.text(4.5, 2.4, "Gaseous", fontsize=8, color="#5f5e5a")

hz_too_large = df[df["within_optimistic"] & ~df["pl_name"].isin(candidates["pl_name"])]
ax_size.scatter(hz_too_large["pl_insol"], hz_too_large["pl_rade"], s=25, color="#eb6834",
                edgecolor="white", linewidth=0.5, label="In optimistic HZ, too large", zorder=2)

for quality, (color, marker) in quality_style.items():
    subset = candidates[candidates["data_quality"] == quality]
    ax_size.scatter(subset["pl_insol"], subset["pl_rade"], s=45, color=color, marker=marker,
                    edgecolor="white", linewidth=1,
                    label=f"Candidate with {quality} data quality", zorder=3)

ax_size.scatter(1, 1, marker="*", s=150, color="#1a1a19", zorder=4, label="Earth")

ax_size.set_xlim(5, 0.1)

if candidates["pl_rade"].min() >= 0.5 and candidates["pl_rade"].max() <= 20:
    ax_size.set_ylim(0.5, 20)
else:
    ax_size.set_ylim(0.3, 30)
    print("Candidate radius outside 0.5-20, using wider 0.3-30 range")
    
ax_size.scatter(df["pl_insol"], df["pl_rade"], s=5, color="#c3c2b7", label="All planets", zorder=1)    # x = insolation, y = planet radius
ax_size.set_xscale("log")
ax_size.set_yscale("log")
ax_size.set_yticks([0.5, 1, 1.5, 2, 5, 10, 20], labels=["0.5", "1", "1.5", "2", "5", "10", "20"])
ax_size.set_xlabel("Insolation (Earth = 1)")
ax_size.set_ylabel("Planet radius (Earth = 1)")

ax_size.set_title("Most habitable-zone planets are too large to be rocky")
ax_size.legend(loc="upper right", fontsize=8, labelspacing=1.2, frameon=False)

fig_size.tight_layout()
fig_size.savefig("radius_diagram.png", dpi=200, bbox_inches="tight")

plt.show()