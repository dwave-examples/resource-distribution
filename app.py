import streamlit as st

from pages import home

title = "Resource Distribution Optimization"
st.set_page_config(page_title=title, layout="wide")

page = st.sidebar.selectbox("Navigation", ["Home", "Optimization - BQM", "Optimization - CQM"])

if page == "Home":
    home.run_page()
