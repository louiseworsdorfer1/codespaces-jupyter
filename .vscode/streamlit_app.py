import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# import your functions/vars
from src.perceel_radius import run, ROOT, o_lat_global, o_lon_global

st.set_page_config(page_title="Parcel Radius Analysis", layout="wide")

st.title("Parcel Radius Analysis")
st.caption("Select postcodes within a radius around a parcel, compute tons/year, and pick largest locations up to a target.")

with st.form("inputs"):
    perceel = st.text_input("Parcel code", value="SLD02 H 1842")
    radius_km = st.number_input("Radius (km)", min_value=1.0, max_value=500.0, value=40.0, step=1.0)
    include_german = st.checkbox("Include German zip codes?", value=True)
    target_ton = st.number_input("Target (tons/year)", min_value=0.0, value=60000.0, step=1000.0)
    submitted = st.form_submit_button("Run")

if not submitted:
    st.info("Fill the form and click **Run** to start.")
else:
    try:
        with st.spinner("Running analysis..."):
            in_range, summary = run(perceel, radius_km, save_outputs=False, include_german=include_german)
            # Aggregate like in your function, then greedily pick to target
            df = in_range.copy()
            df["kg"] = pd.to_numeric(df["kg"], errors="coerce")

            yearly = (
                df.groupby("POSTCODE_KEY", as_index=False)
                  .agg(
                      kg_sum=("kg", "sum"),
                      laadlocaties=("aantal_laadlocaties", "sum"),
                      afstand_km=("afstand_km", "mean"),
                      latitude=("latitude", "mean"),
                      longitude=("longitude", "mean"),
                  )
                  .dropna(subset=["kg_sum"])
            )
            yearly["ton"] = yearly["kg_sum"] / 1000.0
            yearly["laadlocaties"] = yearly["laadlocaties"].fillna(0).astype(float)
            yearly = yearly.sort_values(["ton", "laadlocaties"], ascending=[False, True]).reset_index(drop=True)

            picked_rows, cum_ton, cum_loc = [], 0.0, 0
            for _, r in yearly.iterrows():
                if cum_ton >= target_ton:
                    break
                picked_rows.append(r)
                cum_ton += r["ton"]
                cum_loc += int(r["laadlocaties"])
            picked = pd.DataFrame(picked_rows)

        # Show outputs
        st.subheader("Summary")
        st.dataframe(summary)

        st.subheader("Largest locations up to target")
        picked_out = (
            picked.assign(
                tons=picked["ton"].round(2),
                loading_locations=picked["laadlocaties"].astype(int),
                distance_km=picked["afstand_km"].round(1),
            )[["POSTCODE_KEY", "tons", "loading_locations", "distance_km"]]
            if not picked.empty else
            pd.DataFrame(columns=["POSTCODE_KEY","tons","loading_locations","distance_km"])
        )
        st.dataframe(picked_out, use_container_width=True)

        # Download table
        if not picked_out.empty:
            st.download_button(
                "Download table (CSV)",
                picked_out.to_csv(index=False).encode("utf-8"),
                file_name="largest_locations.csv",
                mime="text/csv"
            )

        # Map
        st.subheader("Map")
        if not picked.empty:
            m = folium.Map(location=[o_lat_global, o_lon_global], zoom_start=9, control_scale=True)

            # center marker
            folium.Marker(
                [o_lat_global, o_lon_global],
                icon=folium.Icon(color="blue", icon="star"),
                tooltip="Parcel center",
            ).add_to(m)

            # radius circle (solid + light fill)
            folium.Circle(
                location=[o_lat_global, o_lon_global],
                radius=radius_km * 1000,
                color="royalblue",
                weight=3,
                fill=True,
                fill_opacity=0.1,
                tooltip=f"Radius {radius_km:.0f} km"
            ).add_to(m)

            for _, r in picked.iterrows():
                folium.CircleMarker(
                    location=[float(r["latitude"]), float(r["longitude"])],
                    radius=6, color="red", fill=True, fill_opacity=0.9,
                    tooltip=f"{r['POSTCODE_KEY']}",
                    popup=(f"<b>{r['POSTCODE_KEY']}</b><br>"
                           f"Tons/year: {r['ton']:.2f}<br>"
                           f"Loading locations: {int(r['laadlocaties'])}<br>"
                           f"Distance: {r['afstand_km']:.1f} km")
                ).add_to(m)

            st_folium(m, height=600)
        else:
            st.info("No locations selected for the chosen target/radius.")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
