import pandas as pd
from pathlib import Path

def fetch_data():
    cols = ["pl_name", "hostname", "discoverymethod", "pl_controv_flag", "pl_rade", "pl_bmasse", "pl_bmassprov", "pl_orbper", "pl_orbsmax", "pl_orbeccen", 
            "pl_insol", "pl_eqt", "st_teff", "st_rad", "st_mass", "st_lum", "pl_radeerr1", "pl_radeerr2", "pl_insolerr1", "pl_insolerr2",
            "st_tefferr1", "st_tefferr2", "pl_bmasseerr1", "pl_bmasseerr2", "pl_bmasselim"]  # all needed collumns
    
    query = "select " + ",".join(cols) + " from pscomppars" #allows selecting each collumnn from the table
    url = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        + query.replace(" ", "+") + "&format=csv")

    path = Path("data/planets_raw.csv")
    if path.exists():
        df = pd.read_csv(path)
        print(f"Loaded {len(df)} planets from cache")
    else:
        df = pd.read_csv(url)
        path.parent.mkdir(exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Downloaded {len(df)} planets from NASA")


    return df

def fill_derived(df):

    #calculates orb distance first since needed for insolation calcs.  
    mask = df["pl_orbsmax"].isna() & df["st_mass"].notna() & df["pl_orbper"].notna() #finds where orbdistance is absent but can be calculated
    df.loc[mask, "pl_orbsmax"] = ((df.loc[mask, "st_mass"])*(((df.loc[mask, "pl_orbper"])/365.25)**2))**(1/3) #kepler's law
    df["pl_orbsmax_derived"]=mask #states if derived

    mask = df["pl_insol"].isna() & df["st_lum"].notna() & df["pl_orbsmax"].notna() #finds where insolation is absent but it can also be calculated
    df.loc[mask, "pl_insol"] = 10 ** df.loc[mask, "st_lum"] / df.loc[mask, "pl_orbsmax"] ** 2 #update only stated rows with calculated insol
    df["pl_insol_derived"] = mask #clarifies if we derived it or not

    print(f"Filled {df['pl_orbsmax_derived'].sum()} distances, {df['pl_insol_derived'].sum()} insolations")
    return df

def elim_bad_rows(df):
    # disputed planets are kept but flagged, so famous ones like Kepler-186 f don't silently dissapear
    df["disputed"] = df["pl_controv_flag"] == 1

    bad = (df["pl_rade"] <= 0) | (df["pl_orbeccen"] >= 1)  # physically impossible values
    print("Removing", bad.sum(), "impossible planets;", df["disputed"].sum(), "disputed planets kept and flagged")
    df = df[~bad].reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = fetch_data()
    df = fill_derived(df)
    df = elim_bad_rows(df)
    df.to_csv("data/planets_cleaned.csv", index=False)
    print("Saved", len(df), "planets")