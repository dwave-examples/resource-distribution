import base64
from pathlib import Path

import streamlit as st
import jinja2


def img_to_bytes(img_path: str) -> str:
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def run_page():
    """Runs when user visits home page."""
    template_dir = Path(__file__).absolute().parent.parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)

    # Display header
    header_html = env.get_template('header.html').render()
    st.components.v1.html(header_html, height=60)

    # Display rest of home page
    home = env.get_template('home.html')
    home_html = home.render(partitioning=img_to_bytes("assets/partitioning.png"),
                            partition_with_distance=img_to_bytes("assets/partition_with_distance.png"))

    st.components.v1.html(home_html, height=3000, scrolling=True)

    # Both templates (header.html and home.html) include the stylesheet already,
    # but we include it here again for the sidebar.
    with open("templates/style.html") as css:
        stylesheet = css.read()
    st.write(stylesheet, unsafe_allow_html=True)
