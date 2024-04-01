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
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Union

import dash
import diskcache
import folium
from dash import DiskcacheManager, callback_context, ctx, ALL, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from resource_distribution import FormInput, get_results
from page_utils import persisted

from utils import us_hospitals, get_empty_map

from dash_html import create_table, update_table, create_warning, set_html

# from solver.solver import RoutingProblemParameters, SamplerType, Solver, VehicleType

cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

from app_configs import APP_TITLE

if TYPE_CHECKING:
    from dash import html

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    prevent_initial_callbacks="initial_duplicate",
    background_callback_manager=background_callback_manager,
    use_pages=True,
)
app.title = APP_TITLE

server = app.server
app.config.suppress_callback_exceptions = True

BASE_PATH = Path(__file__).parent.resolve()
DATA_PATH = BASE_PATH.joinpath("input").resolve()


@app.callback(
    Output({"class": "nav-links", "path": ALL}, "className"),
    inputs=[
        Input("url", "pathname"),
        Input({"class": "nav-links", "path": ALL}, "id")
    ]
)
def intialize_nav(pathname, nav_links):
    return ["active" if link["path"] == pathname else "" for link in nav_links]


@app.callback(
    Output("left-column", "className"),
    inputs=[
        Input("left-column-collapse", "n_clicks"),
        State("left-column", "className"),
    ],
    prevent_initial_call=True,
)
def toggle_left_column(left_column, class_name):
    if class_name:
        return ""
    return "collapsed"


def generate_inital_map(num_hospitals: int) -> folium.Map:
    """Generates the initial map.

    Args:
        num_hospitals (int): Number of hospitals.

    Returns:
        folium.Map: Initial map shown on the map tab.
    """
    # Generate hospital data
    hospital_df = us_hospitals(num_hospitals)

    # Initialize map
    initial_map = get_empty_map(hospital_df)

    return initial_map


@app.callback(
    Output("solution-map", "srcDoc", allow_duplicate=True),
    inputs=[
        Input("num-hospitals", "value"),
        Input("run-button", "n_clicks"),
    ],
)
def render_initial_map(num_hospitals: int, _) -> str:
    """Generates and saves and HTML version of the initial map.

    Note that 'run-button' is required as an Input to reload the map each time
    a run is started. This resets the solution map to the initial map but does
    NOT regenerate the initial map unless 'num-hospitals' is changed.

    Args:
        num_hospitals: Number of hospitals.

    Returns:
        str: Initial map shown on the map tab as HTML.
    """
    map_path = Path("initial_map.html")

    # only regenerate map if num_hospitals is changed (i.e., if run buttons is NOT clicked)
    if ctx.triggered_id != "run-button" or not map_path.exists():
        initial_map = generate_inital_map(num_hospitals)
        initial_map.save(map_path)

    return open(map_path, "r").read()


@app.callback(
    Output("solution-table", "children"),
    inputs=[
        Input("run-in-progress", "data"),
        State("stored-results", "data"),
        State("reset-results", "data"),
        State("sampler-type", "data"),
    ],
    prevent_initial_call=True,
)
def update_tables(
    run_in_progress, stored_results, reset_results, sampler_type
) -> list:
    """Update the results tables each time a run is made.

    Args:
        run_in_progress: Whether or not the ``run_optimiation`` callback is running.
        stored_results: The results tab from the latest run.
        reset_results: Whether or not to reset the results tables before applying the new one.
        sampler_type: The sampler type used in the latest run (``"quantum"`` or ``"classical"``)

    Returns:
        tuple: A tuple containing the two results tables.
    """
    empty_or_no_update = [] if reset_results else dash.no_update

    if run_in_progress is True:
        raise PreventUpdate

    # if sampler_type == "classical":
    #     return empty_or_no_update, stored_results

    return stored_results



def validate_input(num_hospitals: int, partition_size: int, num_neighbors: int) -> list[str]:
    """Validate form input from user."""

    warnings = []

    if num_hospitals <= partition_size:
        warnings.append("The number of hospitals must be greater than the partition size.")
    if num_hospitals % partition_size != 0:
        warnings.append("The number of hospitals must be divisible by the partition size.")
    if num_neighbors < partition_size:
        warnings.append("The number of neighbors must be greater than or equal to the partition size.")
    if num_neighbors > num_hospitals:
        warnings.append("The number of neighbors must be less than or equal to the number of hospitals.")

    return warnings



@app.long_callback(
    # update map and results
    Output("solution-map", "srcDoc", allow_duplicate=True),
    Output("stored-results", "data", allow_duplicate=True),
    # store the solver used, whether or not to reset results tabs and the
    # parameter hash value used to detect parameter changes
    Output("sampler-type", "data", allow_duplicate=True),
    # Output("reset-results", "data"),
    # Output("parameter-hash", "data"),
    Output("warning", "children", allow_duplicate=True),
    inputs=[
        Input("run-button", "n_clicks"),
        State("url", "pathname"),
        State("sampler-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-hospitals", "value"),
        State("partition-size", "value"),
        State("num-neighbors", "value"),
        State("distance-objective-fraction", "value"),
        # input and output result table (to update it dynamically)
        State("solution-table", "children"),
        # State("parameter-hash", "data"),
    ],
    running=[
        # show cancel button and disable run button, and disable and animate results tab
        (Output("cancel-button", "style"), {"display": "inline-block"}, {"display": "none"}),
        (Output("run-button", "style"), {"display": "none"}, {"display": "inline-block"}),
        (Output("results-tab", "disabled"), True, False),
        (Output("results-tab", "className"), "tab-loading", "tab"),
        # switch to map tab while running
        (Output("tabs", "value"), "map-tab", "map-tab"),
        # block certain callbacks from running until this is done
        (Output("run-in-progress", "data"), True, False),
        (Output("warning", "style"), {"display": "none"}, {"display": "block"}),
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    prevent_initial_call=True,
)
def run_optimiation(
    run_click: int,
    pathname: str,
    sampler_type: str,
    time_limit: float,
    num_hospitals: int,
    partition_size: int,
    num_neighbors: int,
    distance_objective_fraction: int,
    results_table: list[html.Thead, html.Tbody],
    # previous_parameter_hash: str,
) -> tuple[str, list[html.Thead, html.Tbody], str, int, int, str]:
    """Run the optimization and update map and results tables.

    This is the main optimization function which is called when the Run optimization button is
    clicked. It uses all inputs from the drop-down lists, sliders and text entries and runs the
    optimization, updates the run/cancel buttons, animates (and disables) the results tab,
    moves focus to the map tab and updates all relevant HTML entries.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        sampler_type: A string stating the sampler type as in SAMPLER_TYPES_CQM or SAMPLER_TYPES_BQM.
        time_limit: The solver time limit.
        num_hospitals: The number of hospitals.
        partition_size: The partition size.
        num_neighbors: The number of neighbors.
        distance_objective_fraction: The distance objective fraction.
        results_table: The html 'Solution cost' table. Used to update it dynamically.

    Returns:
        A tuple containing all outputs to be used when updating the HTML template (in
        ``dash_html,py``). These are:

            solution-map: Updates the 'srcDoc' entry for the 'solution-map' IFrame in the map tab.
                This is the map (initial and solution map).
            stored-results: Stores the Solution cost table in the results tab.
            sampler-type: The sampler used (``"quantum"`` or ``"classical"``).
            reset-results: Whether or not to reset the results tables before applying the new one.
            parameter-hash: Hash string to detect changed parameters.
    """
    if run_click == 0 or ctx.triggered_id != "run-button":
        return ""

    warning = ""
    page = pathname[1:]

    if page == "bqm":
        validate_warnings = validate_input(num_hospitals, partition_size, num_neighbors)
        if validate_warnings:
            warning = create_warning(validate_warnings)

            return (
                no_update,
                no_update,
                no_update,
                warning
            )

    if ctx.triggered_id == "run-button":
        # Generate hospital data
        hospital_df = us_hospitals(num_hospitals)

        if page == "bqm":
            form_input = FormInput(
                page=page,
                num_hospitals=num_hospitals,
                partition_size=partition_size,
                num_neighbors=num_neighbors,
                dof=distance_objective_fraction,
                solver=sampler_type,
                time_limit=time_limit,
            )
        else:
            form_input = FormInput(
                page=page,
                num_hospitals=num_hospitals,
                solver=sampler_type,
                time_limit=time_limit,
            )

        folium_map = get_empty_map(hospital_df)
        results_dict = persisted('bqm-results')

        result = get_results(form_input, hospital_df, folium_map)

        constraints_satisfied = False

        if result is None:
            raise ValueError("Something went wrong while solving problem. Refresh and try again.")
        elif result.total_transfer == 0:
            warning = create_warning(["No solution found."])
            return (
                no_update,
                no_update,
                no_update,
                warning
            )
        else:
            results_dict['Hospitals'].append(form_input.num_hospitals)

            if page == "bqm":
                results_dict['Partition Size'].append(form_input.partition_size)
                results_dict['Neighbors'].append(form_input.num_neighbors)
                results_dict['DOF'].append(form_input.dof)

            results_dict['Solver'].append(form_input.solver)

            if not result.error_msgs:
                results_dict['Constraints'].append("Satisfied")
            else:
                warning = create_warning(result.error_msgs)
                results_dict['Constraints'].append("Not Satisfied")

            results_dict['Transfer'].append(str(round(result.total_transfer, 2)))
            results_dict['Cost'].append(str(round(result.total_cost, 2)))
            results_dict['Energy'].append(str(round(result.energy, 2)))
            results_dict['Run Time'].append(str(round(result.run_time, 2)))

            if results_dict:
                try:
                    if results_table:
                        results_table = update_table(results_table, results_dict)
                    else:
                        results_table = create_table(results_dict)
                except Exception as e:
                    # Something wrong with cached dictionary -> reset and give warning
                    results_dict.clear()
                    warning = create_warning(["Something went wrong. Clear results and try again please."])
                    print(e)
                    return (
                        no_update,
                        no_update,
                        no_update,
                        warning
                    )

            result.figure.save("solution_map.html")

            # parameter_hash = _get_parameter_hash(**callback_context.states)
            # if parameter_hash != previous_parameter_hash:
            #     reset_results = True
            # else:
            #     reset_results = False

            return (
                open("solution_map.html", "r").read(),
                results_table,
                sampler_type,
                # reset_results,
                # str(parameter_hash),
                # num_hospitals,
                # num_neighbors,
                warning
            )

    raise PreventUpdate


# def _get_parameter_hash(**states) -> str:
#     """Calculate a hash string for parameters which reset the results tables."""
#     # list of parameter values that will reset the results tables
#     # when changed in the app; must be hashable
#     items = [
#         "vehicle-type-select.value",
#         "num-vehicles-select.value",
#         "num-clients-select.value",
#         "solver-time-limit.value",
#     ]
#     try:
#         return str(hash(itemgetter(*items)(states)))
#     except TypeError as e:
#         raise TypeError("unhashable problem parameter value") from e


# import the html code and sets it in the app
# creates the visual layout and app (see `dash_html.py`)
set_html(app)

# Run the server
if __name__ == "__main__":
    app.run_server(debug=True)
