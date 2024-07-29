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

import argparse
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple, Union

import dash
import dash_bootstrap_components as dbc
import diskcache
from dash import ALL, MATCH, DiskcacheManager, ctx
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app_configs import (
    APP_TITLE,
    DESCRIPTION_BQM,
    DESCRIPTION_CQM,
    MAIN_HEADER_BQM,
    MAIN_HEADER_CQM,
    THEME_COLOR,
    THEME_COLOR_SECONDARY,
)
from dash_html import SAMPLER_OPTIONS_ALL, SAMPLER_TYPES, generate_table, set_html
from src.enums import Formulation, SamplerType
from src.resource_distribution import FormInput, get_results
from src.utils import generate_hospital_dataframe, get_empty_map

cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

# Fix for Dash background callbacks crashing on macOS 10.13+ (https://bugs.python.org/issue33725)
# See https://github.com/dwave-examples/template-dash for more details.
import multiprocess

if multiprocess.get_start_method(allow_none=True) is None:
    multiprocess.set_start_method("spawn")

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    prevent_initial_callbacks="initial_duplicate",
    background_callback_manager=background_callback_manager,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
app.title = APP_TITLE

server = app.server
app.config.suppress_callback_exceptions = True

# Parse debug argument
parser = argparse.ArgumentParser(description="Dash debug setting.")
parser.add_argument(
    "--debug",
    action="store_true",
    help="Add argument to see Dash debug menu and get live reload updates while developing.",
)

args = parser.parse_args()
DEBUG = args.debug

print(f"\nDebug has been set to: {DEBUG}")
if not DEBUG:
    print(
        "The app will not show live code updates and the Dash debug menu will be hidden.",
        "If editting code while the app is running, run the app with `python app.py --debug`.\n",
        sep="\n",
    )

# Generates css file and variable using THEME_COLOR and THEME_COLOR_SECONDARY settings
css = f"""/* Automatically generated theme settings css file, see app.py */
:root {{
    --theme: {THEME_COLOR};
    --theme-secondary: {THEME_COLOR_SECONDARY};
}}
"""
with open("assets/custom_00_theme.css", "w") as f:
    f.write(css)


@app.callback(
    Output({"type": "to-collapse-class", "index": MATCH}, "className"),
    inputs=[
        Input({"type": "collapse-trigger", "index": MATCH}, "n_clicks"),
        State({"type": "to-collapse-class", "index": MATCH}, "className"),
    ],
    prevent_initial_call=True,
)
def toggle_left_column(collapse_trigger: int, to_collapse_class: str) -> str:
    """Toggles a 'collapsed' class that hides and shows some aspect of the UI.

    Args:
        collapse_trigger (int): The (total) number of times a collapse button has been clicked.
        to_collapse_class (str): Current class name of the thing to collapse, 'collapsed' if not visible, empty string if visible

    Returns:
        str: The new class name of the thing to collapse.
    """

    classes = to_collapse_class.split(" ") if to_collapse_class else []
    if "collapsed" in classes:
        classes.remove("collapsed")
        return " ".join(classes)
    return to_collapse_class + " collapsed" if to_collapse_class else "collapsed"


@app.callback(
    Output("num-hospitals", "min"),
    inputs=[
        Input("partition-size", "value"),
    ],
)
def update_num_hospitals(partition_size: int) -> int:
    """Ensures the number of hospitals can never be lower than the partition size.

    Args:
        partition_size: The partition size value.

    Returns:
        num-hospitals: The minimum value for the number of hospitals input.
    """

    return partition_size


@app.callback(
    Output("partition-size", "max"),
    inputs=[
        Input("num-hospitals", "value"),
    ],
)
def update_partition_size(num_hospitals: int) -> int:
    """Ensures the partition size can never be greater than the number of hospitals.

    Args:
        num_hospitals: The current value of the number of hospitals input.

    Returns:
        partition-size: The maximum value of partition size slider.
    """

    return num_hospitals


@app.callback(
    Output("num-neighbors", "max"),
    Output("num-neighbors", "min"),
    Output("num-neighbors", "marks"),
    Output("small-caption", "className", allow_duplicate=True),
    Output("run-button", "disabled", allow_duplicate=True),
    inputs=[
        Input("num-hospitals", "value"),
        Input("partition-size", "value"),
    ],
)
def update_num_neighbors(num_hospitals: int, partition_size: int) -> int:
    """The number of neighbors must be greater than or equal to the partition
        size and less than or equal to the number of hospitals.

        Also checks whether the partition size is a factor of num hospitals and shows a warning if not.

    Args:
        num_hospitals: The current value of the number of hospitals input.
        partition_size: The partition size value.

    Returns:
        num-neighbors-max: The maximum for the number of neighbors slider.
        num-neighbors-min: The minimum for the number of neighbors slider.
        num-neighbors-marks: The marks for the number of neighbors slider.
        small-caption-classname: The class name for the error caption.
        run-button-disabled: Whether the run button should be disabled.
    """
    is_valid = num_hospitals % partition_size == 0

    return (
        num_hospitals,
        partition_size,
        {partition_size: f"{partition_size}", num_hospitals: f"{num_hospitals}"},
        "display-none" if is_valid else "",
        not is_valid,
    )


class UpdateSelectedFormulationReturn(NamedTuple):
    """Return type for the ``update_selected_formulation`` callback function."""

    formulation_options_class: list = dash.no_update
    sliders_class: list = dash.no_update
    main_header: str = dash.no_update
    description: str = dash.no_update
    selected_formulation: int = dash.no_update
    last_formulation: int = dash.no_update
    sampler_select_options: list = dash.no_update
    sampler_select_value: int = dash.no_update
    results_tab_disabled: bool = dash.no_update
    selected_tab: str = dash.no_update
    solution_table: list = dash.no_update
    small_caption_class: str = dash.no_update
    run_button_disabled: bool = dash.no_update
    results_table_store: dict = dash.no_update


@app.callback(
    Output({"type": "formulation-option", "index": ALL}, "className"),
    Output({"type": "slider", "index": ALL}, "className"),
    Output("header", "children"),
    Output("description", "children"),
    Output("selected-formulation", "data"),
    Output("last-formulation", "data"),
    Output("sampler-type-select", "options"),
    Output("sampler-type-select", "value"),
    Output("results-tab", "disabled"),
    Output("tabs", "value"),
    Output("solution-table", "children"),
    Output("small-caption", "className"),
    Output("run-button", "disabled"),
    Output("results-table-store", "data"),
    inputs=[
        Input({"type": "formulation-option", "index": ALL}, "n_clicks"),
        State({"type": "slider", "index": ALL}, "className"),
        State("last-formulation", "data"),
        State("num-hospitals", "value"),
        State("partition-size", "value"),
    ],
)
def update_selected_formulation(
    formulation_options: list[int],
    sliders: list[str],
    last_formulation: int,
    num_hospitals: int,
    partition_size: int,
) -> UpdateSelectedFormulationReturn:
    """Updates the formulation that is selected (BQM or CQM), hides/shows settings accordingly,
        and updates the navigation options to indicate the currently active formulation option.

    Args:
        formulation_options: A list containing the number of times each formulation option has been clicked.
        sliders: A list of the current classes on each of the sliders.
        last_formulation: The previous formulation that was selected, either BQM (``0`` or ``Formulation.BQM``) or CQM (``1`` or ``Formulation.CQM``).
        num_hospitals: The current value of the number of hospitals input.
        partition_size: The partition size value.

    Returns: A NamedTuple (UpdateSelectedFormulationReturn) containing all outputs to be used when updating the HTML
        template (in ``dash_html.py``). These are:

            formulation_options_class (list): A list of classes for the formulation navigation options in the header.
            sliders_class (list): A list of classes for the slider form fields.
            main_header (str): The title of the app.
            description (str): The description of the app.
            selected_formulation (int): Either BQM (``0`` or ``Formulation.BQM``) or CQM (``1`` or ``Formulation.CQM``).
            last_formulation (int): The previous formulation that was selected, either BQM (``0`` or ``Formulation.BQM``) or CQM (``1`` or ``Formulation.CQM``).
            sampler_select_options (list): A list of sampler options to include in the sampler select dropdown.
            sampler_select_value (int): The new value of the sampler select dropdown.
            results_tab_disabled (bool): Whether the results tab should be disabled.
            selected_tab (str): The tab to select.
            solution_table (list): The new solution table to set.
            small_caption_class (str): The class name for the error caption.
            run_button_disabled (bool): Whether the run button should be disabled.
            results_table_store (dict): Dict of lists of results for each run.
    """
    nav_class_names = [""] * len(formulation_options)

    # Clicked the button that was already selected
    if ctx.triggered_id and last_formulation == ctx.triggered_id["index"]:
        raise PreventUpdate

    # Either first load or BQM was selected
    if not ctx.triggered_id or ctx.triggered_id["index"] is Formulation.BQM.value:
        nav_class_names[Formulation.BQM.value] = "active"
        sampler_options_bqm = [
            option for option in SAMPLER_OPTIONS_ALL if option["value"] is not SamplerType.CQM.value
        ]
        is_valid = num_hospitals % partition_size == 0

        return UpdateSelectedFormulationReturn(
            formulation_options_class=nav_class_names,
            sliders_class=[""] * len(sliders),
            main_header=MAIN_HEADER_BQM,
            description=DESCRIPTION_BQM,
            selected_formulation=Formulation.BQM.value,
            last_formulation=Formulation.BQM.value,
            sampler_select_options=sampler_options_bqm,
            sampler_select_value=sampler_options_bqm[0]["value"],
            results_tab_disabled=True,
            selected_tab="input-tab",
            solution_table=[],
            small_caption_class="display-none" if is_valid else "",
            run_button_disabled=not is_valid,
            results_table_store={},
        )

    # CQM was selected
    nav_class_names[Formulation.CQM.value] = "active"
    return UpdateSelectedFormulationReturn(
        formulation_options_class=nav_class_names,
        sliders_class=["display-none"] * len(sliders),
        main_header=MAIN_HEADER_CQM,
        description=DESCRIPTION_CQM,
        selected_formulation=Formulation.CQM.value,
        last_formulation=Formulation.CQM.value,
        sampler_select_options=SAMPLER_OPTIONS_ALL,
        sampler_select_value=SAMPLER_OPTIONS_ALL[0]["value"],
        results_tab_disabled=True,
        selected_tab="input-tab",
        solution_table=[],
        small_caption_class="display-none",
        run_button_disabled=False,
        results_table_store={},
    )


@app.callback(
    Output("map", "srcDoc", allow_duplicate=True),
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

    # Only regenerate map if run buttons is NOT clicked (ie num_hospitals has been changed or first load)
    if ctx.triggered_id != "run-button" or not map_path.exists():
        # Generate hospital data
        hospital_df = generate_hospital_dataframe(num_hospitals)

        # Initialize map
        initial_map = get_empty_map(hospital_df)
        initial_map.save(map_path)

    return open(map_path, "r").read()


class RunOptimizationReturn(NamedTuple):
    """Return type for the ``run_optimization`` callback function."""

    solution_map: str = dash.no_update
    solution_table: str = dash.no_update
    results_table_store: defaultdict = dash.no_update


@app.long_callback(
    # update map and results
    Output("map", "srcDoc", allow_duplicate=True),
    Output("solution-table", "children", allow_duplicate=True),
    Output("results-table-store", "data", allow_duplicate=True),
    inputs=[
        Input("run-button", "n_clicks"),
        State("sampler-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-hospitals", "value"),
        State("partition-size", "value"),
        State("num-neighbors", "value"),
        State("distance-objective-fraction", "value"),
        State("selected-formulation", "data"),
        State("results-table-store", "data"),
    ],
    running=[
        # Shows cancel button while running.
        (Output("cancel-button", "className"), "", "display-none"),
        (Output("run-button", "className"), "display-none", ""),  # Hides run button while running.
        (Output("results-tab", "disabled"), True, False),  # Disables results tab while running.
        (Output("results-tab", "label"), "Loading...", "Results"),
        (Output("tabs", "value"), "input-tab", "input-tab"),  # Switch to input tab while running.
    ],
    cancel=[Input("cancel-button", "n_clicks")],
    prevent_initial_call=True,
)
def run_optimiation(
    run_click: int,
    sampler_type: Union[SamplerType, int],
    time_limit: float,
    num_hospitals: int,
    partition_size: int,
    num_neighbors: int,
    distance_objective_fraction: float,
    selected_formulation: Union[Formulation, int],
    results_table_store: dict,
) -> RunOptimizationReturn:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the `Run Optimization` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        sampler_type: Either Quantum Hybrid (CQM) (``0`` or ``SamplerType.CQM``), Quantum Hybrid (BQM)
            (``1`` or ``SamplerType.BQM``), Tabu (``2`` or ``SamplerType.TABU``), or Simulated Annealing
            (``3`` or ``SamplerType.SIM_ANNEAL``).
        solver_time_limit: The solver time limit.
        num_hospitals: The number of hospitals.
        partition_size: The partition size value.
        num_neighbors: The number of neighbors.
        distance_objective_fraction: The distance objective fraction.
        selected_formulation: Either BQM (``0`` or ``Formulation.BQM``) or CQM (``1`` or ``Formulation.CQM``).
        results_table_store: Dict of lists of results for each run.

    Returns:
        A NamedTuple (RunOptimizationReturn) containing all outputs to be used when updating the HTML
        template (in ``dash_html.py``). These are:

            map (str): Updates the 'srcDoc' entry for the 'map' Iframe in the map tab.
            solution_table (list): The new solution table to set.
            results_table_store (defaultdict[list]): Dict of lists of results for each run.
    """
    if run_click == 0 or ctx.triggered_id != "run-button":
        raise PreventUpdate

    if isinstance(sampler_type, int):
        sampler_type = SamplerType(sampler_type)

    if isinstance(selected_formulation, int):
        selected_formulation = Formulation(selected_formulation)

    hospital_df = generate_hospital_dataframe(num_hospitals)  # Generate hospital data

    if not results_table_store:
        results_table_store = defaultdict(list)

    results_table_store["Solver"].append(SAMPLER_TYPES[sampler_type])
    results_table_store["Hospitals"].append(num_hospitals)

    if selected_formulation is Formulation.BQM:
        form_input = FormInput(
            formulation=selected_formulation,
            num_hospitals=num_hospitals,
            partition_size=partition_size,
            num_neighbors=num_neighbors,
            dof=distance_objective_fraction,
            solver=sampler_type,
            time_limit=time_limit,
        )

        results_table_store["Partition"].append(partition_size)
        results_table_store["Neighbors"].append(num_neighbors)
        results_table_store["DOF"].append(distance_objective_fraction)
    else:
        form_input = FormInput(
            formulation=selected_formulation,
            num_hospitals=num_hospitals,
            solver=sampler_type,
            time_limit=time_limit,
        )

    folium_map = get_empty_map(hospital_df)
    result = get_results(form_input, hospital_df, folium_map)

    if not result:
        raise ValueError("Something went wrong while solving problem. Refresh and try again.")

    if not result.total_transfer:
        results_table_store["Transfer"].append("---")
        results_table_store["Cost"].append("---")
        results_table_store["Energy"].append("---")
        results_table_store["Run Time"].append("---")
        results_table_store["Error"].append("No solution found")
        return RunOptimizationReturn(results_table_store=results_table_store)

    results_table_store["Transfer"].append(str(round(result.total_transfer, 2)))
    results_table_store["Cost"].append(str(round(result.total_cost, 2)))
    results_table_store["Energy"].append(str(round(result.energy, 2)))
    results_table_store["Run Time"].append(str(round(result.run_time, 2)))
    results_table_store["Error"].append(result.error_msgs)

    result.figure.save("solution_map.html")

    return RunOptimizationReturn(
        solution_map=open("solution_map.html", "r").read(),
        solution_table=generate_table(results_table_store),
        results_table_store=results_table_store,
    )


# Imports the Dash HTML code and sets it in the app.
# Creates the visual layout and app (see `dash_html.py`)
set_html(app)

# Run the server
if __name__ == "__main__":
    app.run_server(debug=DEBUG)
