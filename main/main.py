"""Run from the repo root: streamlit run main/main.py"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from statsmodels.stats.diagnostic import acorr_ljungbox

from progress import YEARS, compare_years, load_world_bank_data
from trend_tests import MIN_TEST_YEARS, co_movement, comparison_rows, lag1_pacf, render_co_movement, stationarity
from theme import apply_theme, BLUE, ORANGE, TEAL, MUTED, SURFACE, GRID

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


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def data(years=YEARS):
    # Passing the range makes the cache refetch whenever YEARS changes.
    return load_world_bank_data(years)


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

window_rows = pd.DataFrame([r for r in rows if start <= r["year"] <= end])
per_country = window_rows.groupby("code").agg(years=("year", "count"), access_values=("access_rate", "nunique"),
                                              gap_values=("unserved", "nunique"))
# Countries with a gap to study: people without access at the start and both series changing.
has_gap = {r["code"] for r in compared if r["start_unserved"] > 0}
relevant = per_country[(per_country["access_values"] >= 3) & (per_country["gap_values"] >= 3)
                       & per_country.index.isin(has_gap)]
testable = set(relevant[relevant["years"] >= MIN_TEST_YEARS].index)
if testable:
    keep = testable
    option_note = (f"The map shows {len(keep)} of {len(compared)} countries: those with at least {MIN_TEST_YEARS} "
                   f"years of data and a changing access gap in {start}–{end}.")
elif len(relevant):
    keep = set(relevant.index)
    option_note = (f"The map shows {len(keep)} countries with a changing access gap. Choose a period of at least "
                   f"{MIN_TEST_YEARS} years to run the correlation tests.")
else:
    keep = {r["code"] for r in compared}
    option_note = "No country has a changing access gap in this period, so all countries are shown."

country_options = sorted((r for r in compared if r["code"] in keep), key=lambda r: r["country"])
eligible_paradoxes = [r for r in paradoxes if r["code"] in keep]
default_code = eligible_paradoxes[0]["code"] if eligible_paradoxes else country_options[0]["code"]
STATUS_COLORS = {"Hidden gap grew": ORANGE, "Gap shrank": TEAL, "Other change": MUTED}


def status(row):
    if row["paradox"]:
        return "Hidden gap grew"
    return "Gap shrank" if row["delta_unserved"] < 0 else "Other change"


# The map is the country picker for two slots; keep each choice while it stays available for the period.
available = [r["code"] for r in country_options]
if st.session_state.get("selected_code") not in available:
    st.session_state["selected_code"] = default_code
if st.session_state.get("compare_code") not in available:
    others = [r["code"] for r in eligible_paradoxes] + available
    st.session_state["compare_code"] = next((c for c in others if c != st.session_state["selected_code"]),
                                            st.session_state["selected_code"])
RING = {"selected_code": "#ffffff", "compare_code": BLUE}


def ring(code, part):
    for slot, color in RING.items():
        if code == st.session_state[slot]:
            return color if part == "color" else 3
    return "#071424" if part == "color" else 1


mapped = [r for r in country_options if r["latitude"] is not None and r["longitude"] is not None]
st.subheader("Click a country on the map")
slot_label = st.radio("A map click sets the", ["Main country", "Comparison country"], horizontal=True,
                      key="map_slot")
slot = "selected_code" if slot_label == "Main country" else "compare_code"
st.caption("Orange = access rose but the number without electricity also rose (the paradox) · "
           "Teal = the gap shrank · Gray = other change. Marker size shows people without electricity "
           f"in {end}. White ring = main country · blue ring = comparison country.")
map_fig = go.Figure(go.Scattergeo(
    lat=[r["latitude"] for r in mapped], lon=[r["longitude"] for r in mapped],
    text=[r["country"] for r in mapped],
    customdata=[[r["delta_rate"], r["delta_unserved"] / 1_000_000, r["end_unserved"] / 1_000_000] for r in mapped],
    marker=dict(size=[max(7, min(37, 7 + (r["end_unserved"] / 1_000_000) ** .5 * 2.2)) for r in mapped],
                color=[STATUS_COLORS[status(r)] for r in mapped], opacity=.85,
                line=dict(color=[ring(r["code"], "color") for r in mapped],
                          width=[ring(r["code"], "width") for r in mapped])),
    mode="markers",
    hovertemplate=("<b>%{text}</b><br>Access change: %{customdata[0]:+.1f} points"
                   "<br>Change in people without access: %{customdata[1]:+.2f}M"
                   "<br>Without access at end: %{customdata[2]:.2f}M<extra></extra>"),
))
map_fig.update_layout(
    height=480, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="#101d31", font_color="#edf3fb",
    clickmode="event+select", dragmode=False,
    geo=dict(projection_type="natural earth", showland=True, landcolor="#203550", showocean=True,
             oceancolor="#101d31", showlakes=False, showcountries=True, countrycolor="#47617b",
             bgcolor="#101d31"),
)
# Keying by period resets the click state when the years (and so the marker list) change.
event = st.plotly_chart(map_fig, key=f"country_map_{start}_{end}", on_select="rerun",
                        selection_mode="points", width="stretch")
points = event.selection.points if event else []
indices = [p["point_index"] for p in points if "point_index" in p]
clicked = mapped[indices[-1]]["code"] if indices and 0 <= indices[-1] < len(mapped) else None
if clicked and clicked != st.session_state.get(f"last_click_{start}_{end}"):
    # Only a new click fills a slot, so flipping the toggle doesn't move the old click into the other slot.
    st.session_state[f"last_click_{start}_{end}"] = clicked
    st.session_state[slot] = clicked
    st.rerun()  # redraw so the rings move to the new countries
selected_code = st.session_state["selected_code"]
chosen = next(r for r in country_options if r["code"] == selected_code)
compare = next(r for r in country_options if r["code"] == st.session_state["compare_code"])
st.caption(f"Main: **{chosen['country']}** · Comparison: **{compare['country']}**. {option_note}")

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

def percent_change(column):
    """Percent change from the start year, so both series share one unit."""
    base = history.loc[history["year"] == start, column].iloc[0]
    return (history[column] / base - 1) * 100 if base else None


def trend_chart(change, levels, title, color, level_format, y_range):
    fig = go.Figure(go.Scatter(x=history["year"], y=change, customdata=levels,
                               mode="lines+markers", connectgaps=False,
                               line=dict(color=color, width=4), marker=dict(size=8),
                               hovertemplate=f"%{{x}}: %{{y:+.1f}}% ({level_format})<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=GRID, width=2))
    fig.update_layout(title=title, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                      font_color="#e9f0f8", height=315, margin=dict(l=30,r=25,t=62,b=35),
                      xaxis=dict(dtick=1, gridcolor=GRID),
                      yaxis=dict(gridcolor=GRID, ticksuffix="%", range=y_range), showlegend=False)
    return fig


access_change, unserved_change = percent_change("access_rate"), percent_change("unserved")
st.caption(f"Both charts show the percent change from {start} on the same scale. Hover for the reported values.")
changes = [c for c in (access_change, unserved_change) if c is not None]
low = min(0, *(c.min() for c in changes))
high = max(0, *(c.max() for c in changes))
pad = max(high - low, 1) * 0.1
y_range = [low - pad, high + pad]

left, right = st.columns(2)
with left:
    st.plotly_chart(trend_chart(access_change, history["access_rate"],
                                f"Access rate · % change since {start}", BLUE, "%{customdata:.1f}% access", y_range),
                    width="stretch")
with right:
    if unserved_change is None:
        st.info(f"No one was estimated to be without electricity in {start}, so a percent change is undefined.")
    else:
        st.plotly_chart(trend_chart(unserved_change, history["unserved"] / 1_000_000,
                                    f"People without access · % change since {start}", ORANGE,
                                    "%{customdata:,.2f}M people", y_range),
                        width="stretch")


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


st.subheader("Do the two trends move together?")
render_co_movement(history, start, end, chosen["country"])


def period_history(code):
    frame = pd.DataFrame([r for r in rows if r["code"] == code and start <= r["year"] <= end]).sort_values("year")
    return frame.set_index("year").reindex(range(start, end + 1)).rename_axis("year").reset_index()


def change_since_start(frame, column):
    base = frame.loc[frame["year"] == start, column].iloc[0]
    return (frame[column] / base - 1) * 100 if base else None


st.header(f"Compare two countries · {chosen['country']} vs {compare['country']}")
if compare["code"] == chosen["code"]:
    st.info("Pick a different comparison country: set the toggle above the map to **Comparison country**, "
            "then click a country.")
else:
    st.caption("To change the comparison, set the toggle above the map to **Comparison country** and click a "
               "country. Both charts show the percent change from the start year on the same scale.")
    pair = [(chosen, period_history(chosen["code"])), (compare, period_history(compare["code"]))]
    pair_changes = [(change_since_start(h, "access_rate"), change_since_start(h, "unserved")) for _, h in pair]
    series = [v for changes in pair_changes for v in changes if v is not None]
    low, high = min(0, *(v.min() for v in series)), max(0, *(v.max() for v in series))
    pad = max(high - low, 1) * 0.1
    for column, (row, frame), (access_pct, unserved_pct), label in zip(
            st.columns(2), pair, pair_changes, ("Main", "Comparison")):
        with column:
            st.subheader(f"{label} · {row['country']}")
            fig = go.Figure(go.Scatter(x=frame["year"], y=access_pct, customdata=frame["access_rate"],
                                       name="Access rate", mode="lines+markers", connectgaps=False,
                                       line=dict(color=BLUE, width=3),
                                       hovertemplate="%{x}: %{y:+.1f}% (%{customdata:.1f}% access)<extra></extra>"))
            if unserved_pct is not None:
                fig.add_trace(go.Scatter(x=frame["year"], y=unserved_pct, customdata=frame["unserved"] / 1_000_000,
                                         name="People without access", mode="lines+markers", connectgaps=False,
                                         line=dict(color=ORANGE, width=3),
                                         hovertemplate="%{x}: %{y:+.1f}% (%{customdata:,.2f}M people)<extra></extra>"))
            fig.add_hline(y=0, line=dict(color=GRID, width=2))
            fig.update_layout(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font_color="#e9f0f8", height=320,
                              margin=dict(l=30, r=20, t=40, b=35), xaxis=dict(dtick=1, gridcolor=GRID),
                              yaxis=dict(title=f"% change since {start}", ticksuffix="%", gridcolor=GRID,
                                         range=[low - pad, high + pad]),
                              legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, key=f"compare_chart_{label}", width="stretch")

    def summary(row, frame):
        return {
            "Paradox (access up, gap up)": "Yes" if row["paradox"] else "No",
            f"Access rate {start} → {end}": f"{row['start_rate']:.1f}% → {row['end_rate']:.1f}%",
            "People without access, change": f"{'+' if row['delta_unserved'] > 0 else ''}{compact(row['delta_unserved'])}",
            "Added by population growth": f"{'+' if row['population_effect'] > 0 else ''}{compact(row['population_effect'])}",
            "Gained electricity (access gains)": compact(-row["access_effect"]),
            **comparison_rows(co_movement(frame, start, end)),
        }

    table = pd.DataFrame({row["country"]: summary(row, frame) for row, frame in pair})
    st.dataframe(table.rename_axis("Measure").reset_index(), width="stretch", hide_index=True)
    st.caption("Tests use each country's own years in the selected period; see the evidence section above "
               "for the full statistical details of the main country.")


st.header("Where is the hidden gap growing?")
if not paradoxes:
    st.info("No paradox cases in this period. Try another start year.")
else:
    flagged = pd.DataFrame(paradoxes)  # already sorted by gap growth, largest first
    top = flagged.head(15)
    st.markdown(
        "**How to read this chart:** each row is a country where the access rate went up but more people "
        "ended up without electricity.\n"
        "- **Blue (left):** people who **gained electricity** because the access rate improved.\n"
        "- **Orange (right):** **new people without electricity**, from population growth outpacing new connections.\n"
        "- **◆ Overall change:** orange minus blue, the actual change in people without electricity. "
        "Right of zero means the gap grew."
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top["country"], x=top["access_effect"] / 1_000_000, orientation="h", name="Gained electricity",
        marker_color=BLUE, customdata=-top["access_effect"] / 1_000_000,
        hovertemplate="<b>%{y}</b><br>%{customdata:.2f}M people gained electricity<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=top["country"], x=top["population_effect"] / 1_000_000, orientation="h", name="New people without electricity",
        marker_color=ORANGE, hovertemplate="<b>%{y}</b><br>%{x:+.2f}M new people without electricity (population growth)<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        y=top["country"], x=top["delta_unserved"] / 1_000_000, mode="markers", name="Overall change", legendgroup="net",
        marker=dict(symbol="diamond", size=11, color="#e9f0f8", line=dict(color=SURFACE, width=2)),
        hovertemplate="<b>%{y}</b><br>Overall change in people without electricity: %{x:+.2f}M<extra></extra>",
    ))
    # Net labels sit just past the end of the orange bar so they never overlap a fill.
    fig.add_trace(go.Scatter(
        y=top["country"], x=top["population_effect"] / 1_000_000, mode="text", showlegend=False, legendgroup="net",
        text=[f"  overall +{compact(v)}" for v in top["delta_unserved"]], textposition="middle right",
        textfont=dict(color="#e9f0f8"), hoverinfo="skip",
    ))
    fig.update_layout(
        title=dict(text="Population growth outpaced access gains", x=0, xanchor="left", y=0.98, yanchor="top"),
        barmode="relative", bargap=0.35, barcornerradius=4,
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font_color="#e9f0f8",
        height=max(320, 42 * len(top) + 170), margin=dict(l=10, r=30, t=110, b=45),
        xaxis=dict(title="Change in people without electricity (millions)", gridcolor=GRID,
                   zeroline=True, zerolinecolor="#93a3ba", zerolinewidth=2,
                   range=[top["access_effect"].min() / 1_000_000 * 1.1,
                          top["population_effect"].max() / 1_000_000 * 1.25]),
        yaxis=dict(autorange="reversed", categoryorder="array", categoryarray=list(top["country"]),
                   automargin=True, ticksuffix="  "),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom"),
    )
    st.plotly_chart(fig, width="stretch")
    if len(flagged) > len(top):
        st.caption(f"Showing the {len(top)} largest of {len(flagged)} paradox countries; all are in the table below.")

    with st.expander(f"See the numbers for all {len(flagged)} paradox countries"):
        st.dataframe(
            flagged[["country", "start_rate", "end_rate", "start_unserved", "end_unserved",
                     "population_effect", "access_effect", "delta_unserved"]]
            .rename(columns={"country": "Country", "start_rate": f"Access {start} (%)",
                             "end_rate": f"Access {end} (%)",
                             "start_unserved": f"Without access {start}",
                             "end_unserved": f"Without access {end}",
                             "population_effect": "New people without electricity (population growth)",
                             "access_effect": "Gained electricity (access gains)",
                             "delta_unserved": "Overall change"})
            .style.format({f"Access {start} (%)": "{:.1f}", f"Access {end} (%)": "{:.1f}",
                           f"Without access {start}": "{:,.0f}", f"Without access {end}": "{:,.0f}",
                           "New people without electricity (population growth)": "+{:,.0f}",
                           "Gained electricity (access gains)": "{:,.0f}",
                           "Overall change": "+{:,.0f}"}),
            width="stretch", hide_index=True,
        )
    export = flagged[["code", "country", "start_rate", "end_rate", "delta_rate",
                      "start_unserved", "end_unserved", "delta_unserved",
                      "population_effect", "access_effect", "population_change", "served_change"]]
    st.download_button(
        "Download priority list (CSV)", export.to_csv(index=False).encode("utf-8"),
        file_name=f"electricity_progress_paradox_{start}_{end}.csv",
        mime="text/csv",
    )

    st.subheader("Is each country's gap a steady trend?")
    st.write("Time-series checks on each country's number of people without electricity, over the selected years. "
             "**Trend** uses ADF + KPSS on the yearly totals. **Persistence** uses PACF (lag 1) and Ljung-Box on "
             "the year-to-year changes: does one year's change in the gap carry over into the next?")

    def gap_checks(code):
        series = history_by_code.get(code)
        if series is None or len(series) < MIN_TEST_YEARS:
            return {"Years": 0 if series is None else len(series), "Trend (ADF + KPSS)": "Too few years"}
        state, adf_p, kpss_p = stationarity(series, 1 if len(series) < 12 else 2)
        changes = series.diff().dropna()
        lag1, band = lag1_pacf(changes)
        lb_p = acorr_ljungbox(changes, lags=[1])["lb_pvalue"].iloc[0]
        return {
            "Years": len(series), "Trend (ADF + KPSS)": state, "ADF p": adf_p, "KPSS p": kpss_p,
            "Persistence (PACF lag 1)": f"{lag1:+.2f} ({'significant' if abs(lag1) > band else 'not significant'}, "
                                        f"band ±{band:.2f})",
            "Autocorrelation (Ljung-Box)": f"{'Detected' if lb_p < 0.05 else 'None detected'} (p = {lb_p:.3f})",
        }

    history_by_code = {
        code: group.sort_values("year")["unserved"].reset_index(drop=True)
        for code, group in window_rows[window_rows["code"].isin(flagged["code"])].groupby("code")
    }
    checks = pd.DataFrame([{"Country": row["country"], **gap_checks(row["code"])} for _, row in flagged.iterrows()])
    st.dataframe(checks.style.format({"ADF p": "{:.3f}", "KPSS p": "{:.3f}"}, na_rep="–"),
                 width="stretch", hide_index=True)
    trend_counts = checks["Trend (ADF + KPSS)"].value_counts()
    st.caption(
        " · ".join(f"{label}: {count}" for label, count in trend_counts.items())
        + ". Significance level 0.05; PACF is significant when it falls outside ±1.96/√n. "
        + (f"With only {end - start + 1} years, these tests have low statistical power, so a longer period "
           "gives clearer results. " if end - start + 1 < 15 else "")
        + f"Countries need at least {MIN_TEST_YEARS} years of data in the period."
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
