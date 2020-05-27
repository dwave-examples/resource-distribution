from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo


_choices = ['SimulatedAnnealing', 'TabuSampler', 'LeapHybridSampler']


class OptimizationParameters(FlaskForm):
    partition_size = IntegerField('Partition size', validators=[DataRequired()], default=4)
    longitude = FloatField('longitude', validators=[DataRequired()], default=-95)
    population = IntegerField('population', validators=[DataRequired()], default=100000)
    num_neighbors = IntegerField('Number of Neighbors', validators=[DataRequired()], default=8)
    solver = SelectField('Solver', choices=[(x, x) for x in _choices])
    submit = SubmitField('Run')
    time_limit = FloatField('Time Limit (seconds)', default=10)
    num_sweeps = IntegerField('Number of sweeps', validators=[DataRequired()], default=1000)
    num_reads = IntegerField('Number of reads', validators=[DataRequired()], default=10)

