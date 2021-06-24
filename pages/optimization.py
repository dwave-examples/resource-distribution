from collections import defaultdict
from typing import DefaultDict

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

def run_page():
    """Main func for optimization page. Runs on any user input on the page.""" 

    # Generate sidebar inputs
    num_hospitals = st.sidebar.number_input("Number of Hospitals", value=52, min_value=2)   
    update_button = st.sidebar.button("Update Map", key="update")
    partition_size = st.sidebar.number_input("Partition Size", value=4, min_value=1)
    num_neighbors = st.sidebar.number_input("Number of Neighbors", value=8)
    dof = st.sidebar.slider("Distance Objective Fraction", value=0.2, min_value=0.0, max_value=1.0, step=0.01)
    solver = st.sidebar.radio("Solver", ["SimulatedAnnealing", "Tabu", "LeapHybridSampler"], index=0)
    time_limit = st.sidebar.number_input("Time Limit", value=10)

    run_button = st.sidebar.button("Run Optimization", key="run")
    st.sidebar.markdown("""---""")

    form = FormInput(num_hospitals=num_hospitals, 
                    partition_size=partition_size, 
                    num_neighbors=num_neighbors, 
                    dof=dof, 
                    solver=solver, 
                    time_limit=time_limit)

    # Initialize map and results
    folium_map = get_empty_map(num_hospitals)
    results_dict = ResultsTable()

    # On run, update map and results
    if run_button:
        if validate_input(form):
            figure, result = get_results(form)

            if result:
                st.sidebar.success("Found solution!")
                results_dict['# of Hospitals'].append(num_hospitals)
                results_dict['Partition Size'].append(partition_size)
                results_dict['# of Neighbors'].append(num_neighbors)
                results_dict['Dist. Objective Fraction'].append(dof)
                results_dict['Solver'].append(form.solver)
                results_dict['Utility'].append(result.total_utility)
                results_dict['Cost'].append(result.total_cost)
                results_dict['Energy'].append(result.energy)
                results_dict['Run Time'].append(result.t)
                
                folium_map = figure
            else:
                st.sidebar.warning("No feasible solution found.")

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
