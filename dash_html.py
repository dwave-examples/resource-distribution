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

from dash import dcc, html, page_registry, page_container

from app_configs import THUMBNAIL
from src.enums import SamplerType

SAMPLER_TYPES = {
    SamplerType.CQM: "Quantum Hybrid (CQM)",
    SamplerType.BQM: "Quantum Hybrid (BQM)",
    SamplerType.TABU: "Tabu",
    SamplerType.SIM_ANNEAL: "Simulated Annealing",
}

def set_html(app):
    """Set the application HTML."""
    app.layout = html.Div(
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
            dcc.Location(id="url"),
            # Banner
            html.Div(
                className="banner",
                children=[
                    html.Img(src=THUMBNAIL),
                    html.Div([
                        html.Div(
                            dcc.Link(
                                page["name"],
                                href=page["relative_path"],
                                id={
                                    "class": "nav-links",
                                    "path": page["path"]
                                },
                            )
                        ) for page in page_registry.values()
                    ]),
                ]
            ),
            page_container
        ],
    )

def create_table(
    values_dicts: defaultdict
) -> list[html.Thead, html.Tbody]:
    """Create a row in the table dynamically.

    Args:
        values_dicts: List of dictionaries with vehicle number as results data as values.
        values_tot: List of total results data (sum of individual vehicle data).
    """

    table = [
        html.Thead([html.Tr([html.Th(header) for header in values_dicts.keys()])]),
        html.Tbody([html.Tr([html.Td(value) for value in values_dicts.values()])])
    ]

    return table

def update_table(
    prev_table: list[html.Thead, html.Tbody], values_dicts: defaultdict
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
                html.Tr([html.Td(value) for value in values_dicts.values()])
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
