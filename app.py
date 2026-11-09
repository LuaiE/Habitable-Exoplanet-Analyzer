import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import re

from habitable import hz_edge
from monte_carlo import get_sigma

QUALITY_COLORS = {"high": "#184f95", "medium": "#2a78d6", "low": "#86b6ef"}

COMPOSITION_TEXT = {"rocky": "Rocky (Earth-like)", "water_world": "Water world",
                    "gas_envelope": "Gas envelope", "unknown": "Unknown (no measured mass)"}

NASA_NAME_FIXES = {"Proxima Cen b": "proxima-centauri-b"}


def nasa_catalog_url(name):
    slug = NASA_NAME_FIXES.get(name) or re.sub(r"[^a-z0-9]+", "-", name.lower().replace("'", "")).strip("-")
    return f"https://science.nasa.gov/exoplanet-catalog/{slug}/"

st.set_page_config(page_title="Habitable Exoplanet Analyzer", layout="wide")


@st.cache_data(ttl="1d") #refresh data once a day
def load_results():
    return pd.read_csv("results/planets_mc.csv")


def hz_chart(df, candidates):
    fig = go.Figure()

    teff = np.linspace(2500, 7200, 300)
    teff_used = np.clip(teff, 2600, 7200)
    for inner, outer, name, opacity in [("recent_venus", "early_mars", "Optimistic HZ", 0.15),
                                        ("runaway_greenhouse", "max_greenhouse", "Conservative HZ", 0.35)]:
        x = np.concatenate([hz_edge(teff_used, inner), hz_edge(teff_used, outer)[::-1]])
        y = np.concatenate([teff, teff[::-1]])
        fig.add_trace(go.Scatter(x=x, y=y, fill="toself", mode="none", name=name,
                                 fillcolor=f"rgba(27, 175, 122, {opacity})", hoverinfo="skip"))

    fig.add_trace(go.Scatter(x=df["pl_insol"], y=df["st_teff"], mode="markers", name="All planets",
                             marker=dict(size=4, color="#c3c2b7"),
                             text=df["pl_name"], hovertemplate="%{text}<extra></extra>"))

    for quality, color in QUALITY_COLORS.items():
        subset = candidates[candidates["data_quality"] == quality]
        fig.add_trace(go.Scatter(
            x=subset["pl_insol"], y=subset["st_teff"], mode="markers",
            name=f"Candidate ({quality} data quality)",
            marker=dict(size=10, color=color, line=dict(width=1, color="white")),
            customdata=np.stack([subset["pl_rade"], subset["p_strong"] * 100], axis=-1),
            text=subset["pl_name"],
            hovertemplate="<b>%{text}</b><br>Starlight: %{x:.2f}<br>Star temp: %{y:.0f} K"
                          "<br>Radius: %{customdata[0]:.2f}<br>Probability: %{customdata[1]:.0f}%<extra></extra>",
        ))

    fig.add_trace(go.Scatter(x=[1], y=[5780], mode="markers", name="Earth",
                             marker=dict(symbol="star", size=16, color="#1a1a19"),
                             hovertemplate="Earth<extra></extra>"))

    fig.update_xaxes(type="log", range=[np.log10(5), np.log10(0.1)], title="Insolation (Earth = 1)")
    fig.update_yaxes(range=[2400, 7300], title="Star temperature (K)")
    fig.update_layout(height=550, legend=dict(font=dict(size=11)), margin=dict(t=20))
    return fig

def system_chart(df, planet):
    system = df[df["hostname"] == planet["hostname"]].dropna(subset=["pl_orbsmax"])
    luminosity = (system["pl_insol"] * system["pl_orbsmax"] ** 2).median()
    if system.empty or not np.isfinite(luminosity):
        return None

    teff = np.clip(planet["st_teff"], 2600, 7200)
    edge = {name: np.sqrt(luminosity / hz_edge(teff, name))
            for name in ["recent_venus", "runaway_greenhouse", "max_greenhouse", "early_mars"]}

    theta = np.linspace(0, 2 * np.pi, 200)
    fig = go.Figure()

    for inner, outer, name, opacity in [("recent_venus", "early_mars", "Optimistic HZ", 0.15),
                                        ("runaway_greenhouse", "max_greenhouse", "Conservative HZ", 0.35)]:
        r_in, r_out = edge[inner], edge[outer]
        x = np.concatenate([r_out * np.cos(theta), r_in * np.cos(theta[::-1])])
        y = np.concatenate([r_out * np.sin(theta), r_in * np.sin(theta[::-1])])
        fig.add_trace(go.Scatter(x=x, y=y, fill="toself", mode="none", name=name,
                                 fillcolor=f"rgba(27, 175, 122, {opacity})", hoverinfo="skip"))

    angles = np.linspace(0, 2 * np.pi, len(system), endpoint=False) + 0.4
    for angle, (_, p) in zip(angles, system.sort_values("pl_orbsmax").iterrows()):
        a = p["pl_orbsmax"]
        selected = p["pl_name"] == planet["pl_name"]
        fig.add_trace(go.Scatter(x=a * np.cos(theta), y=a * np.sin(theta), mode="lines",
                                 line=dict(color="#898781", width=1), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=[a * np.cos(angle)], y=[a * np.sin(angle)], mode="markers+text",
            text=[p["pl_name"].split()[-1]], textposition="top center", showlegend=False,
            marker=dict(size=14 if selected else 9, color="#184f95" if selected else "#5f5e5a",
                        line=dict(width=1, color="white")),
            hovertemplate=f"<b>{p['pl_name']}</b><br>Orbit: {a:.3f} AU<extra></extra>",
        ))

    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers", name=planet["hostname"],
                             marker=dict(size=18, color="#eda100"), hoverinfo="skip"))

    reach = 1.15 * max(system["pl_orbsmax"].max(), edge["early_mars"])
    fig.update_xaxes(range=[-reach, reach], title="Distance from star (AU)", zeroline=False)
    fig.update_yaxes(range=[-reach, reach], scaleanchor="x", showticklabels=False, zeroline=False)
    fig.update_layout(height=500, margin=dict(t=20), legend=dict(font=dict(size=11)))
    return fig

df = load_results()
candidates = df[df["within_optimistic"] & df["pl_type"].isin(["rocky", "uncertain"])]

st.sidebar.header("Filters")
min_prob = st.sidebar.slider("Minimum probability, conservative HZ (%)", 0, 100, 0, step=5)
qualities = st.sidebar.multiselect("Data quality", ["high", "medium", "low"], default=["high", "medium", "low"])
teff_range = st.sidebar.slider("Star temperature (K)", 2500, 7500, (2500, 7500), step=100)

filtered = candidates[
    (candidates["p_strong"] * 100 >= min_prob)
    & candidates["data_quality"].isin(qualities)
    & candidates["st_teff"].between(*teff_range)
]

st.title("Habitable Exoplanet Analyzer")
st.write("Which confirmed exoplanets could support liquid surface water, and how confident can we be? "
         "Live NASA data, published climate-model physics, and 10,000 Monte Carlo simulations per planet.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Planets analysed", f"{len(df):,}")
col2.metric("Habitable-zone candidates", len(candidates))
col3.metric("≥ 50% likely", int((df["p_strong"] >= 0.5).sum()))
col4.metric("≥ 90% likely", int((df["p_strong"] >= 0.9).sum()))

st.subheader("Habitable zone")
st.caption(f"Showing {len(filtered)} of {len(candidates)} candidates")
st.plotly_chart(hz_chart(df, filtered), width="stretch")

st.subheader("Top candidates")
top = filtered.sort_values("p_strong", ascending=False).copy()
top["Probability"] = top["p_strong"] * 100
top["Optimistic"] = top["p_optimistic"] * 100
top["Status"] = np.where(top["disputed"], "⚠️ Disputed", "")

st.dataframe(
    top[["pl_name", "Status", "Probability", "Optimistic", "composition", "pl_rade", "pl_insol", "st_teff", "data_quality"]],
    hide_index=True,
    column_config={
        "pl_name": "Planet",
        "Status": st.column_config.TextColumn("Status", width=85),
        "Probability": st.column_config.ProgressColumn("Conservative HZ", min_value=0, max_value=100, format="%.0f%%"),
        "Optimistic": st.column_config.ProgressColumn("Optimistic HZ", min_value=0, max_value=100, format="%.0f%%"),
        "pl_rade": st.column_config.NumberColumn("Radius (Earth = 1)", format="%.2f"),
        "pl_insol": st.column_config.NumberColumn("Starlight (Earth = 1)", format="%.2f"),
        "st_teff": st.column_config.NumberColumn("Star temp (K)", format="%.0f"),
        "data_quality": "Data quality", "composition": "Composition",
    },
)

st.subheader("Planet details")

if top.empty:
    st.info("No candidates match the current filters.")
else:
    name = st.selectbox("Choose a planet", top["pl_name"])
    planet = df[df["pl_name"] == name].iloc[0]
    if planet["disputed"]:
        st.warning("This planet's existence has been questioned in published research "
                   "(flagged as controversial in the NASA Exoplanet Archive). Treat its ranking with caution.")
    sigma = get_sigma(planet, "pl_rade")

    c1, c2, c3 = st.columns(3)
    c1.metric("Conservative HZ + solid or ocean surface", f"{planet['p_strong']:.0%}")
    c2.metric("Optimistic HZ + solid or ocean surface", f"{planet['p_optimistic']:.0%}")
    c3.metric("Earth-like rocky", f"{planet['p_rocky']:.0%}")
    c4, c5, c6 = st.columns(3)
    c4.metric("Radius (Earth = 1)", f"{planet['pl_rade']:.2f} ± {sigma:.2f}")
    c5.metric("Starlight (Earth = 1)", f"{planet['pl_insol']:.2f}")
    c6.metric("Star temp (K)", f"{planet['st_teff']:.0f}")

    st.write(f"**Host star:** {planet['hostname']}  ·  **Discovered by:** {planet['discoverymethod']}  ·  "
             f"**Data quality:** {planet['data_quality']}  ·  "
             f"**Composition:** {COMPOSITION_TEXT[planet['composition']]}")

    if planet["p_surface"] < planet["p_hz_conservative"]:
        st.write(f"Held back mainly by **composition**: {planet['p_surface']:.0%} chance of a solid or ocean surface, "
                 f"{planet['p_hz_conservative']:.0%} chance of being in the conservative habitable zone.")
    else:
        st.write(f"Held back mainly by **position**: {planet['p_hz_conservative']:.0%} chance of being in the "
                 f"conservative habitable zone, {planet['p_surface']:.0%} chance of a solid or ocean surface.")
        
    samples = np.random.default_rng(77).normal(planet["pl_rade"], sigma, 10000)
    hist = go.Figure(go.Histogram(x=samples, nbinsx=60, marker_color=QUALITY_COLORS[planet["data_quality"]]))
    hist.add_vline(x=1.5, line_dash="dash", line_color="#898781", annotation_text="Rocky limit")
    hist.add_vline(x=2.0, line_dash="dot", line_color="#898781", annotation_text="Gaseous above")
    hist.update_layout(height=320, margin=dict(t=30), showlegend=False,
                       xaxis_title="Simulated radius (Earth = 1)", yaxis_title="Simulations")
    st.plotly_chart(hist, width="stretch")
    st.caption("Shows radius uncertainty only. For planets with measured mass, composition comes from density instead.")

    st.markdown(f"[{planet['pl_name']} on NASA Science ↗]({nasa_catalog_url(planet['pl_name'])})  ·  "
                f"[{planet['hostname']} on the NASA Exoplanet Archive ↗]"
                f"(https://exoplanetarchive.ipac.caltech.edu/overview/{planet['hostname'].replace(' ', '%20')})")
    
    st.markdown(f"**The {planet['hostname']} system**")
    system_fig = system_chart(df, planet)
    if system_fig is None:
        st.caption("Not enough orbit data to draw this system.")
    else:
        st.plotly_chart(system_fig, width="stretch")
        st.caption("Orbit distances and habitable-zone rings are to scale. Planet and star markers are not, "
                   "and planets are spaced evenly around their orbits for readability.")