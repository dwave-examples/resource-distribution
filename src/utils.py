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

import math
from itertools import cycle
from typing import Tuple

import folium
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

from src.solve_lp import haversine


def generate_hospital_dataframe(num_hospitals: int) -> pd.DataFrame:
    """Loads the hospitals dataset and assigns random values of resource shortage/surplus
    proportional to hospital size.

    Args:
        num_hospitals: Number of hospitals to add to the map.

    Returns:
        Hospital data.
    """
    df = pd.read_csv("hospitals_processed.csv").drop(["Unnamed: 0"], axis=1).reset_index()
    df.columns = [x.lower() for x in df.columns]
    df["Population"] = df["population"].values
    df.drop("population", axis=1, inplace=True)

    # Sort hospitals by their distance to the center of Manhattan
    df["d"] = [
        haversine((-73.985130, 40.758896), (lon, lat))
        for lon, lat in zip(df["longitude"], df["latitude"])
    ]
    df = df.sort_values(by="d").head(num_hospitals)

    # Hardcoding seed to keep the same map/hospitals for each run
    np.random.seed(123)
    rnds = np.random.rand(len(df)) * df["Population"]
    rnds = rnds / np.max(np.abs(rnds)) * 100
    rnds = np.round(rnds - np.mean(rnds))
    rnds[np.abs(rnds) < 10] = 10 * (np.random.binomial(1, 0.5, size=sum(np.abs(rnds) < 10)) * 2 - 1)
    df["excess_beds"] = rnds

    # Make sure we have a net surplus of beds
    total_beds = sum(df["excess_beds"])
    if total_beds < 0:
        extra_beds_per_hosp = int(math.ceil(-total_beds / num_hospitals))
        df["excess_beds"] += extra_beds_per_hosp

    return df.sort_values(by="Population", ascending=False)


def get_empty_map(df: pd.DataFrame) -> folium.Map:
    """Create a Folium map with hospital markers.

    Args:
        df: DataFrame containing hospital data for all hospitals in the problem.

    Returns:
        Folium map with markers for hospitals in `df`.
    """
    df["size"] = np.abs(df["excess_beds"])

    start_coords = (40.758896, -73.985130)
    zoom = 12 if len(df) > 25 else 13

    folium_map = folium.Map(location=start_coords, tiles=None, zoom_start=zoom)
    folium.TileLayer(tiles="openstreetmap", opacity=0.5).add_to(folium_map)

    label_colors = [
        "#fc0009",
        "#e10435",
        "#b30963",
        "#910b81",
        "#5f0aad",
        "#4f08ba",
        "#2606de",
        "#1702f6",
    ]

    # Marker color is based on number of excess_beds (scale is from red (shortage) to blue (surplus))
    df["marker_color"] = pd.cut(df["excess_beds"], bins=8, labels=label_colors)

    # Add one marker per hospital
    for name, latitude, longitude, size, excess_beds, color in zip(
        df["name"],
        df["latitude"],
        df["longitude"],
        df["size"],
        df["excess_beds"],
        df["marker_color"],
    ):
        folium.CircleMarker(
            [latitude, longitude],
            radius=math.sqrt(size) + 3,
            tooltip=(
                "Name: " + name + "<br>"
                "Latitude: " + str(latitude) + "<br>"
                "Longitude: " + str(longitude) + "<br>"
                "Excess beds: " + str(excess_beds)
            ),
            fill=True,
            stroke=False,
            fill_color=color,
            fill_opacity=0.8,
            interactive=False,
        ).add_to(folium_map)

    return folium_map


def get_cost(names: list, resources: list, distances: dict) -> float:
    """Compute the cost of transfer in a partition. Cost refers to the sum of distances between pairs
    of hospitals in a partition, in which one hospital has a shortage of beds and the other has a
    surplus.

    Args:
        names: Names of hospitals in the group.

        resources: Amount of shortage/surplus for each hospital in the group. Should be in the same
                   order as `names`.

        distances: Keys are 2-tuples of hospital names and values are the distances between the pair.

    Returns:
        Maximum cost of transfer in a group of hospitals.
    """
    cost = 0
    for h0, beds0 in zip(names, resources):
        for h1, beds1 in zip(names, resources):
            if beds0 > 0 and beds1 < 0:
                cost += distances[(h0, h1)]

    return cost


def get_transfer(excess_beds: np.ndarray) -> float:
    """Compute the maximum number of beds that can be transferred in one group of hospitals.

    Args:
        excess_beds: Contains the amount of shortage/surplus for each hospital in the group.

    Returns:
        Maximum transfer in a group of hospitals.
    """
    surplus = excess_beds[excess_beds > 0]
    shortage = excess_beds[excess_beds < 0]

    if len(surplus) == 0 or len(shortage) == 0:
        # No transfer should be done if there is no shortage or no surplus
        return 0

    surplus = np.sum(surplus)
    shortage = np.sum(-shortage)

    return np.min([surplus, shortage])


def add_result_markers(figure: folium.Map, groups: list) -> None:
    """Adds Polygon markers to `figure` for each group of hospitals specified in `groups`.

    Args:
        figure: Map to add markers to.

        groups: List of HospitalGroup tuples.
    """
    colors = cycle(["red", "blue", "green", "purple", "yellow"])

    for group in groups:
        if group.transfer > 0:
            num_hospitals = len(group.names)
            if num_hospitals > 2:
                hull = ConvexHull(group.positions)
                vertices = hull.vertices
            else:
                vertices = range(num_hospitals)

            locations = [(group.positions[idx][1], group.positions[idx][0]) for idx in vertices]

            color = next(colors)

            hospitals = dict(zip(group.names, group.excess_beds))
            text = "Group of {} hospitals. <br> <br> \
                    Hospitals: {} <br> <br>\
                    Transfer: {:.2f} <br> <br>\
                    Cost: {:.2f}".format(
                num_hospitals, hospitals, group.transfer, group.cost
            )

            popup = folium.map.Popup(html=text, max_width=250)

            folium.vector_layers.Polygon(
                locations,
                fill=True,
                stroke=True,
                color=color,
                fill_color=color,
                fill_opacity=0.3,
                opacity=0.2,
                interactive=False,
                popup=popup,
            ).add_to(figure)


def check_feasibility(groups: list) -> Tuple[bool, bool]:
    """Given groups of hospitals, check that all constraints are satisfied.

    Args:
        groups: List of HospitalGroup tuples.

    Returns:
        Two bools specifying whether each group has a net positive number of beds and whether each
        hospital is only in one group.
    """
    # constraint 1: net positive beds
    net_positive_beds = True

    for group in groups:
        if not group.net_positive_beds:
            net_positive_beds = False
            break

    # constraint 2: in one group
    assigned_hospitals = []
    only_one_group = True

    for group in groups:
        if only_one_group:
            for hospital in group.names:
                if hospital in assigned_hospitals:
                    only_one_group = False
                    break
                assigned_hospitals.append(hospital)

    return net_positive_beds, only_one_group
