from flask import Flask
from flask import render_template, url_for, redirect
from flask import flash
from forms import OptimizationParametersForm
from resource_distribution import plot_empty_map, plot_map_results
import plotly.graph_objects as go
import plotly
import json
import sys

if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    port = 5000

app = Flask(__name__)
app.config['SECRET_KEY'] = '2b55241464af362a104880e46b36d2b6'


results = []


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    return render_template('index.html')


@app.route('/optimization', methods=['GET', 'POST'])
def optimization():
    form = OptimizationParametersForm()
    if form.validate_on_submit():
        flash(f'Parameters submitted successfully!', category='success')
        if form.update.data:
            results.clear()
            graph_indices, graphJSON = plot_empty_map(form)
            return render_template('optimization.html', form=form, ids=graph_indices, graphJSON=graphJSON)
        else:
            graph_indices, graphJSON, success, message, run_time, result = plot_map_results(form)
            if success == 0:
                flash(message, category='danger')
                graph_indices, graphJSON = plot_empty_map(form)
                return render_template('optimization.html', form=form, ids=graph_indices, graphJSON=graphJSON)
            elif success == 1:
                flash(message, category='danger')
                flash(f'Solve time: {run_time:.2f}', category='info')
            elif result is None:
                flash(message, category='danger')
            else:
                results.append(result)
                flash(f'Solve time: {run_time:.2f}', category='info')
            return render_template('optimization.html', form=form, ids=graph_indices, graphJSON=graphJSON, results=results)
    else:
        graph_indices, graphJSON = plot_empty_map(form)
        return render_template('optimization.html', form=form, ids=graph_indices, graphJSON=graphJSON)


def plot_results(results):
    fig = go.Figure([
        go.Bar(x=[res.solver for res in results],
               y=[res.energy for res in results]
               )])
    ids = ['graph-results-{}'.format(i) for i in range(1)]
    graphJSON = json.dumps([fig], cls=plotly.utils.PlotlyJSONEncoder)
    return ids, graphJSON


if __name__ == '__main__':
    app.run(debug=False, port=port)
