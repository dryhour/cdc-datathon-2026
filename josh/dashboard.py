"""Run with: streamlit run josh/dashboard.py"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from progress import compare_years, load_world_bank_data
from theme import apply_theme, BLUE, ORANGE, SURFACE, GRID

st.set_page_config(page_title="The Progress Paradox", page_icon="⚡", layout="wide")
apply_theme()


def compact(number):
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:,.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:,.0f}K"
    return f"{number:,.0f}"


st.markdown('<span class="eyebrow">WORLD BANK DATA · ELECTRICITY ACCESS</span>', unsafe_allow_html=True)
st.title("The Progress Paradox")
st.caption("An early warning when a better percentage hides a growing number of people without electricity")
st.page_link("pages/1_Explore_the_map.py", label="Explore the interactive map and compare two countries →", icon="🌍")


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def data():
    return load_world_bank_data()


try:
    with st.spinner("Fetching electricity access and population from the World Bank…"):
        rows, updates = data()
except Exception as exc:
    st.error(f"Could not load World Bank data: {exc}")
    st.stop()

years = sorted({r["year"] for r in rows})
if len(years) < 2:
    st.error("The API did not return two comparable years.")
    st.stop()

with st.sidebar:
    st.header("Compare years")
    start = st.selectbox("Start year", years[:-1], index=max(0, len(years) - 6))
    end_options = [year for year in years if year > start]
    end = st.selectbox("End year", end_options, index=len(end_options) - 1)
    st.markdown("**What counts as a paradox?**")
    st.write("Electricity access percentage rises **and** the estimated number without electricity rises over the same period.")
    st.caption("Choose the same year range for every country. Missing country-years are excluded.")

compared = compare_years(rows, start, end)
paradoxes = [r for r in compared if r["paradox"]]
if not compared:
    st.warning("No countries have both indicators in these endpoint years. Choose another period.")
    st.stop()

country_options = sorted(compared, key=lambda r: r["country"])
default_code = paradoxes[0]["code"] if paradoxes else country_options[0]["code"]
selected_code = st.selectbox(
    "Explore a country", [r["code"] for r in country_options],
    index=[r["code"] for r in country_options].index(default_code),
    format_func=lambda code: next(r["country"] for r in country_options if r["code"] == code),
)
chosen = next(r for r in country_options if r["code"] == selected_code)

if chosen["paradox"]:
    headline = (f"Access rose. <span class='accent'>{compact(chosen['delta_unserved'])} more people</span> "
                "were left without electricity.")
    intro = (f"{escape(chosen['country'])} · {start}–{end}. A rising access rate concealed a growing "
             "estimated gap. Explore the evidence below.")
else:
    headline = f"What happened in {escape(chosen['country'])}?"
    intro = (f"Compare the access rate with the estimated number left without electricity "
             f"from {start} to {end}. This country does not meet the paradox rule in this period.")
st.markdown(f'<div class="hero"><span class="eyebrow">THE REVEAL</span><h1>{headline}</h1>'
            f'<p>{intro}</p></div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Paradox countries", len(paradoxes))
c2.metric("Additional people left without access*", compact(sum(r["delta_unserved"] for r in paradoxes)))
c3.metric("Countries with both years", len(compared))
st.caption("*Sum of estimated increases across flagged countries, rounded. This is a change in the access gap, not a count of new connections needed for universal access.")

st.header(f"The evidence · {chosen['country']}")
history = pd.DataFrame([r for r in rows if r["code"] == selected_code and start <= r["year"] <= end]).sort_values("year")
# Reindex so missing observations break the line rather than imply measured values.
history = history.set_index("year").reindex(range(start, end + 1)).rename_axis("year").reset_index()

def trend_chart(frame, column, title, color, suffix="", divisor=1):
    fig = go.Figure(go.Scatter(x=frame["year"], y=frame[column] / divisor,
                               mode="lines+markers", connectgaps=False,
                               line=dict(color=color, width=4), marker=dict(size=8),
                               hovertemplate=f"%{{x}}: %{{y:,.2f}}{suffix}<extra></extra>"))
    fig.update_layout(title=title, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                      font_color="#e9f0f8", height=315, margin=dict(l=30,r=25,t=62,b=35),
                      xaxis=dict(dtick=1, gridcolor=GRID),
                      yaxis=dict(gridcolor=GRID, ticksuffix=suffix), showlegend=False)
    return fig

left, right = st.columns(2)
with left:
    st.plotly_chart(trend_chart(history, "access_rate", "Access rate · higher is better", BLUE, "%"), width="stretch")
with right:
    st.plotly_chart(trend_chart(history, "unserved", "People without access · lower is better", ORANGE, "M", 1_000_000), width="stretch")

if chosen["paradox"]:
    target_rate = 100 * (1 - chosen["start_unserved"] / chosen["end_population"])
    st.warning(
        f"**The hidden gap:** Access improved from {chosen['start_rate']:.1f}% to "
        f"{chosen['end_rate']:.1f}%, but the estimated unserved count rose from "
        f"{compact(chosen['start_unserved'])} to {compact(chosen['end_unserved'])}."
    )
    st.info(
        f"**A useful threshold:** With {end}'s population, access would have needed to reach "
        f"**{target_rate:.1f}%** (about **{target_rate - chosen['end_rate']:.1f} percentage points** "
        f"above the reported rate) just to keep the unserved count at its {start} level. "
        f"That equals roughly **{compact(chosen['delta_unserved'])} additional people** with access "
        "at the endpoint. This is a retrospective benchmark, not a forecast or project cost."
    )
else:
    st.info("This country does not meet the paradox rule for these years. The charts show its trajectory.")

st.header("Where is the hidden gap growing?")
if not paradoxes:
    st.info("No paradox cases in this period. Try another start year.")
else:
    flagged = pd.DataFrame(paradoxes)
    flagged["gap_millions"] = flagged["delta_unserved"] / 1_000_000
    fig = px.scatter(
        flagged, x="delta_rate", y="gap_millions", size="end_unserved",
        hover_name="country", custom_data=["start_rate", "end_rate", "code"],
        labels={"delta_rate": "Increase in access rate (percentage points)",
                "gap_millions": "Increase in people without electricity (millions)"},
        title="Prioritize by the growth in people without access",
        size_max=42,
        color_discrete_sequence=[ORANGE],
    )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Access gain: %{x:.1f} points<br>Gap grew: %{y:.2f}M<extra></extra>")
    fig.update_layout(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font_color="#e9f0f8",
                      xaxis_gridcolor=GRID, yaxis_gridcolor=GRID)
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Priority view: largest increase in people without electricity**")
    st.dataframe(
        flagged[["country", "start_rate", "end_rate", "delta_rate", "start_unserved", "end_unserved", "delta_unserved"]]
        .rename(columns={"country": "Country", "start_rate": f"Access {start} (%)",
                         "end_rate": f"Access {end} (%)", "delta_rate": "Gain (points)",
                         "start_unserved": f"Without access {start}",
                         "end_unserved": f"Without access {end}",
                         "delta_unserved": "Gap grew by"})
        .style.format({f"Access {start} (%)": "{:.1f}", f"Access {end} (%)": "{:.1f}",
                       "Gain (points)": "+{:.1f}", f"Without access {start}": "{:,.0f}",
                       f"Without access {end}": "{:,.0f}", "Gap grew by": "+{:,.0f}"}),
        width="stretch", hide_index=True,
    )
    export = flagged[["code", "country", "start_rate", "end_rate", "delta_rate",
                      "start_unserved", "end_unserved", "delta_unserved",
                      "population_change", "served_change"]]
    st.download_button(
        "Download priority list (CSV)", export.to_csv(index=False).encode("utf-8"),
        file_name=f"electricity_progress_paradox_{start}_{end}.csv",
        mime="text/csv",
    )

with st.expander(f"See {chosen['country']} year-by-year data"):
    detail = history[["year", "access_rate", "population", "unserved"]].dropna()
    st.dataframe(detail.rename(columns={"year": "Year", "access_rate": "Access (%)",
                                        "population": "Population", "unserved": "Without access (estimated)"})
                 .style.format({"Access (%)": "{:.2f}", "Population": "{:,.0f}",
                                "Without access (estimated)": "{:,.0f}"}),
                 hide_index=True, width="stretch")

with st.expander("Method, limitations, and sources"):
    st.markdown(
        "**Formula:** estimated people without electricity = population × "
        "(1 − access percentage / 100). A country is flagged only if the access "
        "percentage and estimated unserved count both increase between the "
        "selected years. We join indicators on identical country and year, exclude "
        "regional aggregates and null observations, and compare the same endpoint "
        "years for all countries. Intermediate missing years appear as gaps in a "
        "country's line chart. Counts are estimates derived from reported rates, "
        "not household-level measurements. Changes may reflect population growth "
        "or revisions to indicator estimates; this analysis does not identify causes "
        "or recommend a specific intervention."
    )
    st.markdown(
        "**World Bank Indicators API:** "
        "[Electricity access (EG.ELC.ACCS.ZS)](https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS) · "
        "[Population (SP.POP.TOTL)](https://data.worldbank.org/indicator/SP.POP.TOTL) · "
        "[API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)"
    )
    st.caption(f"API last updated: access {updates['access'] or 'not specified'}; population {updates['population'] or 'not specified'}. Data refreshes daily in this app.")
