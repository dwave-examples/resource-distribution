from app_configs import (DESCRIPTION_BQM, MAIN_HEADER_BQM, NUM_HOSPITALS, PARTITION_SIZE, DISTANCE_OBJECTIVE_FRACTION, NUM_NEIGHBORS, SOLVER_TIME,
                         THEME_COLOR_SECONDARY)
from dash import dcc, html, register_page
from dash_html import SAMPLER_TYPES
from src.enums import SamplerType

register_page(__name__)


def slider(label: str, id: str, config: dict) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configerations, see dcc.Slider docs.
    """
    return html.Div(
        className="slider-wrapper",
        children=[
            html.Label(label),
            dcc.Slider(
                id=id,
                className="slider",
                **config,
                marks={
                    config["min"]: str(config["min"]),
                    config["max"]: str(config["max"]),
                },
                tooltip={
                    "placement": "bottom",
                    "always_visible": True,
                },
            ),
        ],
    )


def dropdown(label: str, id: str, options: list) -> html.Div:
    """Dropdown element for option selection.

    Args:
        label: The title that goes above the dropdown.
        id: A unique selector for this element.
        options: A list of dictionaries of labels and values.
    """
    return html.Div(
        className="dropdown-wrapper",
        children=[
            html.Label(label),
            dcc.Dropdown(
                id=id,
                options=options,
                value=options[0]["value"],
                clearable=False,
                searchable=False,
            ),
        ],
    )


def generate_control_card() -> html.Div:
    """This function generates the control card for the dashboard, which
        contains the settings for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the settings for selecting the scenario,
            model, and solver.
    """

    sampler_options = []
    for sampler_type, label in SAMPLER_TYPES.items():
        if sampler_type != SamplerType.CQM:
            sampler_options.append({"label": label, "value": sampler_type.value})


    return html.Div(
        id="control-card",
        children=[
            html.Label("Number of Hospitals"),
            dcc.Input(
                id="num-hospitals",
                type="number",
                **NUM_HOSPITALS,
            ),
            slider(
                "Partition Size",
                "partition-size",
                PARTITION_SIZE,
            ),
            # html.Caption("The number of hospitals must be divisible by this value."),
            slider(
                "Number of Neighbors",
                "num-neighbors",
                NUM_NEIGHBORS,
            ),
            # html.Caption("This value must be greater than or equal to the partition size and less than or equal to the number of hospitals."),
            slider(
                "Distance Objective Fraction",
                "distance-objective-fraction",
                DISTANCE_OBJECTIVE_FRACTION,
            ),
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
                                                html.H1(id="header", children=[MAIN_HEADER_BQM]),
                                                html.P(id="description", children=[DESCRIPTION_BQM]),
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
