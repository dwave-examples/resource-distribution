import streamlit as st
from streamlit_folium import folium_static
import pandas as pd

from utils import us_hospitals, get_empty_map
from page_utils import write_header, persisted
from resource_distribution import FormInput, get_results


map_width, map_height = 1200, 600

def render_sidebar():
    """Render sidebar. Returns the user input (button, form)."""

    num_hospitals = st.sidebar.number_input("Number of Hospitals", value=12, min_value=2)
    update_button = st.sidebar.button("Update Map", key="update")
    solver = st.sidebar.radio("Solver", ["LeapHybridCQMSampler", 
                                         "LeapHybridBQMSampler", 
                                         "SimulatedAnnealing", 
                                         "TabuSampler"], index=0)
    time_limit = st.sidebar.number_input("Time Limit", value=10)

    run_button = st.sidebar.button("Run Optimization", key="run")
    st.sidebar.markdown("---")

    return run_button, FormInput(page='cqm',
                                 num_hospitals=num_hospitals,
                                 solver=solver,
                                 time_limit=time_limit)

def run_page():
    """Runs when user visits optimization page, and on any user input."""

    write_header(title="Resource Distribution Optimization")
    run_button, form = render_sidebar()

    # Generate hospital data
    hospital_df = us_hospitals(form.num_hospitals)

    # Initialize map and results
    folium_map = get_empty_map(hospital_df)
    results_dict = persisted('cqm-results')

    # On run, update map and results
    if run_button:
        result = get_results(form, hospital_df, folium_map)

        if result is None:
            st.sidebar.error("Something went wrong while solving problem. Refresh and try again.")
        elif result.total_transfer == 0:
            st.sidebar.warning("No solution found.")
        else:
            results_dict['# of Hospitals'].append(form.num_hospitals)
            results_dict['Solver'].append(form.solver)

            if not result.error_msgs:
                st.sidebar.success("Found feasible solution!")
                results_dict['All Constraints Satisfied'].append("True")
            else:
                for msg in result.error_msgs:
                    st.sidebar.warning(msg)
                results_dict['All Constraints Satisfied'].append("False")

            results_dict['Transfer'].append(str(round(result.total_transfer, 2)))
            results_dict['Cost'].append(str(round(result.total_cost, 2)))
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
            placeholder.dataframe(df,
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

run_page()