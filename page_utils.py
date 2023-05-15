import base64
from pathlib import Path

import jinja2
import streamlit as st


def img_to_bytes(img_path: str) -> str:
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def render_template(name, **values):
    """Render 'templates/{name}' Jinja2 template."""

    template_dir = Path(__file__).absolute().parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)
    html = env.get_template(name).render(**values)

    return html

def print_header():
    """Display header."""
    logo = img_to_bytes("assets/logo_dots.png")
    st.markdown(
        f'<div class="header"> \
          <img src="data:image/gif;base64,{logo}"> \
          <h1>Resource Distribution Demonstration</h1> \
          </div>',
        unsafe_allow_html=True,
    )

def print_style():
    st.write(render_template('style.html'), unsafe_allow_html=True)
