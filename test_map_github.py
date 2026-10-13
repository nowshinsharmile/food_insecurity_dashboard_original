# ==========================================================
# STREAMLIT FOOD ACCESS DASHBOARD
# ==========================================================


import streamlit as st
from pathlib import Path
st.set_page_config(layout="wide", page_title="Bivariate Classification Visualization")

import geopandas as gpd
import pandas as pd
import folium
import altair as alt
from streamlit_folium import st_folium

# ==========================================================
# FILE PATHS
# ==========================================================
# Resolve data files relative to this script so the same code works
# locally and when deployed directly from a GitHub repository.

BASE_DIR = Path(__file__).resolve().parent

excel_file = BASE_DIR / "SNAP_Bivariate _Classification_Dataset_original_data.xlsx"
shapefile = BASE_DIR / "cb_2023_37_tract_500k" / "cb_2023_37_tract_500k.shp"


# Fail early with a clear message if deployment files are missing.

if not excel_file.exists():

    st.error(f"Excel file not found: {excel_file}")

    st.stop()



if not shapefile.exists():

    st.error(f"Census tract shapefile not found: {shapefile}")

    st.stop()





# ==========================================================

# LOAD DATA

# ==========================================================



@st.cache_data

def load_data():



    df = pd.read_excel(excel_file, sheet_name="Sheet3")

    agency_df = pd.read_excel(excel_file, sheet_name="Agency_Data")

    tracts = gpd.read_file(shapefile, engine="pyogrio")



    return df, agency_df, tracts





df, agency_df, tracts = load_data()





# ==========================================================

# CLEAN DATA

# ==========================================================



df["tractid"] = df["tractid"].astype(str).str.zfill(11)

tracts["GEOID"] = tracts["GEOID"].astype(str)



gdf = tracts.merge(df, left_on="GEOID", right_on="tractid", how="inner")



gdf = gdf.to_crs(epsg=4326)



# ==========================================================

# SERVICE AREA MAP BOUNDS

# ==========================================================

# Automatically fit each map to the census tracts in the

# SHFBNWNC service-area dataset instead of using a fixed

# statewide/regional starting view.

minx, miny, maxx, maxy = gdf.total_bounds

service_area_bounds = [[miny, minx], [maxy, maxx]]



gdf["LI/LA"] = gdf["LI/LA"].astype(str)

# Human-readable LI/LA labels for tables and charts.
# Keep the original LI/LA column unchanged for map filtering.
gdf["LI/LA Status"] = gdf["LI/LA"].replace({
    "1": "LI/LA",
    "0": "Not LI/LA",
    "Not in Database": "Not In Data",
    "Not In Database": "Not In Data"
})





# ==========================================================

# AGENCY POINT DATA

# ==========================================================



agency_gdf = gpd.GeoDataFrame(

    agency_df,

    geometry=gpd.points_from_xy(agency_df["long"], agency_df["lat"]),

    crs="EPSG:4326"

)





# ==========================================================

# COLOR DEFINITIONS

# ==========================================================



snap_colors = {

    "Above SNAP Median,No Agency Presence": "#ea524a",

    "Below SNAP Median,No Agency Presence": "#6ecffa",

    "Below SNAP Median,Agency Presence": "#7dba53",

    "Above SNAP Median,Agency Presence": "#f9dd5f"

}



change_colors = {

    "Increase": "#93c883",

    "Decrease": "#e28980",

    "No Change": "#d5d487",

    "No Agency": "#e5acd0"

}





def get_lila_color(val):



    if val.lower() in ["not in data", "not in database"]:

        return "#e0e0e0"



    if val == "1":

        return "#e5513f"



    return "#defd93"





# ==========================================================

# PAGE TITLE

# ==========================================================



st.title("Food Access and SNAP Need Dashboard")



st.markdown(

    """

This dashboard shows **food need and food access** across census tracts in the

Second Harvest Food Bank of Northwest North Carolina service area.



**SNAP Bivariate Classification** combines two things:

- whether SNAP participation is **above or below the service-area median**

- whether a food-assistance agency is **located in the tract**



**LI/LA** means **Low-Income and Low-Access**, a USDA measure used to identify

areas where residents may have lower income and limited access to grocery stores.



**Data sources:** ACS 5-year estimates (2022 and 2023), partner-agency data,

U.S. Census Bureau tract boundaries, and USDA Economic Research Service LI/LA data.

"""

)





# ==========================================================

# MAP TYPE SELECTOR

# ==========================================================



st.subheader("Compare SNAP Need and Food Access")



map_mode = st.selectbox(

    "Select map visualization",

    ["SNAP Bivariate Classification", "LI/LA Classification"]

)



if map_mode == "SNAP Bivariate Classification":

    st.info(

        "How to read this map: each tract is grouped by whether its SNAP participation is "

        "above or below the service-area median and whether a food-assistance agency is "

        "located in that tract. The map therefore shows two dimensions at the same time."

    )

else:

    st.info(

        "How to read this map: LI/LA means Low-Income and Low-Access. This view shows the "

        "LI/LA status recorded for each tract in the project dataset, based on USDA ERS "

        "food-access information."

    )





# ==========================================================

# SNAP MAP LOGIC

# ==========================================================



if map_mode == "SNAP Bivariate Classification":



    acs_year = st.selectbox("Select ACS 5-Year SNAP Estimate", ["2022", "2023"])



    if acs_year == "2022":

        formulation_col = "Formulation 2022"

    else:

        formulation_col = "Formulation 2023"



    selected = st.multiselect(

        "Filter bivariate categories",

        options=list(snap_colors.keys()),

        default=list(snap_colors.keys())

    )



    filtered_gdf = gdf[gdf[formulation_col].isin(selected)].copy()

    filtered_gdf["color"] = filtered_gdf[formulation_col].map(snap_colors)



else:



    selected = st.multiselect(

        "Filter LI/LA status",

        options=["1","0","Not In Data"],

        default=["1","0","Not In Data"]

    )



    filtered_gdf = gdf[gdf["LI/LA"].isin(selected)].copy()

    filtered_gdf["color"] = filtered_gdf["LI/LA"].apply(get_lila_color)





# ==========================================================

# MAP 1

# ==========================================================



m = folium.Map(tiles="OpenStreetMap")

m.fit_bounds(service_area_bounds, padding=(20, 20))



def style_function(feature):

    return {

        "fillColor": feature["properties"]["color"],

        "color": "black",

        "weight": 0.3,

        "fillOpacity": 0.7

    }



tooltip_fields = ["County","tractid","Agency Count","Average Increase in Visit"]



folium.GeoJson(

    filtered_gdf,

    style_function=style_function,

    tooltip=folium.GeoJsonTooltip(

        fields=tooltip_fields,

        aliases=["County","Tract","Agency Count","Visit Change"]

    )

).add_to(m)



# ----------------------------------------------------------

# MAP LEGEND

# ----------------------------------------------------------

if map_mode == "SNAP Bivariate Classification":

    legend_map1 = """

    <div style="

    position: fixed;

    bottom: 40px; left: 40px;

    width: 300px;

    background-color: white;

    border: 2px solid grey;

    z-index: 9999;

    font-size: 14px;

    padding: 10px;

    ">

    <b>SNAP Bivariate Classification</b><br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#ea524a" stroke="#777" stroke-width="0.4"/></svg>

    Above SNAP Median, No Agency<br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#6ecffa" stroke="#777" stroke-width="0.4"/></svg>

    Below SNAP Median, No Agency<br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#7dba53" stroke="#777" stroke-width="0.4"/></svg>

    Below SNAP Median, Agency<br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#f9dd5f" stroke="#777" stroke-width="0.4"/></svg>

    Above SNAP Median, Agency

    </div>

    """

else:

    legend_map1 = """

    <div style="

    position: fixed;

    bottom: 40px; left: 40px;

    width: 210px;

    background-color: white;

    border: 2px solid grey;

    z-index: 9999;

    font-size: 14px;

    padding: 10px;

    ">

    <b>LI/LA Classification</b><br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#e5513f" stroke="#777" stroke-width="0.4"/></svg>

    LI/LA<br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#defd93" stroke="#777" stroke-width="0.4"/></svg>

    Not LI/LA<br>



    <svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#e0e0e0" stroke="#777" stroke-width="0.4"/></svg>

    Not In Data

    </div>

    """



m.get_root().html.add_child(folium.Element(legend_map1))



# Agency markers

for _,row in agency_gdf.iterrows():



    folium.CircleMarker(

        location=[row["lat"],row["long"]],

        radius=1.5,

        color="black",

        weight=0.5,

        fill=True,

        fill_color="#1f77b4",

        fill_opacity=0.9,

        tooltip=row["Agency Short Name"]

    ).add_to(m)



st_folium(m, height=750, use_container_width=True, returned_objects=[])





# ==========================================================

# VISIT CHANGE MAP

# ==========================================================



st.subheader("Visit Change Map")



gdf["change_color"] = gdf["Average Increase in Visit"].map(change_colors)



m2 = folium.Map(tiles="OpenStreetMap")

m2.fit_bounds(service_area_bounds, padding=(20, 20))



def style_change(feature):

    return {

        "fillColor": feature["properties"]["change_color"],

        "color": "black",

        "weight": 0.3,

        "fillOpacity": 0.7

    }



folium.GeoJson(

    gdf,

    style_function=style_change,

    tooltip=folium.GeoJsonTooltip(

        fields=[

            "County",

            "tractid",

            "Agency Count",

            "Average Increase in Visit",

            "Need Level 2023"

        ],

        aliases=[

            "County:",

            "Tract:",

            "Agency Count:",

            "Visit Change:",

            "Need Level:"

        ],

        sticky=True

    )

).add_to(m2)



for _,row in agency_gdf.iterrows():



    folium.CircleMarker(

        location=[row["lat"],row["long"]],

        radius=1.5,

        color="black",

        weight=0.5,

        fill=True,

        fill_color="#1f77b4",

        fill_opacity=0.9,

        tooltip=row["Agency Short Name"]

    ).add_to(m2)

# ----------------------------------------------------------

# VISIT CHANGE LEGEND

# ----------------------------------------------------------



legend2 = """

<div style="

position: fixed; 

bottom: 40px; left: 40px; 

width: 220px;

background-color: white;

border:2px solid grey;

z-index:9999;

font-size:14px;

padding: 10px;

">



<b>Visit Change</b><br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#93c883" stroke="#777" stroke-width="0.4"/></svg>

Increase<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#e28980" stroke="#777" stroke-width="0.4"/></svg>

Decrease<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#d5d487" stroke="#777" stroke-width="0.4"/></svg>

No Change<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#e5acd0" stroke="#777" stroke-width="0.4"/></svg>

No Agency



</div>

"""



m2.get_root().html.add_child(folium.Element(legend2))



st_folium(m2, height=750, use_container_width=True, returned_objects=[])



# ==========================================================

# NEED LEVEL MAP

# ==========================================================



st.subheader("Food Access Need Map")



need_colors = {

    "Has Agency": "#7790b3",

    "Neighboring Agency": "#9ac2bf",

    "High Need": "#d77c7b",

    "Moderate Need": "#e8a663"

}



gdf["need_color"] = gdf["Need Level 2023"].map(need_colors)



m3 = folium.Map(tiles="OpenStreetMap")

m3.fit_bounds(service_area_bounds, padding=(20, 20))



# ----------------------------------------------------------

# STYLE FUNCTION

# ----------------------------------------------------------



def style_need(feature):



    return {

        "fillColor": feature["properties"]["need_color"],

        "color": "black",

        "weight": 0.3,

        "fillOpacity": 0.7

    }





# ----------------------------------------------------------

# HOVER TOOLTIP FOR TRACTS

# ----------------------------------------------------------



tooltip_fields = [

    "County",

    "tractid",

    "Agency Count",

    "SNAP Participant Count 2023",

    "Above SNAP Median 2023",

    "Need Level 2023"

]



tooltip_alias = [

    "County:",

    "Tract:",

    "Agency Count:",

    "SNAP Participants:",

    "SNAP Median:",

    "Need Level:"

]



folium.GeoJson(

    gdf,

    style_function=style_need,

    tooltip=folium.GeoJsonTooltip(

        fields=tooltip_fields,

        aliases=tooltip_alias,

        sticky=True,

        labels=True

    )

).add_to(m3)





# ----------------------------------------------------------

# AGENCY POINT OVERLAY

# ----------------------------------------------------------



for _, row in agency_gdf.iterrows():



    folium.CircleMarker(

        location=[row["lat"], row["long"]],

        radius=2,

        color="black",

        weight=0.5,

        fill=True,

        fill_color="#1f77b4",

        fill_opacity=0.9,

        tooltip=folium.Tooltip(

            f"""

            <b>Agency:</b> {row['Agency Short Name']}<br>

            <b>Lat:</b> {row['lat']}<br>

            <b>Lon:</b> {row['long']}

            """,

            sticky=True

        )

    ).add_to(m3)





# ----------------------------------------------------------

# LEGEND

# ----------------------------------------------------------



legend3 = """

<div style="

position: fixed; 

bottom: 40px; left: 40px; 

width: 230px;

background:white;

border:2px solid grey;

z-index:9999;

font-size:14px;

padding:10px;

">



<b>Food Access Need</b><br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#7790b3" stroke="#777" stroke-width="0.4"/></svg>

Has Agency<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#9ac2bf" stroke="#777" stroke-width="0.4"/></svg>

Neighboring Agency<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#d77c7b" stroke="#777" stroke-width="0.4"/></svg>

High Need<br>



<svg width="15" height="15" viewBox="0 0 15 15" style="vertical-align:-2px;margin-right:6px"><rect x="0" y="0" width="15" height="15" fill="#e8a663" stroke="#777" stroke-width="0.4"/></svg>

Moderate Need



</div>

"""



m3.get_root().html.add_child(folium.Element(legend3))



st_folium(m3, height=750, use_container_width=True, returned_objects=[])

# ==========================================================

# SNAP VS LI/LA ANALYSIS

# ==========================================================



st.subheader("SNAP vs LI/LA Analysis")



if map_mode == "SNAP Bivariate Classification":



    pivot_table = pd.crosstab(

        gdf["LI/LA"],

        gdf[formulation_col]

    )



    pivot_table["Total"] = pivot_table.sum(axis=1)



    total_row = pivot_table.sum(axis=0)

    total_row.name = "Total"



    pivot_table = pd.concat([pivot_table,total_row.to_frame().T])



    st.dataframe(pivot_table)



    # Prepare chart data

    plot_df = pivot_table.drop("Total").drop(columns="Total")



    chart_df = plot_df.T.reset_index()

    chart_df.columns = ["SNAP Category"] + list(chart_df.columns[1:])



    chart_df = chart_df.melt(

        id_vars="SNAP Category",

        var_name="LI/LA Status",

        value_name="Count"

    )



    st.subheader("Distribution of SNAP Categories by LI/LA Status")



    chart = alt.Chart(chart_df).mark_bar().encode(

    x=alt.X(

        "SNAP Category:N",

        sort=None,

        title="SNAP Classification",

        axis=alt.Axis(labelAngle=-20, labelLimit=400, labelFontSize=13, labelPadding=10)

    ),

    y=alt.Y("Count:Q", title="Number of Census Tracts"),

    color=alt.Color(

        "LI/LA Status:N",

        legend=alt.Legend(

            title="LI/LA Status",

            orient="bottom"

        )

    ),

        tooltip=["SNAP Category","LI/LA Status","Count"]

    ).properties(

        width=1000,

        height=350

    )



    st.altair_chart(chart, use_container_width=True)





# ==========================================================

# INCREASE IN VISIT ANALYSIS

# ==========================================================



st.subheader("Increase in Visit Analysis")



increase_df = gdf[gdf["Average Increase in Visit"] == "Increase"]



st.write("Number of tracts with increased visits:", len(increase_df))



# ----------------------------------------------------------

# CREATE PIVOT

# ----------------------------------------------------------



pivot_inc = pd.crosstab(

    increase_df["LI/LA"],

    increase_df[formulation_col]

)



# add totals

pivot_inc["Total"] = pivot_inc.sum(axis=1)



total_row = pivot_inc.sum(axis=0)

total_row.name = "Total"



pivot_inc = pd.concat([pivot_inc, total_row.to_frame().T])



# ----------------------------------------------------------

# TRANSPOSE FOR DISPLAY

# ----------------------------------------------------------



pivot_display = pivot_inc.T



st.write("Pivot Table (Increase in Visits Only)")

st.dataframe(pivot_display)



# ----------------------------------------------------------

# PREP DATA FOR ALTAIR

# ----------------------------------------------------------



plot_df = pivot_display.drop("Total").drop(columns="Total")



chart_df = plot_df.reset_index()



# rename first column safely

chart_df = chart_df.rename(columns={chart_df.columns[0]: "SNAP Category"})



chart_df = chart_df.melt(

    id_vars="SNAP Category",

    var_name="LI/LA Status",

    value_name="Count"

)



# ----------------------------------------------------------

# ALTAIR CHART

# ----------------------------------------------------------



chart2 = alt.Chart(chart_df).mark_bar().encode(

    x=alt.X(

        "SNAP Category:N",

        sort=None,

        title="SNAP Classification",

        axis=alt.Axis(labelAngle=-20, labelLimit=400, labelFontSize=13, labelPadding=10)

    ),

    y=alt.Y("Count:Q", title="Number of Census Tracts"),

    color=alt.Color(

        "LI/LA Status:N",

        legend=alt.Legend(
            title="LI/LA Status",
            orient="bottom"
        )
    ),
    tooltip=["SNAP Category","LI/LA Status","Count"]
).properties(
    width=1000,
    height=350
)
st.altair_chart(chart2, use_container_width=True)
