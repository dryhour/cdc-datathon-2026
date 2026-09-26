"""Shared presentation styles for the Progress Paradox pages."""

import streamlit as st

BLUE = "#78c8fa"
ORANGE = "#ffae77"
TEAL = "#50d4bd"
MUTED = "#93a3ba"
SURFACE = "#17243a"
GRID = "#293a55"


def apply_theme():
    st.markdown("""<style>
        .stApp {background: #0b1220; color: #e9f0f8}
        .block-container {max-width: 1260px; padding-top: 2rem}
        h1, h2, h3 {letter-spacing: -.035em}
        div[data-testid="stMetric"] {background: #17243a; border: 1px solid #293a55;
            border-radius: 14px; padding: 16px 18px}
        div[data-testid="stMetricValue"] {color: #ffb27a}
        .eyebrow {color: #8dc7ec; font-weight: 700; letter-spacing: .17em; font-size: .75rem}
        .hero {background: linear-gradient(120deg,#182d48,#152235 62%,#3a2630);
            border: 1px solid #385270; padding: 28px; border-radius: 20px; margin: 14px 0 22px}
        .hero h1 {font-size: clamp(2rem, 4vw, 3.7rem); line-height: 1.08; margin: 10px 0}
        .hero p {color: #c6d8e8; font-size: 1.07rem; margin-bottom: 0}
        .accent {color: #ffae77}
    </style>""", unsafe_allow_html=True)


def chart_style(fig, height=330):
    fig.update_layout(paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                      font_color="#e9f0f8", height=height,
                      margin=dict(l=35, r=35, t=60, b=40))
    return fig
