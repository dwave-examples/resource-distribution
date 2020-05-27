from flask import Flask
from flask import render_template, url_for, redirect
from flask import flash
from forms import OptimizationParameters
from get_graphs import get_graphs, get_graphs_results


app = Flask(__name__)
app.config['SECRET_KEY'] = '2b55241464af362a104880e46b36d2b6'


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def home():
    form = OptimizationParameters()
    if form.validate_on_submit():
        flash(f'Parameters sumbitted successfully!', category='success')
        ids, graphJSON, success, message, run_time = get_graphs_results(form)
        if success == 0:
            flash(message, category='danger')
        elif success == 1:
            flash(message, category='danger')
            flash(f'Solve time: {run_time:.2f}', category='info')
        else:
            flash(f'Solve time: {run_time:.2f}', category='info')
        return render_template('index.html', form=form, ids=ids, graphJSON=graphJSON)
    else:
        ids, graphJSON = get_graphs(form)
        return render_template('index.html', form=form, ids=ids, graphJSON=graphJSON)


if __name__ == '__main__':
    app.run(debug=True)
