"""Run with: streamlit run josh/dashboard.py"""

import pandas as pd
import plotly.express as px
import streamlit as st

from progress import compare_years, load_world_bank_data

st.set_page_config(page_title="The Progress Paradox", page_icon="⚡", layout="wide")


def compact(number):
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:,.1f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:,.0f}K"
    return f"{number:,.0f}"


st.title("The Progress Paradox ⚡")
st.subheader("When electricity access rises, are fewer people actually left behind?")
st.caption("Live World Bank Indicators API data · Rates and population joined by country and year")


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
st.markdown(
    f"From **{start} to {end}**, the access rate rose while the number without "
    f"electricity also rose in **{len(paradoxes)} countries**."
)

c1, c2, c3 = st.columns(3)
c1.metric("Paradox countries", len(paradoxes))
c2.metric("Additional people left without access*", compact(sum(r["delta_unserved"] for r in paradoxes)))
c3.metric("Countries with both years", len(compared))
st.caption("*Sum of estimated increases across flagged countries, rounded. This is a change in the access gap, not a count of new connections needed for universal access.")

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
        title="Both measures rose—but they tell different stories",
        size_max=42,
    )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Access gain: %{x:.1f} points<br>Gap grew: %{y:.2f}M<extra></extra>")
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

st.header("Investigate a country")
country_options = sorted(compared, key=lambda r: r["country"])
default_code = paradoxes[0]["code"] if paradoxes else country_options[0]["code"]
selected_code = st.selectbox(
    "Country", [r["code"] for r in country_options],
    index=[r["code"] for r in country_options].index(default_code),
    format_func=lambda code: next(r["country"] for r in country_options if r["code"] == code),
)
chosen = next(r for r in country_options if r["code"] == selected_code)
history = pd.DataFrame([r for r in rows if r["code"] == selected_code and start <= r["year"] <= end]).sort_values("year")
# Reindex so missing observations break the line rather than imply measured values.
history = history.set_index("year").reindex(range(start, end + 1)).rename_axis("year").reset_index()
left, right = st.columns(2)
with left:
    st.plotly_chart(px.line(history, x="year", y="access_rate", markers=True,
                            labels={"year": "Year", "access_rate": "Access rate (%)"},
                            title="Share of people with electricity"), width="stretch")
with right:
    history["unserved_millions"] = history["unserved"] / 1_000_000
    st.plotly_chart(px.line(history, x="year", y="unserved_millions", markers=True,
                            labels={"year": "Year", "unserved_millions": "People (millions)"},
                            title="People still without electricity"), width="stretch")

if chosen["paradox"]:
    st.warning(
        f"**The paradox:** {chosen['country']}'s access rate rose by "
        f"{chosen['delta_rate']:.1f} percentage points, yet the estimated number "
        f"without electricity grew by {compact(chosen['delta_unserved'])} people "
        f"between {start} and {end}. At least that many additional people would have "
        "needed access over this period to keep the gap from growing."
    )
    st.write(
        f"**Why the count grew:** population changed by {compact(chosen['population_change'])}, "
        f"while the estimated number of people with access changed by "
        f"{compact(chosen['served_change'])}. The difference is "
        f"{compact(chosen['delta_unserved'])} more people left without access."
    )
else:
    st.info("This country does not meet the paradox rule for these years. The charts still show its trajectory.")

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
