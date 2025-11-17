# src/perceel_radius.py
from pathlib import Path
import pandas as pd
import numpy as np
import requests, re
from math import radians, sin, cos, sqrt, atan2
import pgeocode
import folium
from folium.plugins import FloatImage

# ---------- Path to data ----------
ROOT = Path(__file__).resolve().parents[1]
CSV  = ROOT / "data" / "data_afvoerlocaties_2024.csv"  

o_lat_global = None
o_lon_global = None

# ---------- Helpers ----------
def valideer_perceelcode(perceelcode: str) -> bool:
    # Validate a parcel code in the format:
    # 3-4 letters, space, 1 letter, space, 4 digits (e.g., ABCD A 1234)
    patroon = r"^[A-Z]{3,4}\d{0,2}\s[A-Z]\s\d{1,5}$"
    return bool(re.match(patroon, perceelcode))

def zoek_perceel_coordinaten(perceelcode: str) -> tuple[float, float]:
    # Retrieve (lat, lon) for a parcel code via PDOK. Returns (lat, lon)
    # 1) suggest → id
    s_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/suggest"
    r = requests.get(s_url, params={"q": perceelcode, "fq": "type:perceel"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data["response"]["numFound"] == 0:
        raise ValueError("Parcel not found in PDOK (suggest).")
    perceel_id = data["response"]["docs"][0]["id"]

    # 2) lookup → centroide_ll
    l_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup"
    r = requests.get(l_url, params={"id": perceel_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data["response"]["numFound"] == 0:
        raise ValueError("Parcel not found in PDOK (lookup).")
    doc = data["response"]["docs"][0]

    # PDOK centroide_ll is: "POINT(lon lat)"
    m = re.search(r"POINT\s*\(([-\d.]+)\s+([-\d.]+)\)", doc.get("centroide_ll", ""))
    if not m:
        raise ValueError("Could not parse 'centroide_ll'.")
    lon, lat = map(float, m.groups())
    return lat, lon

def find_column(pattern: str, columns, error_msg: str) -> str:
    matches = [c for c in columns if pattern in c.lower()]
    if not matches:
        raise ValueError(error_msg)
    return matches[0]

def haversine_km(lat1, lon1, lat2, lon2):
    # Vectorized haversine. lat2/lon2 may be numpy arrays
    R = 6371.0088
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lat2, lon2 = np.radians(lat2), np.radians(lon2)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def normalize_pc(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return re.sub(r"\s+", "", s.upper())

def detect_country(pc_clean: str) -> str | None:
    # NL PC6: 1234AB | BE: 4 digits | DE: 5 digits
    if re.fullmatch(r"\d{4}[A-Z]{2}", pc_clean):
        return "NL6"
    if re.fullmatch(r"\d{4}", pc_clean):
        return "BE"
    if re.fullmatch(r"\d{5}", pc_clean):
        return "DE"
    return None

# Select, within the current radius, the largest locations (per group_key, default PC4/PC6 key) until the target (ton/year) is reached 
def top_postcodes_tot_target(in_range: pd.DataFrame, kg_col: str, laadlocatie_col: str, root: Path, group_key: str = "POSTCODE_KEY", radius_km: float = None, target_ton: float | None = None):
    df = in_range.copy()
    df[kg_col] = pd.to_numeric(df[kg_col], errors="coerce")
    df[laadlocatie_col] = pd.to_numeric(df[laadlocatie_col], errors="coerce")

    # Yearly aggregation per PC6/PC4: sum kg, sum laadlocaties, mean distance and coordinates
    yearly = (
        df.groupby(group_key, as_index=False)
          .agg(
              kg_sum=(kg_col, "sum"),
              laadlocaties=(laadlocatie_col, "sum"),
              afstand_km=("afstand_km", "mean"),
              latitude=("latitude", "mean"),
              longitude=("longitude", "mean"),
          )
          .dropna(subset=["kg_sum"])
    )
    yearly["ton"] = yearly["kg_sum"] / 1000.0
    yearly["laadlocaties"] = yearly["laadlocaties"].fillna(0).astype(float)

    # Sort by ton (desc). If equal ton, prefer fewer laadlocaties
    yearly = yearly.sort_values(["ton", "laadlocaties"], ascending=[False, True]).reset_index(drop=True)

    # Ask user for target
    if target_ton is None:
        target_ton = float(input("Enter the target (tons/year) to select largest loading locations within the radius: ").strip())

    # greedy selection until target is reached
    picked_rows, cum_ton, cum_loc = [], 0.0, 0
    for _, r in yearly.iterrows():
        if cum_ton >= target_ton:
            break
        picked_rows.append(r)
        cum_ton += r["ton"]
        cum_loc += int(r["laadlocaties"])

    picked = pd.DataFrame(picked_rows)

    print("\n=== Largest locations up to target (within radius) ===")
    print(f"Target (tons/year):       {target_ton:,.2f}")
    print(f"Chosen {group_key}s:     {len(picked)}")
    print(f"Total tons reached:       {cum_ton:,.2f}")
    print(f"Total loading locations:  {cum_loc}")

    if picked.empty:
        print("[Info] No selection (check target/data).")
        return picked

    picked = picked.assign(
        loading_locations=picked["laadlocaties"].astype(int),
        tons=picked["ton"].round(2),
    )
    picked["distance_km"] = picked["afstand_km"].round(1)

    cols_show = [group_key, "tons", "loading_locations", "distance_km"]
    print()
    print(picked[cols_show].to_string(index=False))
    out_html = (root / "outputs" / "kaart_grootste_locaties.html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    save_map_for_picked(picked, o_lat_global, o_lon_global, out_html, radius_km=radius_km)

# Create an interactive map with: blue star (parcel point) and red dots (selected POSTCODE_KEYs)
def save_map_for_picked(picked: pd.DataFrame, o_lat: float, o_lon: float, out_html: Path, radius_km: float = None):
    if picked.empty or {"latitude", "longitude"}.isdisjoint(picked.columns):
        print("[Info] No coordinates in 'picked' to plot.")
        return

    # Center map on the parcel
    m = folium.Map(location=[o_lat, o_lon], zoom_start=7, control_scale=True)

    # Mark the parcel
    folium.Marker(
        [o_lat, o_lon],
        icon=folium.Icon(color="blue", icon="star"), 
        tooltip="Parcel point",
        popup=f"Perceel (lat={o_lat:.5f}, lon={o_lon:.5f})"
    ).add_to(m)

    # Add radius circle around parcel
    if radius_km is not None:
        folium.Circle(
            location=[o_lat, o_lon],
            radius=radius_km * 1000,   # km → meters
            color="royalblue",
            fill =True,
            fill_opacity=0.04,
            weight=2,
            tooltip=f"Radius {radius_km:.0f} km"
        ).add_to(m)

    # Selected locations (red markers)
    for _, r in picked.iterrows():
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        key = r.get("POSTCODE_KEY", "")
        ton = r.get("ton", float("nan"))
        laad = r.get("laadlocaties", float("nan"))
        afstand = r.get("afstand_km", float("nan"))
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="red",
            fill=True,
            fill_opacity=0.9,
            tooltip=f"{key}",
            popup=(f"<b>{key}</b><br>"
                   f"Tons/year: {ton:,.2f}<br>"
                   f"Loading locations: {int(laad)}<br>"
                   f"Distance: {afstand:.1f} km")
        ).add_to(m)

    
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 180px; 
        z-index: 9999; font-size: 14px;
        background-color: white;
        padding: 10px; border:2px solid grey; border-radius:8px;
    ">
    <b>Legend</b><br>
    <span style="color: blue;">★</span> Parcel (origin)<br>
    <span style="color: red;">●</span> Selected zip code<br>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))
    m.save("kaart.html")
    print(f"\n[Info] Map saved to '{out_html}'. Open this file manually in your browser. (via download in codespace)")

# ---------- Main flow ----------
def run(perceelcode: str, radius_km: float, save_outputs: bool = False, include_german: bool = False):
    if not valideer_perceelcode(perceelcode):
        raise ValueError("Invalid parcel code format. Example: 'ABCD A 1234'.")

    # 1) Get origin coordinates
    o_lat, o_lon = zoek_perceel_coordinaten(perceelcode)
  
    global o_lat_global, o_lon_global
    o_lat_global, o_lon_global = o_lat, o_lon

    # 2) Load data
    df = pd.read_csv(CSV, sep=";")  

    # comma→dot for numeric-looking string columns
    for c in df.columns:
        if df[c].dtype == object and df[c].astype(str).str.contains(",", na=False).any():
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")

    # 3) Find required columns
    postcode_col      = find_column("postcode", df.columns, "No postcode column found")
    kg_col            = find_column("kg", df.columns, "No 'kg' column found.")
    laadlocatie_col   = find_column("aantal_laadlocaties", df.columns, "No 'aantal_laadlocaties' column found.")

    # 4) Normalize postcodes and detect country/format
    pc_raw_col = postcode_col  
    df["PC_CLEAN"] = df[pc_raw_col].astype(str).apply(normalize_pc)
    df["PC_TYPE"]  = df["PC_CLEAN"].apply(detect_country)  # NL6, BE, DE, of None
    df = df[df["PC_TYPE"].notna()].copy() 

    # 4b) POSTCODE_KEY = the display/grouping key you want
    # - NL: use PC6 when available (we detected NL6)
    # - BE: 4-digit
    # - DE: 5-digit
    df["POSTCODE_KEY"] = np.where(
        df["PC_TYPE"].eq("NL6"), df["PC_CLEAN"],
        np.where(df["PC_TYPE"].eq("BE"), df["PC_CLEAN"],
                 np.where(df["PC_TYPE"].eq("DE"), df["PC_CLEAN"], np.nan))
    )

    # 4c) GEO_KEY + GEO_COUNTRY for geocoding with pgeocode:
    # - NL: geocode on PC4 (first 4 of PC6)
    # - BE: geocode on 4 digits
    # - DE: geocode on 5 digits
    df["GEO_COUNTRY"] = np.where(df["PC_TYPE"].eq("NL6"), "NL",
                         np.where(df["PC_TYPE"].eq("BE"), "BE",
                         np.where(df["PC_TYPE"].eq("DE"), "DE", None)))
    df["GEO_KEY"] = np.where(df["GEO_COUNTRY"].eq("NL"),
                             df["PC_CLEAN"].str[:4],      # NL → PC4 from PC6
                     np.where(df["GEO_COUNTRY"].eq("BE"),
                              df["PC_CLEAN"],              # BE → 4-digit PC
                     np.where(df["GEO_COUNTRY"].eq("DE"),
                              df["PC_CLEAN"],              # DE → 5-digit PLZ
                              np.nan)))
    
    # === Filter out German postcodes unless the user wants them ===
    if not include_german:
       df = df[df["GEO_COUNTRY"].ne("DE") | df["GEO_COUNTRY"].isna()].copy()

    # 5) Coordinates per country via pgeocode
    nl_keys = sorted(df.loc[df["GEO_COUNTRY"].eq("NL"), "GEO_KEY"].dropna().unique().tolist())
    be_keys = sorted(df.loc[df["GEO_COUNTRY"].eq("BE"), "GEO_KEY"].dropna().unique().tolist())
    de_keys = sorted(df.loc[df["GEO_COUNTRY"].eq("DE"), "GEO_KEY"].dropna().unique().tolist())

    frames = []

    if nl_keys:
        nomi_nl = pgeocode.Nominatim("NL")
        nl_coords = nomi_nl.query_postal_code(nl_keys)[["postal_code","latitude","longitude"]]
        nl_coords = nl_coords.rename(columns={"postal_code": "GEO_KEY"})
        nl_coords["GEO_COUNTRY"] = "NL"
        frames.append(nl_coords)

    if be_keys:
        nomi_be = pgeocode.Nominatim("BE")
        be_coords = nomi_be.query_postal_code(be_keys)[["postal_code","latitude","longitude"]]
        be_coords = be_coords.rename(columns={"postal_code": "GEO_KEY"})
        be_coords["GEO_COUNTRY"] = "BE"
        frames.append(be_coords)

    if de_keys:
        nomi_de = pgeocode.Nominatim("DE")
        de_coords = nomi_de.query_postal_code(de_keys)[["postal_code","latitude","longitude"]]
        de_coords = de_coords.rename(columns={"postal_code": "GEO_KEY"})
        de_coords["GEO_COUNTRY"] = "DE"
        frames.append(de_coords)

    coords_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["GEO_KEY","latitude","longitude","GEO_COUNTRY"])

    # Merge on (GEO_KEY, GEO_COUNTRY) to avoid collisions
    df = df.merge(coords_df, on=["GEO_KEY","GEO_COUNTRY"], how="left")

    MANUAL_PC6_COORDS = {
        "3062CG": (51.9278, 4.5296),
    }

    for pc6, (lat_fix, lon_fix) in MANUAL_PC6_COORDS.items():
        mask = df["PC_CLEAN"].eq(pc6)
        df.loc[mask, "latitude"] = lat_fix
        df.loc[mask, "longitude"] = lon_fix

    # 6) Distances and filter by radius
    df_geo = df.dropna(subset=["latitude", "longitude"]).copy()
    dists = haversine_km(o_lat, o_lon, df_geo["latitude"].values, df_geo["longitude"].values)
    df_geo["afstand_km"] = dists
    in_range = df_geo.loc[df_geo["afstand_km"] <= radius_km].copy()

    # 7) Aggregations
    # Sum loading locations per postcode key 
    total_laadlocaties = (
    in_range.groupby("POSTCODE_KEY")[laadlocatie_col]
            .sum()
            .fillna(0)
            .astype(float)
            .sum()
    )

    # >>> Largest locations within radius up to target (list with POSTCODE_KEY, tons, laadlocaties)
    top_postcodes_tot_target(in_range, kg_col, laadlocatie_col, ROOT, group_key="POSTCODE_KEY", radius_km=radius_km)

    # totals
    in_range[kg_col] = pd.to_numeric(in_range[kg_col], errors="coerce")
    total_ton = in_range[kg_col].sum() / 1000

    # 8) Summary
    summary = pd.DataFrame({
        "Origin":         [f"lat: {o_lat:.6f}, lon: {o_lon:.6f}"],
        "Parcel code":   [perceelcode],
        "Radius_km":       [radius_km],
        "Rows_in_range":    [len(in_range)],
        "Total_tons":      [total_ton],
        "Total_loadlocs": [total_laadlocaties],
    })

    # Console output
    print(f"\nZip codes within {radius_km:.0f} km van lat: {o_lat:.5f}, lon: {o_lon:.5f}, perceel: {perceelcode}")
    print(f"Rows in range: {len(in_range)}")
    print(f"Total tons: {total_ton:,.2f}")
    print(f"Total loading locations: {total_laadlocaties}\n")
    
    return in_range, summary

# ---------- CLI ----------
if __name__ == "__main__":
    perceel = input("Parcel code: ").strip().upper()
    radius  = float(input("Radius in km: "))
    inc_de = input("Include German zip codes? (y/n): ").strip().lower()
    include_german = inc_de in ["j", "ja", "y", "yes"]
    run(perceel, radius, save_outputs=False, include_german=include_german)