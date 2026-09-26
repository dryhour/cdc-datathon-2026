"""Interactive country map and side-by-side electricity access comparison."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from progress import compare_years, load_world_bank_data
from theme import apply_theme, BLUE, ORANGE, TEAL, MUTED, SURFACE, GRID


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def data():
    return load_world_bank_data()


def compact(value):
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.0f}K"
    return f"{value:,.0f}"


def status(row):
    if row["paradox"]:
        return "Hidden gap grew"
    if row["delta_unserved"] < 0:
        return "Gap shrank"
    return "Other change"


COLORS = {"Hidden gap grew": ORANGE, "Gap shrank": TEAL, "Other change": MUTED}


def render_map():
    """Render the map and country comparison inside any Streamlit page."""
    apply_theme()
    st.title("Explore the map 🌍")
    st.write("**Click a country marker to place it in A or B**, then compare the two stories. Marker size shows the number of people without electricity at the end of the period.")
    st.caption("World Bank Indicators API · Electricity access (EG.ELC.ACCS.ZS) and population (SP.POP.TOTL)")

    try:
        with st.spinner("Loading World Bank country and indicator data…"):
            rows, updates = data()
    except Exception as exc:
        st.error(f"Could not retrieve World Bank data: {exc}")
        st.stop()

    years = sorted({row["year"] for row in rows})
    with st.sidebar:
        st.header("Time period")
        start = st.selectbox("Start year", years[:-1], index=max(0, len(years) - 6))
        ends = [year for year in years if year > start]
        end = st.selectbox("End year", ends, index=len(ends) - 1)
        st.caption("Only countries with both indicators in both years are compared. Map markers require World Bank coordinates.")

    compared = compare_years(rows, start, end)
    if len(compared) < 2:
        st.warning("Fewer than two countries have comparable data for this period. Select another period.")
        st.stop()

    by_code = {row["code"]: row for row in compared}
    options = sorted(by_code, key=lambda code: by_code[code]["country"])
    flags = [row for row in compared if row["paradox"]]
    defaults = [row["code"] for row in flags[:2]]
    defaults += [code for code in options if code not in defaults][:2 - len(defaults)]
    for slot, default in zip(("A", "B"), defaults):
        if st.session_state.get(f"country_{slot}") not in by_code:
            st.session_state[f"country_{slot}"] = default

    st.markdown(f"**{len(flags)}** countries show the paradox from **{start} to {end}**. "
                "Orange = access percentage rose while the estimated number without electricity rose. "
                "Teal = the estimated gap shrank.")

    slot = st.radio("Send the next map click to", ["A", "B"], horizontal=True)
    mapped = sorted(
        [row for row in compared if row["latitude"] is not None and row["longitude"] is not None],
        key=lambda row: row["country"],
    )
    if mapped:
        fig = go.Figure(go.Scattergeo(
            lat=[row["latitude"] for row in mapped],
            lon=[row["longitude"] for row in mapped],
            text=[row["country"] for row in mapped],
            customdata=[[row["code"], row["delta_rate"], row["delta_unserved"] / 1_000_000,
                         row["end_unserved"] / 1_000_000] for row in mapped],
            marker=dict(
                size=[max(7, min(37, 7 + (row["end_unserved"] / 1_000_000) ** .5 * 2.2)) for row in mapped],
                color=[COLORS[status(row)] for row in mapped], opacity=.83,
                line=dict(color="#071424", width=1),
            ),
            mode="markers",
            hovertemplate=("<b>%{text}</b><br>Access change: %{customdata[1]:+.1f} points"
                           "<br>Unserved change: %{customdata[2]:+.2f}M"
                           "<br>Unserved at end: %{customdata[3]:.2f}M<extra></extra>"),
        ))
        fig.update_layout(
            height=530, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="#101d31", font_color="#edf3fb",
            clickmode="event+select", dragmode="select",
            geo=dict(projection_type="natural earth", showland=True, landcolor="#203550",
                     showocean=True, oceancolor="#101d31", showlakes=False,
                     showcountries=True, countrycolor="#47617b", bgcolor="#101d31"),
        )
        event = st.plotly_chart(fig, key="country_map", on_select="rerun",
                                selection_mode="points", width="stretch")
        selected = event.selection.points if event else []
        indices = tuple(point["point_index"] for point in selected if "point_index" in point)
        if indices and indices != st.session_state.get("last_map_selection"):
            chosen_index = indices[-1]
            if 0 <= chosen_index < len(mapped):
                st.session_state[f"country_{slot}"] = mapped[chosen_index]["code"]
        st.session_state["last_map_selection"] = indices
    else:
        st.warning("The World Bank did not provide map coordinates for this period. Use the selectors below.")

    st.caption(f"Map shows {len(mapped)} of {len(compared)} comparable countries with coordinates. "
               "A map marker is a country point, not the geographic extent of people without access.")

    def country_label(code):
        return by_code[code]["country"]


    col_a, col_b = st.columns(2)
    with col_a:
        a = st.selectbox("Country A", options, format_func=country_label, key="country_A")
    with col_b:
        b = st.selectbox("Country B", options, format_func=country_label, key="country_B")

    if a == b:
        st.info("Choose two different countries to compare their trajectories.")
        st.stop()

    shared_unserved_max = max(
        row["unserved"] for row in rows
        if row["code"] in (a, b) and start <= row["year"] <= end
    ) / 1_000_000 * 1.1

    def country_panel(code, label):
        row = by_code[code]
        st.subheader(f"{label} · {row['country']}")
        st.caption(status(row))
        x, y = st.columns(2)
        x.metric("Access rate", f"{row['end_rate']:.1f}%", f"{row['delta_rate']:+.1f} points")
        gap_change = row["delta_unserved"]
        y.metric("People without access", compact(row["end_unserved"]),
                 f"{'+' if gap_change > 0 else ''}{compact(gap_change)} since {start}", delta_color="inverse")
        history = pd.DataFrame([r for r in rows if r["code"] == code and start <= r["year"] <= end])
        history = history.set_index("year").reindex(range(start, end + 1)).rename_axis("year").reset_index()
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=history["year"], y=history["access_rate"], name="Access rate (%)",
                                    mode="lines+markers", connectgaps=False,
                                    line=dict(color=BLUE, width=3)))
        figure.add_trace(go.Scatter(x=history["year"], y=history["unserved"] / 1_000_000,
                                    name="Without access (millions)", mode="lines+markers",
                                    connectgaps=False, line=dict(color=ORANGE, width=3), yaxis="y2"))
        figure.update_layout(height=330, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                             font_color="#edf3fb", margin=dict(l=30, r=40, t=35, b=35),
                             xaxis=dict(dtick=1, gridcolor=GRID),
                             yaxis=dict(title="Access (%)", gridcolor=GRID, range=[0, 100]),
                             yaxis2=dict(title="People (M)", overlaying="y", side="right",
                                         range=[0, shared_unserved_max]),
                             legend=dict(orientation="h", y=1.15))
        st.plotly_chart(figure, width="stretch")
        if row["paradox"]:
            threshold = 100 * (1 - row["start_unserved"] / row["end_population"])
            st.warning(f"To hold the {start} gap steady at {end}'s population, access would have "
                       f"needed to reach **{threshold:.1f}%**, versus the reported **{row['end_rate']:.1f}%**.")
        else:
            st.success("This country does not meet the paradox rule for this period.")
        with st.expander("See endpoint calculation"):
            st.write(f"{start}: {row['start_population']:,.0f} × (1 − {row['start_rate']:.2f}/100) "
                     f"= {row['start_unserved']:,.0f} estimated people without access")
            st.write(f"{end}: {row['end_population']:,.0f} × (1 − {row['end_rate']:.2f}/100) "
                     f"= {row['end_unserved']:,.0f} estimated people without access")


    with col_a:
        country_panel(a, "A")
    with col_b:
        country_panel(b, "B")

    st.caption("Source: World Bank Indicators API. Estimates inherit uncertainty and revisions in reported rates and population. "
               f"Access API updated {updates['access'] or 'date unspecified'}; population API updated "
               f"{updates['population'] or 'date unspecified'}. The comparison is descriptive, not a causal claim.")
