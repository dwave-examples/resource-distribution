import streamlit as st
from streamlit_folium import folium_static
import pandas as pd

from utils import us_hospitals, get_empty_map
from page_utils import write_header, persisted
from resource_distribution import FormInput, get_results

from app_configs import (DESCRIPTION_CQM, MAIN_HEADER_CQM, NUM_HOSPITALS, PARTITION_SIZE, DISTANCE_OBJECTIVE_FRACTION, NUM_NEIGHBORS, SOLVER_TIME,
                         THUMBNAIL, SAMPLER_TYPES_CQM)
from dash import dcc, html, register_page


map_width, map_height = 1200, 600

register_page(__name__)

def description_card():
    """A Div containing dashboard title & descriptions."""
    return html.Div(
        id="description-card",
        children=[html.H1(MAIN_HEADER_CQM), html.P(DESCRIPTION_CQM)],
    )

def generate_control_card() -> html.Div:
    """
    This function generates the control card for the dashboard, which
    contains the dropdowns for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the dropdowns for selecting the scenario,
        model, and solver.
    """

    return html.Div(
        id="control-card",
        children=[
            html.Label("Number of Hospitals"),
            dcc.Input(
                id="num-hospitals",
                className="select",
                type="number",
                **NUM_HOSPITALS,
            ),
            dcc.Slider(0, 2, 1, id="partition-size", className="display-none"), # Dash does not support optional parameters yet
            dcc.Slider(0, 2, 1, id="num-neighbors", className="display-none"),  # Creating "fake" sliders allows us to use the same functions for both pages
            dcc.Slider(0, 2, 1, id="distance-objective-fraction", className="display-none"),
            html.Label("Solver"),
            dcc.Dropdown(
                id="sampler-type-select",
                options=SAMPLER_TYPES_CQM,
                value=SAMPLER_TYPES_CQM[0]["value"],
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
                id="warning",
                children=[]
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
                        html.Div([
                            html.Div([
                                description_card(),
                                generate_control_card(),
                                html.Div(["initial child"], id="output-clientside", style={"display": "none"}),
                            ])
                        ]),
                        html.Div(
                            html.Button(id="left-column-collapse", children=[html.Div()]),
                        )
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
                                                html.H3("Solution"),
                                                html.Table(
                                                    id="solution-table",
                                                    className="result-table",
                                                    children=[] # add children dynamically using 'create_table'
                                                )
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
