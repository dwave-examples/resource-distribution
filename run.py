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
            ids, graphJSON = plot_empty_map(form)
            return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON)
        else:
            ids, graphJSON, success, message, run_time, res = plot_map_results(form)
            if success == 0:
                flash(message, category='danger')
                ids, graphJSON = plot_empty_map(form)
                return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON)
            elif success == 1:
                flash(message, category='danger')
                flash(f'Solve time: {run_time:.2f}', category='info')
            elif res is None:
                flash(message, category='danger')
            else:
                results.append(res)
                flash(f'Solve time: {run_time:.2f}', category='info')
            # ids2, graphJSON2 = plot_results(results)
            # ids += ids2
            # graphJSON += graphJSON2
            return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON, results=results)
    else:
        ids, graphJSON = plot_empty_map(form)
        return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON)


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
