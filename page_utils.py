import base64
from pathlib import Path
from collections import defaultdict

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

def write_style():
    st.write(render_template('style.html'), unsafe_allow_html=True)

def write_title(title):
    html = render_template(
        'title.html',
        logo=img_to_bytes("static/logo_dots.png"),
        title=title)
    st.write(html, unsafe_allow_html=True)

def write_header(title):
    write_style()
    write_title(title)

@st.cache_resource
def persisted(key, _object_factory=lambda: defaultdict(list)):
    """Cached object for storing results between runs and app reloads.

    Args:
        key: Unique cached object id.
        _object_factory: default object factory.
    """
    return _object_factory()
