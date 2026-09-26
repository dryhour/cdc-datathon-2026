"""Optional standalone map page; the dashboard also embeds this view."""

import streamlit as st
from map_view import render_map

st.set_page_config(page_title="Explore the map · Progress Paradox", page_icon="🌍", layout="wide")
render_map()
