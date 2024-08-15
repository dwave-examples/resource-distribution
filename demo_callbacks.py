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

from collections import defaultdict
from pathlib import Path
from typing import NamedTuple, Union

import dash
from dash import ALL, MATCH, ctx
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from demo_interface import SOLVER_TYPES, generate_table
from src.enums import SolverType
from src.resource_distribution import FormInput, get_results
from src.utils import generate_hospital_dataframe, get_empty_map


@dash.callback(
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


@dash.callback(
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


@dash.callback(
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

    return num_hospitals-1


@dash.callback(
    Output("num-neighbors", "max"),
    Output("num-neighbors", "min"),
    Output("num-neighbors", "marks"),
    Output("small-caption", "className"),
    Output("run-button", "disabled"),
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
        partition_size+1,
        {partition_size: f"{partition_size}", num_hospitals: f"{num_hospitals}"},
        "display-none" if is_valid else "",
        not is_valid,
    )


@dash.callback(
    Output({"type": "slider", "index": ALL}, "className"),
    Output("small-caption", "className", allow_duplicate=True),
    Output("run-button", "disabled", allow_duplicate=True),
    inputs=[
        Input("solver-type-select", "value"),
        State({"type": "slider", "index": ALL}, "className"),
        State("num-hospitals", "value"),
        State("partition-size", "value"),
    ],
    prevent_initial_call=True,
)
def update_settings_visibility(
    solver_type: list[int],
    sliders: list[str],
    num_hospitals: int,
    partition_size: int,
) -> tuple[list, str, bool]:
    """Hides the settings if CQM is chosen, shows the settings otherwise.

    Args:
        solver_type: Either Quantum Hybrid (CQM) (``0`` or ``SolverType.CQM``), Quantum Hybrid (BQM)
            (``1`` or ``SolverType.BQM``), Tabu (``2`` or ``SolverType.TABU``), or Simulated Annealing
            (``3`` or ``SolverType.SIM_ANNEAL``).
        sliders: A list of the current classes on each of the sliders.
        num_hospitals: The current value of the number of hospitals input.
        partition_size: The partition size value.

    Returns:
        A tuple containing all outputs to be used when updating the HTML
        template (in ``dash_html.py``). These are:

            sliders_class (list): A list of classes for the slider form fields.
            small_caption_class (str): The class name for the error caption.
            run_button_disabled (bool): Whether the run button should be disabled.
    """
    if solver_type is SolverType.CQM.value:
        return ["display-none"] * len(sliders), "display-none", False

    is_valid = num_hospitals % partition_size == 0

    return [""] * len(sliders), "display-none" if is_valid else "", not is_valid


@dash.callback(
    Output("map", "srcDoc"),
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


@dash.callback(
    # update map and results
    Output("map", "srcDoc", allow_duplicate=True),
    Output("solution-table", "children", allow_duplicate=True),
    Output("results-table-store", "data", allow_duplicate=True),
    background=True,
    inputs=[
        Input("run-button", "n_clicks"),
        State("solver-type-select", "value"),
        State("solver-time-limit", "value"),
        State("num-hospitals", "value"),
        State("partition-size", "value"),
        State("num-neighbors", "value"),
        State("distance-objective-fraction", "value"),
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
    solver_type: Union[SolverType, int],
    time_limit: float,
    num_hospitals: int,
    partition_size: int,
    num_neighbors: int,
    distance_objective_fraction: float,
    results_table_store: dict,
) -> RunOptimizationReturn:
    """Runs the optimization and updates UI accordingly.

    This is the main function which is called when the `Run Optimization` button is clicked.
    This function takes in all form values and runs the optimization, updates the run/cancel
    buttons, deactivates (and reactivates) the results tab, and updates all relevant HTML
    components.

    Args:
        run_click: The (total) number of times the run button has been clicked.
        solver_type: Either Quantum Hybrid (CQM) (``0`` or ``SolverType.CQM``), Quantum Hybrid (BQM)
            (``1`` or ``SolverType.BQM``), Tabu (``2`` or ``SolverType.TABU``), or Simulated Annealing
            (``3`` or ``SolverType.SIM_ANNEAL``).
        solver_time_limit: The solver time limit.
        num_hospitals: The number of hospitals.
        partition_size: The partition size value.
        num_neighbors: The number of neighbors.
        distance_objective_fraction: The distance objective fraction.
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

    if isinstance(solver_type, int):
        solver_type = SolverType(solver_type)

    hospital_df = generate_hospital_dataframe(num_hospitals)  # Generate hospital data

    if not results_table_store:
        results_table_store = defaultdict(list)

    results_table_store["Solver"].append(SOLVER_TYPES[solver_type])
    results_table_store["Hospitals"].append(num_hospitals)

    if solver_type is SolverType.CQM:
        form_input = FormInput(
            num_hospitals=num_hospitals,
            solver=solver_type,
            time_limit=time_limit,
        )

        results_table_store["Partition"].append("")
        results_table_store["Neighbors"].append("")
        results_table_store["DOF"].append("")
    else:
        form_input = FormInput(
            num_hospitals=num_hospitals,
            partition_size=partition_size,
            num_neighbors=num_neighbors,
            dof=distance_objective_fraction,
            solver=solver_type,
            time_limit=time_limit,
        )

        results_table_store["Partition"].append(partition_size)
        results_table_store["Neighbors"].append(num_neighbors)
        results_table_store["DOF"].append(distance_objective_fraction)

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
