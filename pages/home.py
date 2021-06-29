import os
import base64

import streamlit as st

from pathlib import Path
from jinja2 import Template

def img_to_bytes(img_path: str) -> str:
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def run_page():
    """Runs when user visits home page."""

    with open("templates/home.html") as home:
        template = Template(home.read())
        home_html = template.render(partitioning=img_to_bytes("assets/partitioning.png"), 
                                    partition_with_distance=img_to_bytes("assets/partition_with_distance.png"))

    # css works but mathjax doesn't
    # st.write(home_html, unsafe_allow_html=True)

    # mathjax works but css doesn't
    st.components.v1.html(home_html, height=3000, scrolling=True)
