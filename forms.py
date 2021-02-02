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

from flask_wtf import FlaskForm
from wtforms import SubmitField, FloatField, IntegerField, SelectField
from wtforms.fields.html5 import DecimalRangeField
from wtforms.validators import DataRequired


_choices = ['SimulatedAnnealing', 'TabuSampler', 'LeapHybridSampler']


class OptimizationParametersForm(FlaskForm):
    partition_size = IntegerField('Partition size', validators=[DataRequired()], default=4)
    alpha = DecimalRangeField('Distance Objective Fraction', default=0.2)
    num_hospitals = IntegerField('Number of Hospitals', validators=[DataRequired()], default=52)
    num_neighbors = IntegerField('Number of Neighbors', validators=[DataRequired()], default=8)
    solver = SelectField('Solver', choices=[(x, x) for x in _choices], default='SimulatedAnnealing')
    submit = SubmitField('Run')
    update = SubmitField('Update Map')
    time_limit = FloatField('Time Limit (seconds)', default=10)

