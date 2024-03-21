import streamlit as st
from streamlit_folium import folium_static
import pandas as pd

from utils import us_hospitals, get_empty_map
from page_utils import write_header, persisted
from resource_distribution import FormInput, get_results

from app_configs import (DESCRIPTION_BQM, MAIN_HEADER_BQM, NUM_HOSPITALS, PARTITION_SIZE, DISTANCE_OBJECTIVE_FRACTION, NUM_NEIGHBORS, SOLVER_TIME,
                         THUMBNAIL)
from dash import dcc, html, register_page

SAMPLER_TYPES = ["Simulated Annealing", "Tabu Sampler", "Leap Hybrid BQM Sampler"]



map_width, map_height = 1200, 600

register_page(__name__)

# def validate_input(form: FormInput) -> bool:
#     """Validate form input from user."""

#     if form.num_hospitals <= form.partition_size or form.num_hospitals % form.partition_size != 0:
#         st.sidebar.error("The partition size must be less than and divisible by the number of hospitals.")
#         return False
#     elif form.num_neighbors < form.partition_size - 1 or form.num_neighbors > form.num_hospitals:
#         st.sidebar.error("Number of neighbors must be >= the partition size and <= the number of hospitals.")
#         return False
    
#     return True

# def render_sidebar():
#     """Render sidebar. Returns the user input (button, form)."""

    # num_hospitals = st.sidebar.number_input("Number of Hospitals", value=12, min_value=2)
    # update_button = st.sidebar.button("Update Map", key="update")
    # partition_size = st.sidebar.number_input("Partition Size", value=4, min_value=1)
    # num_neighbors = st.sidebar.number_input("Number of Neighbors", value=8)
    # dof = st.sidebar.slider("Distance Objective Fraction", value=0.2, min_value=0.0, max_value=1.0, step=0.01)
    # solver = st.sidebar.radio("Solver", ["SimulatedAnnealing", 
    #                                      "TabuSampler", 
    #                                      "LeapHybridBQMSampler"], index=0)
    # time_limit = st.sidebar.number_input("Time Limit", value=10)

    # run_button = st.sidebar.button("Run Optimization", key="run")
    # st.sidebar.markdown("---")

    # return run_button, FormInput(page='bqm',
    #                              num_hospitals=num_hospitals,
    #                              partition_size=partition_size,
    #                              num_neighbors=num_neighbors,
    #                              dof=dof,
    #                              solver=solver,
    #                              time_limit=time_limit)


def description_card():
    """A Div containing dashboard title & descriptions."""
    return html.Div(
        id="description-card",
        children=[html.H1(MAIN_HEADER_BQM), html.P(DESCRIPTION_BQM)],
    )

def generate_control_card() -> html.Div:
    """
    This function generates the control card for the dashboard, which
    contains the dropdowns for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the dropdowns for selecting the scenario,
        model, and solver.
    """
    sampler_options = [{"label": sampler, "value": i} for i, sampler in enumerate(SAMPLER_TYPES)]

    return html.Div(
        id="control-card",
        children=[
            html.Label("Number of Hospitals"),
            dcc.Slider(
                id="num-hospitals",
                className="select",
                **NUM_HOSPITALS,
                marks={
                    NUM_HOSPITALS["min"]: str(NUM_HOSPITALS["min"]),
                    NUM_HOSPITALS["max"]: str(NUM_HOSPITALS["max"]),
                },
                tooltip={
                    "placement": "top",
                    "always_visible": True,
                },
            ),
            html.Label("Partition Size"),
            dcc.Slider(
                id="partition-size",
                className="select",
                **PARTITION_SIZE,
                marks={
                    PARTITION_SIZE["min"]: str(PARTITION_SIZE["min"]),
                    PARTITION_SIZE["max"]: str(PARTITION_SIZE["max"]),
                },
                tooltip={
                    "placement": "top",
                    "always_visible": True,
                },
            ),
            html.Label("Number of Neighbors"),
            dcc.Slider(
                id="num-neighbors",
                className="select",
                **NUM_NEIGHBORS,
                marks={
                    NUM_NEIGHBORS["min"]: str(NUM_NEIGHBORS["min"]),
                    NUM_NEIGHBORS["max"]: str(NUM_NEIGHBORS["max"]),
                },
                tooltip={
                    "placement": "top",
                    "always_visible": True,
                },
            ),
            html.Label("Distance Objective Fraction"),
            dcc.Slider(
                id="distance-objective-fraction",
                className="select",
                **DISTANCE_OBJECTIVE_FRACTION,
                marks={
                    DISTANCE_OBJECTIVE_FRACTION["min"]: str(DISTANCE_OBJECTIVE_FRACTION["min"]),
                    DISTANCE_OBJECTIVE_FRACTION["max"]: str(DISTANCE_OBJECTIVE_FRACTION["max"]),
                },
                tooltip={
                    "placement": "top",
                    "always_visible": True,
                },
            ),
            html.Label("Solver"),
            dcc.Dropdown(
                id="sampler-type-select",
                options=sampler_options,
                value=sampler_options[0]["value"],
                clearable=False,
                searchable=False,
            ),
            html.Label("Solver Time Limit (seconds)"),
            dcc.Input(
                id="solver-time-limit",
                type="number",
                **SOLVER_TIME,
            ),
            html.Div(
                id="button-group",
                children=[
                    html.Button(
                        id="run-button", children="Run Optimization", n_clicks=0, disabled=False
                    ),
                    html.Button(
                        id="cancel-button",
                        children="Cancel Optimization",
                        n_clicks=0,
                        style={"display": "none"},
                    ),
                ],
            ),
        ],
    )

layout = html.Div(
    id="app-container",
    children=[
        # below are any temporary storage items, e.g., for sharing data between callbacks
        dcc.Store(id="stored-results"),  # temporarily stored results table
        dcc.Store(id="sampler-type"),  # solver type used for latest run
        dcc.Store(
            id="reset-results"
        ),  # whether to reset the results tables before displaying the latest run
        dcc.Store(
            id="run-in-progress", data=False
        ),  # callback blocker to signal that the run is complete
        dcc.Store(id="parameter-hash"),  # hash string to detect changed parameters
        html.Div(
            id="columns",
            children=[
                # Left column
                html.Div(
                    id="left-column",
                    className="four-columns",
                    children=[
                        description_card(),
                        generate_control_card(),
                        html.Div(["initial child"], id="output-clientside", style={"display": "none"}),
                    ],
                ),
                # Right column
                html.Div(
                    id="right-column",
                    children=[
                        dcc.Tabs(
                            id="tabs",
                            value="map-tab",
                            children=[
                                dcc.Tab(
                                    label="Map",
                                    id="map-tab",
                                    value="map-tab",  # used for switching to programatically
                                    className="tab",
                                    children=[
                                        dcc.Loading(
                                            id="loading",
                                            type="circle",
                                            color="#17BEBB",
                                            children=html.Iframe(id="solution-map")
                                        ),],
                                ),
                                dcc.Tab(
                                    label="Results",
                                    id="results-tab",
                                    className="tab",
                                    disabled=True,
                                    children=[
                                        html.Div(
                                            className="tab-content--results",
                                            children=[
                                                html.H3("Solution Stats"),
                                            ]
                                        )
                                    ],
                                ),
                            ],
                        )
                    ],
                ),
            ]
        )
    ],
)

# def run_page():
#     """Runs when user visits optimization page, and on any user input."""

#     title = "Resource Distribution Optimization"
#     st.set_page_config(page_title=title, layout="wide")
#     write_header(title=title)
#     run_button, form = render_sidebar()

#     # Generate hospital data
#     hospital_df = us_hospitals(form.num_hospitals)

#     # Initialize map and results
#     folium_map = get_empty_map(hospital_df)
#     results_dict = persisted('bqm-results')

#     # On run, update map and results
#     if run_button:
#         if validate_input(form):
#             result = get_results(form, hospital_df, folium_map)

#             if result is None:
#                 st.sidebar.error("Something went wrong while solving problem. Refresh and try again.")
#             elif result.total_transfer == 0:
#                 st.sidebar.warning("No solution found.")
#             else:
#                 results_dict['# of Hospitals'].append(form.num_hospitals)
#                 results_dict['Partition Size'].append(form.partition_size)
#                 results_dict['# of Neighbors'].append(form.num_neighbors)
#                 results_dict['Dist. Obj. Fraction'].append(form.dof)
#                 results_dict['Solver'].append(form.solver)

#                 if not result.error_msgs:
#                     st.sidebar.success("Found feasible solution!")
#                     results_dict['Constraints Satisfied'].append("True")
#                 else:
#                     for msg in result.error_msgs:
#                         st.sidebar.warning(msg)
#                     results_dict['Constraints Satisfied'].append("False")

#                 results_dict['Transfer'].append(str(round(result.total_transfer, 2)))
#                 results_dict['Cost'].append(str(round(result.total_cost, 2)))
#                 results_dict['Energy'].append(str(round(result.energy, 2)))
#                 results_dict['Run Time'].append(str(round(result.run_time, 2)))
#                 folium_map = result.figure

#     # Display map and results
#     folium_static(folium_map, width=map_width, height=map_height)
#     st.markdown("<h2>Results</h2>", unsafe_allow_html=True)

#     # Using st.empty() allows us to remove elements from a page without reloading
#     placeholder = st.empty()

#     if results_dict:
#         try:
#             df = pd.DataFrame(results_dict)
#             placeholder.dataframe(df.style.format(formatter={'Dist. Obj. Fraction': '{:.2f}'}),
#                                   width=map_width)
#         except Exception as e:
#             # Something wrong with cached dictionary -> reset and give warning
#             results_dict.clear()
#             st.error("Something went wrong. Clear results and try again please.")
#             print(e)

#     clear_button = st.button("Clear Results")
#     if clear_button:
#         results_dict.clear()
#         placeholder.empty()

# run_page()