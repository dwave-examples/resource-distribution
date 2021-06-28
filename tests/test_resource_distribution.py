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

import os
import unittest

from resource_distribution import get_results, FormInput

class TestResourceDistribution(unittest.TestCase):
    def test_get_results(self):
        form = FormInput(num_hospitals=6, 
                         partition_size=2, 
                         num_neighbors=4, 
                         dof=0.2, 
                         solver="SimulatedAnnealing", 
                         time_limit=15)
        figure, result = get_results(form)

        self.assertTrue(result)
        self.assertAlmostEqual(result.t, 15, places=0)

        output = figure.to_json()
        num_markers = output.count("CircleMarker")
        self.assertEqual(num_markers, 6)   # Checking hospital markers
        self.assertIn("Polygon", output)   # Checking result markers

        # Check that problem file was created
        problem_file = "saved_problems/main_problem_{}_{}_{}_{:.2f}".format(form.partition_size, 
                                                                            form.num_hospitals, 
                                                                            form.num_neighbors, 
                                                                            form.dof)

        self.assertTrue(os.path.isfile(problem_file))
        os.remove(problem_file)
