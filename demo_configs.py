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

"""This file stores input parameters for the app."""

THUMBNAIL = "static/dwave_logo.svg"

APP_TITLE = "Resource Distribution"
MAIN_HEADER = "Resource Distribution"
DESCRIPTION = """\
Hospitals get divided into groups such that the maximum
number of transfers is achieved at minimum cost (distance). Transfer is the smaller
number between total excess and total shortage in a group of hospitals.
"""

#######################################
# Sliders, buttons and option entries #
#######################################

NUM_HOSPITALS = {
    "min": 2,
    "step": 1,
    "value": 12,
}

PARTITION_SIZE = {
    "min": 2,
    "max": 6,
    "step": 1,
    "value": 4,
}

NUM_NEIGHBORS = {
    "min": 4,
    "max": 12,
    "step": 1,
    "value": 8,
}

DISTANCE_OBJECTIVE_FRACTION = {
    "min": 0,
    "max": 1,
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
