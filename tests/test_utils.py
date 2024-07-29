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

import unittest

import folium
import numpy as np
import pandas as pd

from src.resource_distribution import HospitalGroup
from src.utils import (
    check_feasibility,
    generate_hospital_dataframe,
    get_cost,
    get_empty_map,
    get_transfer,
)


class TestUtils(unittest.TestCase):
    def test_generate_hospital_dataframe(self):
        num_hospitals = 2
        hospital_df = generate_hospital_dataframe(num_hospitals)

        self.assertIsInstance(hospital_df, pd.DataFrame)
        self.assertEqual(len(hospital_df), num_hospitals)

    def test_get_empty_map(self):
        hospital_df = pd.read_csv("hospitals_processed.csv")
        hospital_df["excess_beds"] = 0
        folium_map = get_empty_map(hospital_df)

        self.assertIsInstance(folium_map, folium.Map)

    def test_get_cost(self):
        dist = 5
        cost = get_cost(["hospital_1", "hospital_2"], [2, -1], {("hospital_1", "hospital_2"): dist})

        self.assertEqual(cost, dist)

    def test_get_transfer(self):
        excess_beds = np.array([[1, 2], [-2, -1]])
        cost = get_transfer(excess_beds)

        self.assertEqual(cost, 3)

    def test_check_feasibility(self):
        hospital_df = pd.read_csv("hospitals_processed.csv")
        hospital_df["excess_beds"] = 0
        num_hospitals = 2
        distances = dict(
            ((hospital_df["name"][i], hospital_df["name"][j]), 1)
            for i in range(num_hospitals)
            for j in range(num_hospitals)
        )
        group = HospitalGroup(hospital_df, distances)
        net_positive_beds, only_one_group = check_feasibility([group])

        self.assertTrue(net_positive_beds)
        self.assertFalse(only_one_group)
