import streamlit as st

from page_utils import write_header, render_template


write_header(title="Resource Distribution Optimization")

st.components.v1.html(render_template('home.html'), height=3500, scrolling=True)
