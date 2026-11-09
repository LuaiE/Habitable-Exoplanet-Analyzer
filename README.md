# Habitable Exoplanet Analyzer

Finds the confirmed exoplanets most likely to support liquid surface water, using live NASA data, published climate-model physics, and an honest account of how reliable each measurement is.

![Habitable zone diagram](hz_diagram.png)

## How to Run

1. Clone the repo and open the folder in a terminal
2. Install dependencies: `pip install -r requirements.txt`
3. Run the pipeline in order:

```bash
python fetch_data.py    # download + clean NASA data
python habitable.py     # classify + rank candidates
python plots.py         # generate the charts
```

Results are saved to `data/candidates.csv`. To pull fresh data from NASA, delete `data/planets_raw.csv` and rerun.

## How It Works

The pipeline downloads every confirmed exoplanet from the NASA Exoplanet Archive and runs each one through three tests:

1. **Habitable zone:** is the planet receiving the right amount of starlight for liquid water, given its star's temperature? Uses the Kopparapu et al. (2014) climate-model limits.
2. **Rocky or gaseous:** is it small enough to have a solid surface? Uses radius cutoffs from Rogers (2015).
3. **Atmosphere retention:** is its gravity strong enough to hold an atmosphere against its star's energy? Uses a simplified "cosmic shoreline" score after Zahnle & Catling (2017).

Planets that pass the first two tests become **candidates**, and every result is tagged with a **data-quality tier**, so measured values are never confused with estimates.

## Results

*November 2026 archive snapshot. Numbers update as NASA adds planets.*

| Metric | Result |
|---|---|
| Planets analysed | 6,406 |
| In the optimistic habitable zone | 284 |
| Rocky habitable-zone candidates | **45** |
| Candidates in the conservative zone | 27 |
| Well-known candidates recovered | **8 / 8** |
| Candidates with mass *and* radius measured | 12 |

**Key findings**
- **Most habitable-zone planets are too large to be rocky:** only 45 of 284 pass the size test.
- **Nearly every candidate orbits a cool red dwarf.** This is largely detection bias: red dwarfs' habitable zones are close in, so planets there are easier to detect.
- **Many "rocky" labels rest on estimates.** For 16 candidates, the radius was never observed.

![Planet size diagram](radius_diagram.png)

### Strongest Candidates
Mass and radius both measured, conservative habitable zone.

| Planet | Radius (Earth = 1) | Starlight (Earth = 1) | Star Temp (K) |
|---|---|---|---|
| TRAPPIST-1 e | 0.92 | 0.65 | 2566 |
| TRAPPIST-1 f | 1.05 | 0.37 | 2566 |
| TRAPPIST-1 g | 1.13 | 0.25 | 2566 |
| GJ 1061 d | 1.16 | 0.60 | 2953 |
| LP 890-9 c | 1.37 | 0.91 | 2850 |

## Classifications

**Habitable zone**

| Zone | Inner edge | Outer edge |
|---|---|---|
| Conservative | Runaway greenhouse | Maximum greenhouse |
| Optimistic | Recent Venus | Early Mars |

**Planet type**

| Type | Radius (Earth = 1) |
|---|---|
| Rocky | below 1.5 |
| Uncertain | 1.5 – 2.0 (the "radius gap") |
| Gaseous | above 2.0 |

**Data quality**

| Tier | What was measured | Candidates |
|---|---|---|
| High | Mass and radius | 12 |
| Medium | Radius only (mass estimated from radius) | 17 |
| Low | Minimum mass only (radius estimated) | 16 |

## Files

```
habitable-exoplanet-analyzer/
├── fetch_data.py        — Downloads, caches and cleans NASA data
├── habitable.py         — Habitable zone, planet type, data quality, atmosphere score
├── plots.py             — Generates the charts
├── hz_diagram.png       — Habitable zone chart
├── radius_diagram.png   — Planet size chart
├── requirements.txt     — Python dependencies
├── README.md
└── data/                — Generated CSVs (not committed; recreated by the scripts)
```

## Technical Notes

- Data comes from the archive's **Planetary Systems Composite Parameters** table via its TAP API, with one row per planet and the best available values
- **Gaps are filled with physics, not dropped:** missing orbital distances come from Kepler's third law, and missing starlight from stellar luminosity, recovering 760 values. Every calculated value is flagged
- **Validated against known candidates:** the method recovers all 8 well-known habitable-zone planets tested
- **Cool-star edge case:** TRAPPIST-1 (2566 K) sits just below the Kopparapu formula's calibrated range (2600–7200 K). Slightly-out-of-range stars use the nearest calibrated value and are flagged. For TRAPPIST-1 this changes the zone edges by under 0.5% and reproduces the limits published by Gillon et al. (2017)
- Atmosphere scores are checked against the Solar System: Earth = 1.0, Mars ≈ 0.09

## Limitations

- Assumes Earth-like planets; different atmospheres, clouds or slow rotation can shift the zone edges
- The rocky cutoff was derived from short-period planets and may not transfer perfectly to cooler orbits
- The atmosphere score ignores X-ray/UV radiation, which red dwarfs emit heavily, so real risk is likely higher for most candidates
- Magnetic fields, plate tectonics and actual atmospheres can't be assessed from this data
- Being in the habitable zone means liquid water is *possible*, not confirmed

## References

- Kopparapu et al. (2014), *Habitable Zones around Main-sequence Stars: Dependence on Planetary Mass*, ApJL 787, L29
- Rogers (2015), *Most 1.6 Earth-radius Planets are not Rocky*, ApJ 801, 41
- Zahnle & Catling (2017), *The Cosmic Shoreline*, ApJ 843, 122
- Gillon et al. (2017), *Seven temperate terrestrial planets around the nearby ultracool dwarf star TRAPPIST-1*, Nature 542, 456
- Data: [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/), operated by Caltech under contract with NASA

---

Built by Luai
