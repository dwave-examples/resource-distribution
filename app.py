import streamlit as st

from pages import home, optimization

title = "Resource Distribution Optimization"
st.set_page_config(page_title=title, layout="wide")

col, _ = st.beta_columns([1,4]) # Using columns to shorten width of selectbox
page = col.selectbox("Navigation", ["Home", "Optimization"])
st.markdown("""---""")

st.header(title)
if page == "Home":
    home.run_page()
elif page == "Optimization":
    optimization.run_page()
