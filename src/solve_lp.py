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

from itertools import product
from typing import List, Tuple, Union

import numpy as np
from pulp import LpBinary, LpMinimize, LpProblem, LpStatus, LpVariable, lpSum

Points = Union[List[Tuple[float, float]], np.ndarray]


def haversine(point_1, point_2):
    """Calculate the great circle distance between two points on earth
    (specified in decimal degrees).

    Args:
        point_1 (tuple(float, float))
        point_2 (tuple(float, float))

    Returns:
        float: The haversine distance.
    """
    longitude1, latitude1 = point_1
    longitude2, latitude2 = point_2
    # convert decimal degrees to radians
    longitude1, latitude1, longitude2, latitude2 = np.radians(
        [longitude1, latitude1, longitude2, latitude2]
    )

    # haversine formula
    dlon = longitude2 - longitude1
    dlat = latitude2 - latitude1
    a = np.sin(dlat / 2) ** 2 + np.cos(latitude1) * np.cos(latitude2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def distance_matrix_haversine(X: Points):
    """Compute the haversine distance of a list of points.

    Args:
        X: List of tuples or 2-d array of floats (Mx2).

    Returns:
        Matrix (MxM) of distances.
    """
    M = X.shape[0]
    N = X.shape[1]
    if N != 2:
        raise ValueError
    D = np.zeros((M, M), dtype=np.float32)
    for i in range(M):
        for j in range(M):
            d = haversine(X[i], X[j])
            D[i, j] = np.sqrt(d)
    return D


def lp_problem(points: Points, signed_shortage, transfer, verbose=False):
    """Form and solve the LP problem within each cluster of cities/hospitals.

    Args:
        points (list):
            List of tuples of (longitude, latitude) coordinates.

        signed_shortage (int):
            The amount of shortage for each location (negative values are shortages,
            positive values are surpluses).

        transfer (float):
            The amount of transfer we aim to achieve within each group of points. The
            problem is the optimization of cost subject to having at least this amount
            of transfer.

        verbose (boolean):
            Whether to print out some partial information.

    Returns:
        The solution, optimal cost, status, optimal transfer.

    """
    index_surplus = signed_shortage > 0
    index_shortage = signed_shortage < 0

    location_surplus = points[index_surplus]
    location_shortage = points[index_shortage]

    surplus = signed_shortage[index_surplus]
    shortage = signed_shortage[index_shortage]
    num_surplus = len(surplus)
    num_shortage = len(shortage)
    if num_surplus == 0 or num_shortage == 0:
        return [], 0, "Optimal", 0

    prob = LpProblem("Transfer_cost", LpMinimize)
    data = {}
    iix = 0
    for (idx, (xyp, sp)), (jdx, (xyn, sn)) in product(
        enumerate(zip(location_surplus, surplus)), enumerate(zip(location_shortage, shortage))
    ):
        distance = np.sqrt(haversine(xyp, xyn))
        t = np.min([sp, -sn])
        data[(idx, jdx)] = [
            LpVariable("x_{}".format(iix), cat=LpBinary),
            distance,
            t,  # 2
            sp,  # 3
            -sn,  # 4
        ]
        iix += 1

    prob += lpSum(
        [data[(i, j)][1] * data[(i, j)][0] for i in range(num_surplus) for j in range(num_shortage)]
    )
    prob += (
        lpSum(
            [
                data[(i, j)][2] * data[(i, j)][0]
                for i in range(num_surplus)
                for j in range(num_shortage)
            ]
        )
        >= transfer
    )
    for i in range(num_surplus):
        prob += (
            lpSum([data[(i, j)][2] * data[(i, j)][0] for j in range(num_shortage)])
            <= data[(i, 0)][3]
        )
    for j in range(num_shortage):
        prob += (
            lpSum([data[(i, j)][2] * data[(i, j)][0] for i in range(num_surplus)])
            <= data[(0, j)][4]
        )

    status = prob.solve()
    status = LpStatus[status]
    solutions = np.zeros(len(data))
    for variable in prob.variables():
        if verbose:
            print("{} = {}".format(variable.name, variable.varValue))
        idx = int(variable.name.split("_")[-1])
        solutions[idx] = variable.varValue
    cost = prob.objective.value()

    if status != "Optimal":
        return lp_problem(points, signed_shortage, transfer - 1)

    return solutions, cost, status, transfer
