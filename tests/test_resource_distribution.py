# Copyright 2021 D-Wave Systems Inc.
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

from resource_distribution import get_results

class FormObject:
    def __init__(self, value):
        self.data = value

class MockForm:
    def __init__(self, partition_size=4, num_hospitals=52, 
                 solver='SimulatedAnnealing', alpha=0.2, num_neighbors=8, time_limit=10):
        self.partition_size = FormObject(partition_size)
        self.num_hospitals = FormObject(num_hospitals)
        self.solver = FormObject(solver)
        self.alpha = FormObject(alpha)
        self.num_neighbors = FormObject(num_neighbors)
        self.time_limit = FormObject(time_limit)

class TestResourceDistribution(unittest.TestCase):
    def test_get_results(self):
        form = MockForm(partition_size=2, num_hospitals=10)
        figure, success, msg, run_time, res = get_results(form)

        self.assertEqual(success, 2)
        self.assertEqual(msg, "")
        self.assertAlmostEqual(run_time, 10, places=0)
        self.assertTrue(res)

        output = figure.to_json()
        num_markers = output.count("CircleMarker")
        self.assertEqual(num_markers, 10)   # Checking hospital markers
        self.assertIn("Polygon", output)   # Checking result markers

    def test_bad_results(self):
        form = MockForm(partition_size=3, num_hospitals=10)
        figure, success, msg, run_time, res = get_results(form)

        self.assertEqual(success, 0)
        self.assertEqual(msg, "Number of cities 10 is not divisible by partition size 3")
        self.assertEqual(run_time, 0)
        self.assertIsNone(res)
