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
from enum import EnumMeta

import dash_mantine_components as dmc
from dash import dcc, html

from demo_configs import (
    DESCRIPTION,
    DISTANCE_OBJECTIVE_FRACTION,
    MAIN_HEADER,
    NUM_HOSPITALS,
    NUM_NEIGHBORS,
    PARTITION_SIZE,
    SOLVER_TIME,
    THUMBNAIL,
)
from src.demo_enums import SolverType

THEME_COLOR = "#2d4376"


def slider(label: str, id: str, config: dict) -> html.Div:
    """Slider element for value selection.

    Args:
        label: The title that goes above the slider.
        id: A unique selector for this element.
        config: A dictionary of slider configurations, see dmc.Slider Dash Mantine docs.
    """
    return html.Div(
        className="slider-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            dmc.Slider(
                id=id,
                className="slider",
                **config,
                marks=[
                    {"value": config["min"], "label": f'{config["min"]}'},
                    {"value": config["max"], "label": f'{config["max"]}'},
                ],
                labelAlwaysOn=True,
                thumbLabel=f"{label} slider",
                color=THEME_COLOR,
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
            html.Label(label, htmlFor=id),
            dmc.Select(
                id=id,
                data=options,
                value=options[0]["value"],
                allowDeselect=False,
            ),
        ],
    )


def input(label: str, id: str, configs: dict, type: str = "number") -> html.Div:
    """Input element for either text or number input.

    Args:
        label: The title that goes above the input.
        id: A unique selector for this element.
        configs: A dictionary of configurations for the input element.
        type: The type of input, either "number" or "text".
    """
    return html.Div(
        className="input-wrapper",
        children=[
            html.Label(label, htmlFor=id),
            (
                dmc.TextInput(
                    id=id,
                    **configs,
                )
                if type == "text"
                else dmc.NumberInput(
                    id=id,
                    **configs,
                )
            ),
        ],
    )


def tooltip(content: list, target: str, class_name: str = "") -> dmc.Tooltip:
    """Generates tooltip.

    Args:
        content: The content that should show in the tooltip.
        target: The target id for the tooltip.
        class_name: Optional class name for the tooltip.

    Returns:
        A Dash Mantine components tooltip.
    """

    return dmc.Tooltip(
        label=content,
        target=f"#{target}",
        multiline=True,
        w=250,
        color="#202239",
        withArrow=True,
        arrowSize=10,
        offset=2,
        transitionProps={"transition": "pop", "duration": 200, "timingFunction": "ease"},
        className=f"table-tooltip {class_name}",
    )


def generate_table(results_dict: defaultdict) -> list[html.Thead, html.Tbody]:
    """Generates solution table.

    Args:
        results_dict: Dictionary of lists of results values from all previous runs.

    Returns:
        The table head and table body of the results table.
    """
    table_columns_dict = results_dict.copy()
    error_msg = table_columns_dict.pop("Error")
    settings = table_columns_dict.pop("Settings")
    num_rows = len(settings)
    rows = []

    for i in range(num_rows):
        cells = []

        for key, value in table_columns_dict.items():
            cell = [value[i]]

            if key == "Missing Beds" and error_msg[i]:
                cell.append(
                    html.Div(
                        [html.Div("ⓘ"), tooltip([html.Span(error_msg[i])], f"tooltip-error-{i}")],
                        id=f"tooltip-error-{i}",
                    )
                )

            elif key == "Hospitals" and settings[i]:
                content = [html.Div([f"{key}: {value}"]) for key, value in settings[i].items()]

                cell = [
                    html.Div(
                        [value[i], tooltip(content, f"tooltip-settings-{i}", "tooltip-settings")],
                        id=f"tooltip-settings-{i}",
                    )
                ]

            cells.append(html.Td(cell))

        rows.append(html.Tr([html.Td(i + 1), *cells]))

    return [
        html.Thead(
            [
                html.Tr(
                    [
                        html.Th("Run"),
                        *[html.Th(header) for header in table_columns_dict.keys()],
                    ]
                )
            ]
        ),
        html.Tbody(rows),
    ]


def generate_options(options: list | EnumMeta | dict) -> list[dict]:
    """Format options for dropdowns, checklists, radios, etc.

    Args:
        options: A list, EnumMeta, or dictionary of options to format.

    Returns:
        A list of dictionaries with "label" and "value" keys for each option.
    """
    if isinstance(options, EnumMeta):
        return [{"label": option.label, "value": f"{option.value}"} for option in options]

    if isinstance(options, dict):
        return [{"label": f"{key}", "value": f"{value}"} for key, value in options.items()]

    return [{"label": f"{option}", "value": f"{option}"} for option in options]


def generate_settings_form() -> html.Div:
    """This function generates settings for selecting the scenario, model, and solver.

    Returns:
        A Div containing the settings for selecting the scenario, model, and solver.
    """
    solver_options = generate_options(SolverType)

    return html.Div(
        className="settings",
        children=[
            dropdown(
                "Solver",
                "solver-type-select",
                solver_options,
            ),
            input(
                "Solver Time Limit (seconds)",
                "solver-time-limit",
                SOLVER_TIME,
            ),
            html.Div(
                className="caption-wrapper",
                children=[
                    html.Div(
                        [
                            input(
                                "Number of Hospitals",
                                "num-hospitals",
                                NUM_HOSPITALS,
                            ),
                        ]
                    ),
                    html.P(
                        html.Small("Number of hospitals must be divisible by partition size."),
                        id="small-caption",
                        className="display-none",
                    ),
                ],
            ),
            html.Div(
                [
                    slider(
                        "Partition Size",
                        "partition-size",
                        PARTITION_SIZE,
                    ),
                    slider(
                        "Number of Neighbors",
                        "num-neighbors",
                        NUM_NEIGHBORS,
                    ),
                    slider(
                        "Distance Objective Fraction",
                        "distance-objective-fraction",
                        DISTANCE_OBJECTIVE_FRACTION,
                    ),
                ],
                id="bqm-settings",
                className="display-none",
            ),
        ],
    )


def generate_run_buttons() -> html.Div:
    """Generate run and cancel buttons to run the optimization."""
    return html.Div(
        id="button-group",
        children=[
            html.Button("Run Optimization", id="run-button", className="button"),
            html.Button(
                "Cancel Optimization",
                id="cancel-button",
                className="button",
                style={"display": "none"},
            ),
        ],
    )


def create_interface() -> html.Div:
    """Create the main application interface."""
    return html.Div(
        id="app-container",
        children=[
            html.A(  # Skip link for accessibility
                "Skip to main content",
                href="#main-content",
                id="skip-to-main",
                className="skip-link",
                tabIndex=1,
            ),
            # below are any temporary storage items, e.g., for sharing data between callbacks
            dcc.Store(id="results-table-store"),  # Results dict to update the results table
            # Settings and results columns
            html.Main(
                className="columns-main",
                id="main-content",
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
                                                [
                                                    html.H1(MAIN_HEADER),
                                                    html.P(DESCRIPTION),
                                                ],
                                                className="title-section",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        html.Div(
                                                            [
                                                                generate_settings_form(),
                                                                generate_run_buttons(),
                                                            ],
                                                            className="settings-and-buttons",
                                                        ),
                                                        className="settings-and-buttons-wrapper",
                                                    ),
                                                    # Left column collapse button
                                                    html.Div(
                                                        html.Button(
                                                            id={
                                                                "type": "collapse-trigger",
                                                                "index": 0,
                                                            },
                                                            className="left-column-collapse",
                                                            title="Collapse sidebar",
                                                            children=[
                                                                html.Div(className="collapse-arrow")
                                                            ],
                                                            **{"aria-expanded": "true"},
                                                        ),
                                                    ),
                                                ],
                                                className="form-section",
                                            ),
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Right column
                    html.Div(
                        className="right-column",
                        children=[
                            dmc.Tabs(
                                id="tabs",
                                value="input-tab",
                                color="white",
                                children=[
                                    html.Header(
                                        className="banner",
                                        children=[
                                            html.Nav(
                                                [
                                                    dmc.TabsList(
                                                        [
                                                            dmc.TabsTab("Map", value="input-tab"),
                                                            dmc.TabsTab(
                                                                "Results",
                                                                value="results-tab",
                                                                id="results-tab",
                                                                disabled=True,
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            ),
                                            html.Img(src=THUMBNAIL, alt="D-Wave logo"),
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="input-tab",
                                        tabIndex="12",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper",
                                                children=[
                                                    dcc.Loading(
                                                        parent_className="input",
                                                        type="circle",
                                                        color=THEME_COLOR,
                                                        children=html.Iframe(id="map"),
                                                    ),
                                                ],
                                            )
                                        ],
                                    ),
                                    dmc.TabsPanel(
                                        value="results-tab",
                                        tabIndex="13",
                                        children=[
                                            html.Div(
                                                className="tab-content-wrapper tab-content-results",
                                                children=[
                                                    html.Table(
                                                        id="solution-table",
                                                        className="result-table",
                                                        # add children dynamically using 'generate_table'
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
