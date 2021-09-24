from pathlib import Path
from collections import defaultdict
from typing import DefaultDict

import jinja2
import streamlit as st
from streamlit_folium import folium_static
import pandas as pd

from utils import us_hospitals, get_empty_map
from resource_distribution import FormInput, get_results
from pages.home import render_header

map_width, map_height = 1200, 600

@st.cache(allow_output_mutation=True)
def ResultsTable(model: str = None) -> DefaultDict:
    """Cached object for storing results. Allows us to keep results from previous runs.
    
    Args:
        model: Used to keep the two cached dicts (BQM and CQM) separate.
    """
    return defaultdict(list)

def validate_input(form: FormInput) -> bool:
    """Validate form input from user."""
    if form.num_hospitals <= form.partition_size or form.num_hospitals % form.partition_size != 0:
        st.sidebar.error("The partition size must be less than and divisible by the number of hospitals.")
        return False
    elif form.num_neighbors < form.partition_size - 1 or form.num_neighbors > form.num_hospitals:
        st.sidebar.error("Number of neighbors must be >= the partition size and <= the number of hospitals.")
        return False
    
    return True

def render_style():
    """Render 'templates/style.html'."""
    template_dir = Path(__file__).absolute().parent.parent.joinpath('templates')
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)

    style = env.get_template('style.html').render()
    st.write(style, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar. Returns the user input (button, form)."""
    st.sidebar.markdown("---")
    num_hospitals = st.sidebar.number_input("Number of Hospitals", value=12, min_value=2)
    update_button = st.sidebar.button("Update Map", key="update")
    partition_size = st.sidebar.number_input("Partition Size", value=4, min_value=1)
    num_neighbors = st.sidebar.number_input("Number of Neighbors", value=8)
    dof = st.sidebar.slider("Distance Objective Fraction", value=0.2, min_value=0.0, max_value=1.0, step=0.01)
    solver = st.sidebar.radio("Solver", ["SimulatedAnnealing", 
                                         "TabuSampler", 
                                         "LeapHybridBQMSampler"], index=0)
    time_limit = st.sidebar.number_input("Time Limit", value=10)

    run_button = st.sidebar.button("Run Optimization", key="run")
    st.sidebar.markdown("---")

    return run_button, FormInput(page='bqm',
                                 num_hospitals=num_hospitals,
                                 partition_size=partition_size,
                                 num_neighbors=num_neighbors,
                                 dof=dof,
                                 solver=solver,
                                 time_limit=time_limit)

def run_page():
    """Runs when user visits optimization page, and on any user input."""
    render_style()
    render_header()
    run_button, form = render_sidebar()

    # Generate hospital data
    hospital_df = us_hospitals(form.num_hospitals)

    # Initialize map and results
    folium_map = get_empty_map(hospital_df)
    results_dict = ResultsTable(model='bqm')   # cache containing previous results

    # On run, update map and results
    if run_button:
        if validate_input(form):
            result = get_results(form, hospital_df, folium_map)

            if result is None:
                st.sidebar.error("Something went wrong while solving problem. Refresh and try again.")
            elif result.total_transfer == 0:
                st.sidebar.warning("No solution found.")
            else:
                results_dict['# of Hospitals'].append(form.num_hospitals)
                results_dict['Partition Size'].append(form.partition_size)
                results_dict['# of Neighbors'].append(form.num_neighbors)
                results_dict['Dist. Obj. Fraction'].append(form.dof)
                results_dict['Solver'].append(form.solver)

                if not result.error_msgs:
                    st.sidebar.success("Found feasible solution!")
                    results_dict['Constraints Satisfied'].append("True")
                else:
                    for msg in result.error_msgs:
                        st.sidebar.warning(msg)
                    results_dict['Constraints Satisfied'].append("False")

                results_dict['Transfer'].append(str(round(result.total_transfer, 2)))
                results_dict['Cost'].append(str(round(result.total_cost, 2)))
                results_dict['Energy'].append(str(round(result.energy, 2)))
                results_dict['Run Time'].append(str(round(result.run_time, 2)))
                folium_map = result.figure

    # Display map and results
    folium_static(folium_map, width=map_width, height=map_height)
    st.markdown("<h2>Results</h2>", unsafe_allow_html=True)

    # Using st.empty() allows us to remove elements from a page without reloading
    placeholder = st.empty()

    if results_dict:
        try:
            df = pd.DataFrame(results_dict)
            placeholder.dataframe(df.style.format(formatter={'Dist. Obj. Fraction': '{:.2f}'}),
                                  width=map_width)
        except Exception as e:
            # Something wrong with cached dictionary -> reset and give warning
            results_dict.clear()
            st.error("Something went wrong. Clear results and try again please.")
            print(e)

    clear_button = st.button("Clear Results")
    if clear_button:
        results_dict.clear()
        placeholder.empty()
