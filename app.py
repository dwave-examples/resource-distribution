from pathlib import Path
import streamlit as st

from pages import home, optimization

title = "Resource Distribution Optimization"
st.set_page_config(page_title=title, layout="wide")

with open("templates/stylesheet.html") as css:
  stylesheet = css.read()

st.write(stylesheet, unsafe_allow_html=True)

page = st.sidebar.selectbox("Navigation", ["Home", "Optimization"])

header = Path("templates/header.html").read_text()
st.markdown(header, unsafe_allow_html=True)

if page == "Home":
    home.run_page()
elif page == "Optimization":
    optimization.run_page()
