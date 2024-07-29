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
import unittest

import numpy as np

from src.solve_lp import distance_matrix_haversine, haversine, lp_problem


class TestSolveLp(unittest.TestCase):
    def test_haversine(self):
        point_1, point_2 = ((180, 0), (360, 0))

        dist = haversine(point_1, point_2)
        self.assertEqual(dist, math.pi * 6371)

    def test_distance_matrix_haversine(self):
        X = np.array([[180, 0], [360, 0]])
        D = distance_matrix_haversine(X)

        self.assertEqual(D.shape, X.shape)
        self.assertTrue(np.array_equal(D, D.T))
        self.assertAlmostEqual(D[0][1], np.sqrt(math.pi * 6371), places=3)

    def test_lp_problem(self):
        points = np.array([(180, 0), (360, 0)])
        signed_shortage = np.array([1, -1])
        transfer = 1.0
        solutions, cost, status, transfer = lp_problem(points, signed_shortage, transfer)

        self.assertIsNot(len(solutions), 0)
        self.assertAlmostEqual(cost, np.sqrt(math.pi * 6371), places=3)
        self.assertEqual(status, "Optimal")
        self.assertEqual(transfer, 1)
