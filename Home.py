import streamlit as st

from page_utils import write_header, render_template


def run_page():
    """Runs when user visits home page."""

    title = "Resource Distribution Optimization"
    st.set_page_config(page_title=title, layout="wide")

    write_header(title=title)

    home_html = render_template('home.html')
    st.components.v1.html(home_html, height=3500, scrolling=True)

run_page()