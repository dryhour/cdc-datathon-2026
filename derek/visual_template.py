"""Derek's visual workbench. Run: python3 -m streamlit run derek/visual_template.py"""

from pathlib import Path
import sys

import plotly.graph_objects as go
import streamlit as st

# Keep the data logic in josh/progress.py; this file is safe to redesign freely.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "josh"))
from progress import compare_years, load_world_bank_data  # noqa: E402
from theme import apply_theme, chart_style, BLUE, ORANGE, GRID  # noqa: E402

st.set_page_config(page_title="Visual workbench · Progress Paradox", page_icon="🎨", layout="wide")
apply_theme()


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def data():
    return load_world_bank_data()


def millions(value):
    return f"{value / 1_000_000:,.1f}M"


st.caption("DEREK'S WORKBENCH · EDIT THIS PAGE TO TRY VISUAL IDEAS")
st.title("What does progress look like?")
st.write("This page uses the same live World Bank data as the main app. Change the typography, "
         "layout, chart style, or story here, then move successful ideas into the two demo pages.")

try:
    rows, updates = data()
except Exception as exc:
    st.error(f"Data unavailable: {exc}")
    st.stop()

# Shared starting example; switch countries to see how a design handles different magnitudes.
start, end = 2019, 2024
compared = compare_years(rows, start, end)
examples = [row for row in compared if row["paradox"]]
if not examples:
    st.info("No flagged countries have both endpoints in this example period.")
    st.stop()

names = {row["code"]: row["country"] for row in examples}
code = st.selectbox("Preview country", list(names), format_func=lambda value: names[value])
case = next(row for row in examples if row["code"] == code)
history = sorted((row for row in rows if row["code"] == code and start <= row["year"] <= end),
                 key=lambda row: row["year"])

# DESIGN AREA: change these cards, labels, and charts. The case values are real data.
st.markdown(f"### {case['country']} · {start}–{end}")
first, second, third = st.columns(3)
first.metric("Access rate", f"{case['end_rate']:.1f}%", f"+{case['delta_rate']:.1f} points")
second.metric("Still without power", millions(case["end_unserved"]))
third.metric("Change in the gap", f"+{millions(case['delta_unserved'])}", delta_color="inverse")

chart = go.Figure()
chart.add_trace(go.Scatter(x=[row["year"] for row in history],
                           y=[row["access_rate"] for row in history], name="Access rate (%)",
                           mode="lines+markers", line=dict(color=BLUE, width=4)))
chart.add_trace(go.Scatter(x=[row["year"] for row in history],
                           y=[row["unserved"] / 1_000_000 for row in history],
                           name="People without access (M)", mode="lines+markers",
                           line=dict(color=ORANGE, width=4), yaxis="y2"))
chart_style(chart, height=440)
chart.update_layout(title="Two trends, one country", xaxis=dict(dtick=1, gridcolor=GRID),
                    yaxis=dict(title="Access (%)", range=[0, 100], gridcolor=GRID),
                    yaxis2=dict(title="Without access (millions)", overlaying="y", side="right"),
                    legend=dict(orientation="h", y=1.12))
st.plotly_chart(chart, width="stretch")

st.info("**Design prompt:** Can someone understand that the blue line improved while the "
        "orange gap worsened in five seconds? Keep units and sources legible on a projector.")
st.caption(f"Source: World Bank Indicators API · Updated: access {updates['access'] or 'unspecified'}, "
           f"population {updates['population'] or 'unspecified'}. "
           "Estimated unserved = population × (1 − access rate / 100).")
