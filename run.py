from flask import Flask
from flask import render_template, url_for, redirect
from flask import flash
from forms import OptimizationParameters
from get_graphs import get_graphs, get_graphs_results


app = Flask(__name__)
app.config['SECRET_KEY'] = '2b55241464af362a104880e46b36d2b6'


results = []


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    return render_template('index.html')


@app.route('/optimization', methods=['GET', 'POST'])
def optimization():
    form = OptimizationParameters()
    if form.validate_on_submit():
        flash(f'Parameters sumbitted successfully!', category='success')
        ids, graphJSON, success, message, run_time, res = get_graphs_results(form)
        if success == 0:
            flash(message, category='danger')
        elif success == 1:
            flash(message, category='danger')
            flash(f'Solve time: {run_time:.2f}', category='info')
        elif res is None:
            flash(message, category='danger')
        else:
            results.append(res)
            flash(f'Solve time: {run_time:.2f}', category='info')
        return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON, results=results)
    else:
        ids, graphJSON = get_graphs(form)
        return render_template('optimization.html', form=form, ids=ids, graphJSON=graphJSON)


if __name__ == '__main__':
    app.run(debug=True)
