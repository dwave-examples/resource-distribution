from pathlib import Path
from collections import defaultdict
from typing import DefaultDict

import jinja2
import streamlit as st
from streamlit_folium import folium_static
import pandas as pd

from resource_distribution import FormInput, get_empty_map, get_results

map_width, map_height = 1000, 600

@st.cache(allow_output_mutation=True)
def ResultsTable() -> DefaultDict:
    """Cached object for storing results. Allows us to keep results from previous runs."""
    return defaultdict(list)

def validate_input(form: FormInput) -> bool:
    """Validate form input from user."""
    if form.num_hospitals % form.partition_size != 0:
        st.sidebar.error("The partition size must be divisible by the number of hospitals.")
        return False
    elif form.num_neighbors < form.partition_size - 1 or form.num_neighbors > form.num_hospitals:
        st.sidebar.error("Number of neighbors must be >= the partition size and <= the number of hospitals.")
        return False
    
    return True

def header():
    """Render 'templates/header.html'."""
    # Could just do a st.header, but using a template instead so that the header can be shared
    # between pages (and use the same css).
    template_dir = Path(__file__).absolute().parent.parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)
    
    header_html = env.get_template('header.html').render()
    st.components.v1.html(header_html, height=60, scrolling=False)

def sidebar():
    """Render sidebar. Returns the user input (button, form)."""
    st.sidebar.markdown("""---""")
    num_hospitals = st.sidebar.number_input("Number of Hospitals", value=12, min_value=2)
    update_button = st.sidebar.button("Update Map", key="update")
    partition_size = st.sidebar.number_input("Partition Size", value=4, min_value=1)
    num_neighbors = st.sidebar.number_input("Number of Neighbors", value=8)
    dof = st.sidebar.slider("Distance Objective Fraction", value=0.2, min_value=0.0, max_value=1.0, step=0.01)
    solver = st.sidebar.radio("Solver", ["SimulatedAnnealing", "TabuSampler", "LeapHybridSampler"], index=0)
    time_limit = st.sidebar.number_input("Time Limit", value=10)

    run_button = st.sidebar.button("Run Optimization", key="run")
    st.sidebar.markdown("""---""")

    return run_button, FormInput(num_hospitals=num_hospitals,
                                 partition_size=partition_size,
                                 num_neighbors=num_neighbors,
                                 dof=dof,
                                 solver=solver,
                                 time_limit=time_limit)

def run_page():
    """Runs when user visits optimization page, and on any user input."""
    header()
    run_button, form = sidebar()

    # Initialize map and results
    folium_map = get_empty_map(form.num_hospitals)
    results_dict = ResultsTable()   # cache containing previous results

    # On run, update map and results
    if run_button:
        if validate_input(form):
            figure, result = get_results(form)

            results_dict['# of Hospitals'].append(form.num_hospitals)
            results_dict['Partition Size'].append(form.partition_size)
            results_dict['# of Neighbors'].append(form.num_neighbors)
            results_dict['Dist. Objective Fraction'].append(form.dof)
            results_dict['Solver'].append(form.solver)

            if result:
                st.sidebar.success("Found solution!")
                results_dict['Utility'].append(result.total_utility)
                results_dict['Cost'].append(result.total_cost)
                results_dict['Energy'].append(result.energy)
                results_dict['Run Time'].append(result.t)
                folium_map = figure
            else:
                st.sidebar.warning("No feasible solution found.")
                results_dict['Utility'].append('N/A')
                results_dict['Cost'].append('N/A')
                results_dict['Energy'].append('N/A')
                results_dict['Run Time'].append('N/A')

    # Display map and results
    folium_static(folium_map, width=map_width, height=map_height)

    st.subheader("Results")
    clear_button = st.button("Clear Results")
    if clear_button:
        results_dict.clear()

    if results_dict:
        try:
            df = pd.DataFrame(results_dict)
            st.write(df)
        except:
            # Something wrong with cached dictionary -> reset and give warning
            results_dict.clear()
            st.error("Something went wrong. Try again please.")
