import streamlit as st

from pages import home, optimization_bqm, optimization_cqm

title = "Resource Distribution Optimization"
st.set_page_config(page_title=title, layout="wide")

page = st.sidebar.selectbox("Navigation", ["Home", "Optimization - BQM", "Optimization - CQM"])

if page == "Home":
    home.run_page()
elif page == "Optimization - BQM":
    optimization_bqm.run_page()
elif page == "Optimization - CQM":
    optimization_cqm.run_page()
