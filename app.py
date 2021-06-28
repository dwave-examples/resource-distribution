import streamlit as st

from pages import home, optimization

title = "Resource Distribution Optimization"
st.set_page_config(page_title=title, layout="wide")

page = st.sidebar.selectbox("Navigation", ["Home", "Optimization"])

st.header(title)
if page == "Home":
    home.run_page()
elif page == "Optimization":
    optimization.run_page()
