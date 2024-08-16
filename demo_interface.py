# Copyright 2024 D-Wave
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

import html
from collections import defaultdict

import dash_bootstrap_components as dbc
from dash import dcc, html

from demo_configs import (
    DESCRIPTION,
    DISTANCE_OBJECTIVE_FRACTION,
    MAIN_HEADER,
    NUM_HOSPITALS,
    NUM_NEIGHBORS,
    PARTITION_SIZE,
    SOLVER_TIME,
    THEME_COLOR_SECONDARY,
    THUMBNAIL,
)
from src.demo_enums import SolverType


def slider(label: str, id: str, config: dict, index: int) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configerations, see dcc.Slider docs.
        index: A unique identifier.
    """
    return html.Div(
        className="display-none",
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


def generate_table(results_dict: defaultdict) -> list[html.Thead, html.Tbody]:
    """Generates solution table.

    Args:
        results_dict: Dictionary of lists of results values from all previous runs.
    """

    dict_vals = [val for key, val in results_dict.items() if key != "Error"]
    error_msg = results_dict["Error"]

    return [
        html.Thead(
            [
                html.Tr(
                    [
                        html.Th("Run"),
                        *[html.Th(header) for header in results_dict.keys() if header != "Error"],
                        html.Th(),
                    ]
                )
            ]
        ),
        html.Tbody(
            [
                html.Tr(
                    [
                        html.Td(i + 1),
                        *[html.Td(value[i]) for value in dict_vals],
                        (
                            html.Td(
                                [
                                    html.Div("ⓘ"),
                                    dbc.Tooltip(
                                        [html.Span(error_msg[i])],
                                        target=f"tooltip-{i}",
                                        class_name="table-tooltip",
                                    ),
                                ],
                                id=f"tooltip-{i}",
                            )
                            if error_msg[i]
                            else html.Td()
                        ),
                    ],
                    className="not_satisfied" if error_msg[i] else "",
                )
                for i in range(len(dict_vals[0]))
            ]
        ),
    ]


def generate_settings_form() -> html.Div:
    """This function generates settings for selecting the scenario, model, and solver.

    Returns:
        html.Div: A Div containing the settings for selecting the scenario, model, and solver.
    """
    solver_options = [
        {"label": solver_type.label, "value": solver_type.value} for solver_type in SolverType
    ]

    return html.Div(
        className="settings",
        children=[
            dropdown(
                "Solver",
                "solver-type-select",
                solver_options,
            ),
            html.Label("Solver Time Limit (seconds)"),
            dcc.Input(
                id="solver-time-limit",
                type="number",
                **SOLVER_TIME,
            ),
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
                        className="display-none",
                    ),
                ],
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
        ],
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


def create_interface() -> html.Div:
    """Set the application HTML."""
    return html.Div(
        id="app-container",
        children=[
            # below are any temporary storage items, e.g., for sharing data between callbacks
            dcc.Store(id="results-table-store"),  # Results dict to update the results table
            # Banner
            html.Div(
                className="banner",
                children=[
                    html.Img(src=THUMBNAIL),
                ],
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
                                            html.H1(id="header", children=[MAIN_HEADER]),
                                            html.P(id="description", children=[DESCRIPTION]),
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
                                        value="input-tab",  # used for switching tabs programatically
                                        className="tab",
                                        children=[
                                            dcc.Loading(
                                                parent_className="input",
                                                type="circle",
                                                color=THEME_COLOR_SECONDARY,
                                                children=html.Iframe(id="map"),
                                            ),
                                        ],
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
                                                ],
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )
