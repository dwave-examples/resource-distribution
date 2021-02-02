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

import sys

from flask import Flask
from flask import render_template, url_for, redirect
from flask import flash
from forms import OptimizationParametersForm

from resource_distribution import get_empty_map, get_results

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
            figure, success, message, run_time, result = get_results(form)
            figure.save('templates/map.html')
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
