from pathlib import Path
from collections import defaultdict

import jinja2
import streamlit as st


def render_template(name, **values):
    """Render 'templates/{name}' Jinja2 template."""

    template_dir = Path(__file__).absolute().parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)
    html = env.get_template(name).render(**values)

    return html

def write_style():
    st.write(render_template('style.html'), unsafe_allow_html=True)

def write_title():
    st.write(render_template('title.html'), unsafe_allow_html=True)

def write_header(title):
    st.set_page_config(page_title=title, layout="wide")
    write_style()
    write_title()

@st.cache_resource
def persisted(key, _object_factory=lambda: defaultdict(list)):
    """Cached object for storing results between runs and app reloads.

    Args:
        key: Unique cached object id.
        _object_factory: default object factory.
    """
    return _object_factory()
