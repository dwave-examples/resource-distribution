from flask_wtf import FlaskForm
from wtforms import SubmitField, FloatField, IntegerField, SelectField
from wtforms.fields.html5 import DecimalRangeField
from wtforms.validators import DataRequired


_choices = ['SimulatedAnnealing', 'TabuSampler', 'LeapHybridSampler']


class OptimizationParameters(FlaskForm):
    partition_size = IntegerField('Partition size', validators=[DataRequired()], default=4)
    longitude = FloatField('longitude', validators=[DataRequired()], default=-95)
    # alpha = FloatField('alpha', default=0.0)
    alpha = DecimalRangeField('Distance Objective Fraction', default=0.5)
    num_cities = IntegerField('Number of cities', validators=[DataRequired()], default=40)
    num_neighbors = IntegerField('Number of Neighbors', validators=[DataRequired()], default=8)
    solver = SelectField('Solver', choices=[(x, x) for x in _choices])
    submit = SubmitField('Run')
    time_limit = FloatField('Time Limit (seconds)', default=10)
    num_sweeps = IntegerField('Number of sweeps', validators=[DataRequired()], default=1000)
    num_reads = IntegerField('Number of reads', validators=[DataRequired()], default=10)

