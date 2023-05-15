import streamlit as st

from page_utils import img_to_bytes, print_header, print_style, render_template


def run_page():
    """Runs when user visits home page."""

    st.set_page_config(
        page_title="Resource Distribution Optimization", layout="wide")

    print_style()
    print_header()

    home_html = render_template(
        'home.html',
        partitioning=img_to_bytes("assets/partitioning.png"),
        partition_with_distance=img_to_bytes("assets/partition_with_distance.png"))
    st.components.v1.html(home_html, height=3400, scrolling=True)

run_page()