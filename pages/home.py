import base64
from pathlib import Path

import streamlit as st
import jinja2


def img_to_bytes(img_path: str) -> str:
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def render_header():
    """Display header."""
    logo = img_to_bytes("assets/logo_dots.png")
    st.markdown(
        f'<div class="header"> \
          <img src="data:image/gif;base64,{logo}"> \
          <h1>Resource Distribution Demonstration</h1> \
          </div>',
        unsafe_allow_html=True,
    )

def run_page():
    """Runs when user visits home page."""
    template_dir = Path(__file__).absolute().parent.parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)

    # Render style.html to link the sidebar with style.css
    style = env.get_template('style.html').render()
    st.write(style, unsafe_allow_html=True)

    # Display header
    render_header()

    # Display rest of home page
    home = env.get_template('home.html')
    home_html = home.render(c1=img_to_bytes("assets/c1.png"),
                            c2=img_to_bytes("assets/c2.png"),
                            obj=img_to_bytes("assets/obj.png"),
                            partitioning=img_to_bytes("assets/partitioning.png"),
                            partition_with_distance=img_to_bytes("assets/partition_with_distance.png"))

    st.components.v1.html(home_html, height=3000, scrolling=True)
