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

"""This file stores input parameters for the app."""

ADDRESS = "Cambridge Ln, Rockhampton QLD 4700, Australia"
DISTANCE = 1700  # bounding box distance (in meters) around address
THUMBNAIL = "assets/dwave_logo.svg"

APP_TITLE = "Resource Distribution Demo"
MAIN_HEADER_BQM = "BQM Resource Distribution Optimization"
DESCRIPTION_BQM = """\
In the BQM formulation, the goal is to divide the hospitals into groups such that the maximum 
number of transfers is achieved at minimum cost. Transfer is quantified as the smaller 
number between total excess and total shortage in a group of hospitals. Cost is the sum of all 
costs associated with transferring resources from one hospital to another: In this demonstration, 
only distance is considered as a cost. 
"""
MAIN_HEADER_CQM = "CQM Resource Distribution Optimization"
DESCRIPTION_CQM = """\
The BQM formulation requires multiple mathematical transformations to run on an unconstrained 
solver: the original problem is reformulated as a maximum-independent-set problem.
The CQM formulation enables the direct solution of the original problem in an intuitive way.
"""

#######################################
# Sliders, buttons and option entries #
#######################################


SAMPLER_TYPES_BQM = [
       {'label': 'Leap Hybrid BQM Sampler', 'value': 'Leap Hybrid BQM Sampler'},
       {'label': 'Tabu Sampler', 'value': 'Tabu Sampler'},
       {'label': 'Simulated Annealing', 'value': 'Simulated Annealing'},
   ]


SAMPLER_TYPES_CQM = [
       {'label': 'Leap Hybrid CQM Sampler', 'value': 'Leap Hybrid CQM Sampler'},
       {'label': 'Leap Hybrid BQM Sampler', 'value': 'Leap Hybrid BQM Sampler'},
       {'label': 'Simulated Annealing', 'value': 'Simulated Annealing'},
       {'label': 'Tabu Sampler', 'value': 'Tabu Sampler'},
   ]

NUM_HOSPITALS = {
    "min": 2,
    "step": 1,
    "value": 12,
}

PARTITION_SIZE = {
    "min": 1,
    "max": 100,
    "step": 1,
    "value": 4,
}

NUM_NEIGHBORS = {
    "min": 1,
    "max": 100,
    "step": 1,
    "value": 8,
}

DISTANCE_OBJECTIVE_FRACTION = {
    "min": 0.0,
    "max": 1.0,
    "step": 0.01,
    "value": 0.2,
}

# solver time limits in seconds (value means default)
SOLVER_TIME = {
    "min": 5,
    "max": 300,
    "step": 5,
    "value": 5,
}
