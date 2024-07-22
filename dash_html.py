# Copyright 2024 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from collections import defaultdict
import html

from dash import dcc, html

from app_configs import DESCRIPTION_BQM, DISTANCE_OBJECTIVE_FRACTION, MAIN_HEADER_BQM, NUM_HOSPITALS, NUM_NEIGHBORS, PARTITION_SIZE, SOLVER_TIME, THEME_COLOR_SECONDARY, THUMBNAIL
from src.enums import Formulation, SamplerType

FORMULATION = {
    Formulation.BQM.value: "BQM",
    Formulation.CQM.value: "CQM",
}

SAMPLER_TYPES = {
    SamplerType.CQM: "Quantum Hybrid (CQM)",
    SamplerType.BQM: "Quantum Hybrid (BQM)",
    SamplerType.TABU: "Tabu",
    SamplerType.SIM_ANNEAL: "Simulated Annealing",
}

SAMPLER_OPTIONS_ALL = [
    {"label": label, "value": sampler_type.value}
    for sampler_type, label in SAMPLER_TYPES.items()
]


def slider(label: str, id: str, config: dict, index: int) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configerations, see dcc.Slider docs.
        index: A unique identifier.
    """
    return html.Div(
        className="slider-wrapper",
        id={"type": "slider", "index": index},
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


def create_table(
    values_dicts: defaultdict, not_satisfied: bool
) -> list[html.Thead, html.Tbody]:
    """Create a row in the table dynamically.

    Args:
        values_dicts: List of dictionaries with vehicle number as results data as values.
        values_tot: List of total results data (sum of individual vehicle data).
    """

    table = [
        html.Thead([html.Tr([html.Th(header) for header in values_dicts.keys()])]),
        html.Tbody([html.Tr([html.Td(value) for value in values_dicts.values()], className=f"{'not_satisfied' if not_satisfied else ''}")])
    ]

    return table


def update_table(
    prev_table: list[html.Thead, html.Tbody], values_dicts: defaultdict, not_satisfied: bool
) -> list[html.Thead, html.Tbody]:
    """Create a row in the table dynamically.

    Args:
        values_dicts: List of dictionaries with vehicle number as results data as values.
        values_tot: List of total results data (sum of individual vehicle data).
    """

    thead, tbody = prev_table

    table = [
        thead,
        html.Tbody(
            [
                *tbody['props']['children'],
                html.Tr([html.Td(value) for value in values_dicts.values()], className=f"{'not_satisfied' if not_satisfied else ''}")
            ]
        )
    ]

    return table


def create_warning(
    warnings: list[str]
) -> html.Div:
    """Outputs a div containing a list of warnings

    Args:
        warnings: A list of warning strings
    """

    return html.Div([html.P(warning) for warning in warnings])


def generate_settings_form() -> html.Div:
    """This function generates settings for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the settings for selecting the scenario, model, and solver.
    """

    return html.Div(
        className="settings",
        children=[
            html.Div(
                className="caption-wrapper",
                children=[
                    html.Div(
                        [
                            html.Label("Number of Hospitals"),
                            dcc.Input(
                                id="num-hospitals",
                                type="number",
                                **NUM_HOSPITALS,
                            ),
                        ]
                    ),
                    html.P(
                        html.Small(
                            "The number of hospitals must be divisible by the partition size."
                        ),
                        id="small-caption",
                        className="display-none"
                    ),
                ]
            ),
            slider(
                "Partition Size",
                "partition-size",
                PARTITION_SIZE,
                0,
            ),
            slider(
                "Number of Neighbors",
                "num-neighbors",
                NUM_NEIGHBORS,
                1,
            ),
            slider(
                "Distance Objective Fraction",
                "distance-objective-fraction",
                DISTANCE_OBJECTIVE_FRACTION,
                2,
            ),
            dropdown(
                "Solver",
                "sampler-type-select",
                SAMPLER_OPTIONS_ALL,
            ),
            html.Label("Solver Time Limit (seconds)"),
            dcc.Input(
                id="solver-time-limit",
                type="number",
                **SOLVER_TIME,
            ),
        ]
    )


def generate_run_buttons() -> html.Div:
    """Run and cancel buttons to run the optimization."""
    return html.Div(
        id="button-group",
        children=[
            html.Button(id="run-button", children="Run Optimization", n_clicks=0, disabled=False),
            html.Button(
                id="cancel-button",
                children="Cancel Optimization",
                n_clicks=0,
                className="display-none",
            ),
        ],
    )


def set_html(app):
    """Set the application HTML."""
    app.layout = html.Div(
        id="app-container",
        children=[
            # below are any temporary storage items, e.g., for sharing data between callbacks
            dcc.Store(id="last-formulation"),  # formulation used for latest run
            dcc.Store(id="selected-formulation"),  # The currently selected and displayed formulation
            # Banner
            html.Div(
                className="banner",
                children=[
                    html.Img(src=THUMBNAIL),
                    html.Div([
                        html.Div(
                            html.Button(
                                formulation_option,
                                id={
                                    "type": "formulation-option",
                                    "index": index
                                },
                            )
                        ) for index, formulation_option in FORMULATION.items()
                    ]),
                ]
            ),
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
                                            html.H1(id="header", children=[MAIN_HEADER_BQM]),
                                            html.P(id="description", children=[DESCRIPTION_BQM]),
                                            generate_settings_form(),
                                            generate_run_buttons(),
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
                                                className="tab-content-results",
                                                children=[
                                                    html.Table(
                                                        id="solution-table",
                                                        className="result-table",
                                                        # add children dynamically using 'create_table'
                                                    ),
                                                    html.Div(id="warning", className="display-none"),
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
