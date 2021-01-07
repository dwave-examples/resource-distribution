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

