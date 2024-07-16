from dash_html import SAMPLER_TYPES
from pages.bqm import dropdown

from app_configs import (DESCRIPTION_CQM, MAIN_HEADER_CQM, NUM_HOSPITALS, SOLVER_TIME,
                         THEME_COLOR_SECONDARY)
from dash import dcc, html, register_page

register_page(__name__)


def generate_control_card() -> html.Div:
    """This function generates the control card for the dashboard, which
        contains the settings for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the settings for selecting the scenario,
            model, and solver.
    """

    sampler_options = [
        {"label": label, "value": sampler_type.value}
        for sampler_type, label in SAMPLER_TYPES.items()
    ]

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
            dropdown(
                "Solver",
                "sampler-type-select",
                sampler_options,
            ),
            html.Label("Solver Time Limit (seconds)"),
            dcc.Input(
                id="solver-time-limit",
                type="number",
                **SOLVER_TIME,
            ),
            html.Div(id="warning", className="display-none"),
            # Run and cancel buttons to run the optimization.
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
                        className="display-none",
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
            className="columns-main",
            children=[
                # Left column
                html.Div(
                    id={"type": "to-collapse-class", "index": 0},
                    className="left-column",
                    children=[
                        html.Div(
                            className="left-column-layer-1",  # Fixed width Div to collapse
                            children=[
                                html.Div(
                                    className="left-column-layer-2",  # Padding and content wrapper
                                    children=[
                                        html.Div(
                                            className="description-card",
                                            children=[
                                                html.H1(MAIN_HEADER_CQM),
                                                html.P(DESCRIPTION_CQM),
                                            ],
                                        ),
                                        generate_control_card(),
                                    ],
                                )
                            ],
                        ),
                        # Left column collapse button
                        html.Div(
                            html.Button(
                                id={"type": "collapse-trigger", "index": 0},
                                className="left-column-collapse",
                                children=[html.Div(className="collapse-arrow")],
                            ),
                        ),
                    ],
                ),
                # Right column
                html.Div(
                    className="right-column",
                    children=[
                        dcc.Tabs(
                            id="tabs",
                            value="input-tab",
                            children=[
                                dcc.Tab(
                                    label="Map",
                                    id="input-tab",
                                    value="input-tab",  # used for switching to programatically
                                    className="tab",
                                    children=[
                                        dcc.Loading(
                                            parent_className="input",
                                            type="circle",
                                            color=THEME_COLOR_SECONDARY,
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
                                                    # add children dynamically using 'create_table'
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
