from flask import Flask
from flask import render_template, url_for, redirect
from flask import flash
from forms import OptimizationParametersForm
from resource_distribution import get_empty_map, plot_results
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
app.config['TEMPLATES_AUTO_RELOAD'] = True


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
            empty_map = get_empty_map(form)
            empty_map.save('templates/map.html')
            return render_template('optimization.html', form=form)
        else:
            map_results, success, message, run_time, result = plot_results(form)
            map_results.save('templates/map.html')
            if success == 0:
                flash(message, category='danger')
                return render_template('optimization.html', form=form)
            elif success == 1:
                flash(message, category='danger')
                flash(f'Solve time: {run_time:.2f}', category='info')
            elif result is None:
                flash(message, category='danger')
            else:
                results.append(result)
                flash(f'Solve time: {run_time:.2f}', category='info')
            return render_template('optimization.html', form=form, results=results)
    else:
        empty_map = get_empty_map(form)
        empty_map.save('templates/map.html')

        return render_template('optimization.html', form=form)

if __name__ == '__main__':
    app.run(debug=False, port=port)
