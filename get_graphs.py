import plotly
import plotly.express as px
import plotly.graph_objects as go
from dwave.system import LeapHybridSampler
from neal import SimulatedAnnealingSampler
from scipy.spatial import ConvexHull
from tabu import TabuSampler
import pandas as pd
from itertools import combinations
from time import time
import numpy as np
from dimod import BinaryQuadraticModel
from collections import defaultdict
import json
from itertools import product
from problem_intro import lp_problem, haversine
import dimod
import pickle
from os.path import exists
from os import makedirs


def distance_matrix_haversine(X):
    M = X.shape[0]
    N = X.shape[1]
    if N != 2:
        raise ValueError
    D = np.zeros((M, M), dtype=np.float32)
    for i in range(M):
        for j in range(M):
            d = haversine(X[i], X[j])
            D[i, j] = np.sqrt(d)
    return D


def us_hospitals(num_hospitals):
    # df = pd.read_csv('Hospitals.csv')
    df = pd.read_csv('hospitals_processed.csv').drop(['Unnamed: 0'], axis=1).reset_index()
    df.columns = [x.lower() for x in df.columns]
    df['Population'] = df['population'].values
    df.drop('population', axis=1, inplace=True)
    df['d'] = [haversine((-73.985130, 40.758896), (lon, lat)) for lon, lat in zip(df['longitude'], df['latitude'])]
    df = df.sort_values(by='d').head(num_hospitals)

    seed = 123
    np.random.seed(seed)
    rnds = np.random.rand(len(df)) * df['Population']
    rnds = rnds / np.max(np.abs(rnds)) * 100
    rnds = np.round(rnds - np.mean(rnds))
    rnds[np.abs(rnds) < 10] = 10 * (np.random.binomial(1, 0.5, size=sum(np.abs(rnds) < 10)) * 2 - 1)
    df['excess_beds'] = rnds
    return df


def create_utility_function(form, include_first_neighbor=False):
    num_hospitals = int(form.num_hospitals.data)
    num_neighbors = int(form.num_neighbors.data)
    partition_size = int(form.partition_size.data)
    alpha = float(form.alpha.data)

    df = us_hospitals(num_hospitals).sort_values(by='Population', ascending=False)
    xy = df[['longitude', 'latitude']].values
    excess = df['excess_beds'].values
    d = distance_matrix_haversine(xy)
    n = len(d)
    if n % partition_size != 0:
        return None, None, df, n, None
    nn = []
    for i in range(n):
        nn.append(np.argsort(d[i])[1:num_neighbors+1])
    p_combinations = set()
    for idx, neighb in enumerate(nn):
        if include_first_neighbor:
            combs = list(map(lambda x: frozenset(x).union({idx}).union({neighb[0]}),
                             combinations(neighb[1:], partition_size - 2)))
        else:
            combs = list(map(lambda x: frozenset(x).union({idx}), combinations(neighb, partition_size - 1)))
        p_combinations = p_combinations.union(set(combs))
    utility = []
    utility_dict = {}
    objective = {}
    for part in p_combinations:
        beds = excess[list(part)]
        transfer = transfer_score(beds)
        xys = xy[list(part)]
        solutions, cst, status, transfer = lp_problem(xys, beds, transfer, verbose=False)
        utility.append([part, transfer, cst])
    utility = np.array(utility)
    transfer_stdev = np.std(utility[:, 1])
    cost_stdev = np.std(utility[:, 2])
    for part, transfer, cst in utility:
        objective[part] = (1 - alpha) * transfer / transfer_stdev - alpha * cst / cost_stdev
        utility_dict[part] = [transfer, cst]
    p_combinations = list(p_combinations)
    return p_combinations, utility_dict, df, n, objective


def transfer_score(beds):
    pos = beds[beds > 0]
    neg = beds[beds < 0]
    if len(pos) == 0:
        return 0
    if len(neg) == 0:
        return 0
    pos = np.sum(pos)
    neg = np.sum(-neg)
    return np.min([pos, neg])


def k_clique_from_combinations(utility=None, lagrange=3):
    """
    This function naively generates all possible combinations of size number_variables/num_partitions and then
    using a given utility function (generated randomly here), creates an objective function that find the clique of size
    num_partitions that has the maximum utility function.
    :param utility: A dictionary with frozenset of size partition_size as keys. The dictionary returns the utitlity function for a given partition
    :param lagrange: optional (default 3)
        Lagrange parameter to weight constraints (no edges within set)
        versus objective (largest set possible).
    :return:
    bqm: BinaryQuadraticModel
    utility: dict
    p_combinations: list
    """
    p_combinations = list(utility.keys())
    scale = np.max(np.abs(list(utility.values())))
    qubo = defaultdict(float)
    for idx, u in enumerate(p_combinations):
        qubo[(idx, idx)] += - utility[u] / scale - lagrange
        for jdx, v in enumerate(p_combinations):
            if jdx <= idx:
                continue
            intersection = u.intersection(v)
            if len(intersection) > 0:
                qubo[(idx, jdx)] += lagrange * len(intersection)
    bqm = BinaryQuadraticModel.from_qubo(qubo)
    return bqm, utility, p_combinations


def get_sampler(form):
    name = form.solver.data
    if name == 'SimulatedAnnealing':
        return SimulatedAnnealingSampler(), {}
    elif name == 'LeapHybridSampler':
        return LeapHybridSampler(), {'time_limit': float(form.time_limit.data)}
    elif name == 'TabuSampler':
        return TabuSampler(), {'timeout': int(form.time_limit.data) * 1000}
    else:
        raise ValueError


def plot(form):
    px.set_mapbox_access_token(open(".mapbox_token").read())
    df = us_hospitals(int(form.num_hospitals.data))
    df['size'] = np.abs(df['excess_beds'])
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", color="excess_beds", size='size',
                            center=dict(lon=-73.985130, lat=40.758896),
                            labels={'latitude': 'Latitude', 'longitude': 'Longitude', 'excess_beds': 'Excess Beds'},
                            color_continuous_scale=list(reversed(px.colors.sequential.Bluered)), zoom=10, height=800)
    return fig


def plot_results(form):
    message = ''
    fig = plot(form)
    name = f'saved_problems/main_problem_{form.partition_size.data}_{form.num_hospitals.data}_{form.num_neighbors.data}_{form.alpha.data:.2f}'
    if not exists('saved_problems/'):
        makedirs('saved_problems/')
    if exists(name):
        print('loading')
        with open(name, 'rb') as f:
            p_combinations, utility, df, n, objective = pickle.load(f)
    else:
        p_combinations, utility, df, n, objective = create_utility_function(form)
        print('writing')
        with open(name, 'wb') as f:
            pickle.dump((p_combinations, utility, df, n, objective), f)
    if utility is None:
        message = f'Number of cities {n} is not divisible by partition size {form.partition_size.data}'
        return fig, 0, message, 0, None

    bqm, _, p_combinations = k_clique_from_combinations(utility=objective, lagrange=10)
    num_variables = len(set().union(*p_combinations))
    partition_size = len(p_combinations[0])

    sampler, params = get_sampler(form)
    t0 = time()
    try:
        if form.solver.data == 'SimulatedAnnealing':
            res = sampler.sample(bqm)
            beta_range = res.info['beta_range']
            t0 = time()
            res = sampler.sample(bqm, beta_range=beta_range)
            t = time() - t0
            nsw = int(float(form.time_limit.data) / t * 1000 / 10)
            print(nsw)
            t = 0
            while t < float(form.time_limit.data):
                t0 = time()
                res = dimod.concatenate((res, sampler.sample(bqm, num_sweeps=nsw, beta_range=beta_range)))
                t += time() - t0
            res = res.truncate(1)
        else:
            res = sampler.sample(bqm, **params).truncate(1)
            t = time() - t0
            if form.solver.data == 'LeapHybridSampler':
                t = res.info['run_time'] / 1e6

    except ValueError as err:
        message = str(err)
        return fig, 0, message, 0, None
    variables = np.array(res.variables)

    num_variables = len(set().union(*p_combinations))
    k = num_variables // partition_size
    res = Result(res, p_combinations, variables, num_variables, utility, k, t, solver=form.solver.data)
    if res.total_cost is None or res.total_utility is None or res.energy is None:
        message = f'No feasible solution found'
        return fig, 1, message, t, None
    sample = res.sample
    sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
    np.random.seed(123)
    for sorg in sol:
        fig = add_trace(fig, df, sorg, utility)

    fig.update_layout(title=f'Valid solution with utility {res.total_utility} '
                            f'and total cost {res.total_cost:.2f}, objective {res.energy:.2f}')
    return fig, 2, message, t, res


class Result:
    def __init__(self, res, p_combinations, variables, num_variables, utility, k, t, solver):
        total_cost = None
        self.solver = solver
        total_utility = None
        self.t = t
        energy = None
        for sample, energy, occ in res.record:
            if k != sum(sample):
                continue
            sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
            union = set().union(*sol)
            inter = [set().intersection(a, b) for a, b in combinations(sol, 2)]
            inter = [len(x) for x in inter]
            intersect_length = sum(inter)
            if intersect_length > 0:
                continue
            if len(union) != num_variables:
                continue
            total_utility = np.sum([utility[x][0] for x in sol])
            total_cost = np.sum([utility[x][1] for x in sol])
        self.sample = res.truncate(1).record.sample[0]
        self.total_utility = total_utility
        self.total_cost = total_cost
        self.energy = energy

    def __repr__(self):
        return f'{self.solver:40s}: Utility {self.total_utility:.2f}, cost {self.total_cost:.2f}, energy {self.energy:.2f}, in {self.t:.2f} seconds'


def add_trace(fig, df, sorg, utility):
    s = np.array(list(sorg))
    dfxy = df.iloc[s]
    dfxy = dfxy[['longitude', 'latitude']]
    if len(s) > 2:
        hull = ConvexHull(dfxy.values)
        vertices = hull.vertices
    else:
        vertices = range(len(s))
    u = utility[sorg]
    text = f'Transfers {u[0]:.2f}, Cost {u[1]:.2f}'
    cm = np.mean(dfxy.values[vertices], axis=0)
    rnd = lambda: np.random.randint(0, 256)
    color = f'rgba({rnd()}, {rnd()}, {rnd()}, 0.3)'
    if u[0] > 0:
        fig.add_trace(
            go.Scattermapbox(
                lon=[dfxy.values[idx][0] for idx in vertices],
                lat=[dfxy.values[idx][1] for idx in vertices],
                fill='toself',
                fillcolor=color,
                showlegend=False,
                hoverinfo='none',
                mode='none',
                marker={'size': 0},
            ))

        fig.add_trace(
            go.Scattermapbox(
                lon=[cm[0]],
                lat=[cm[1]],
                showlegend=False,
                text=text,
                hoverinfo='none',
                mode='text',
                marker=go.scattermapbox.Marker(
                    size=0,
                    opacity=0.0
                ),
            ))
    return fig


def get_graphs(form):
    graphs = [plot(form)]
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return ids, graphJSON


def get_graphs_results(form):
    fig, success, message, run_time, res = plot_results(form)
    graphs = [fig]
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return ids, graphJSON, success, message, run_time, res


class Obj:
    def __init__(self, value):
        self.data = value


class Dummy:
    partition_size = Obj(4)
    num_hospitals = Obj(16)
    solver = Obj('TabuSampler')
    alpha = Obj(1.0)

    num_neighbors = Obj(21)
    time_limit = Obj(10)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    form = Dummy()
    fig, success, message, t, res = plot_results(form)
    # print(success)
    # print(message)
    # if success:
    #     fig.show()
        # fig.write_image(f'{res.solver}_{form.time_limit.data}.png', width=2000)
    # us_hospitals(-100, 100)
#     df = pd.read_csv('Hospitals.csv')
#     df.columns = [x.lower() for x in df.columns]
#     df['d'] = [haversine((-73.985130, 40.758896), (lon, lat)) for lon, lat in zip(df['longitude'], df['latitude'])]
#     df = df.sort_values(by='d').head(1000).reset_index()
#
#     df['keep'] = 1
#     for i in range(len(df)):
#         if not df.loc[df.index[i], 'keep']:
#             continue
#         lon1 = df.loc[df.index[i], 'longitude']
#         lat1 = df.loc[df.index[i], 'latitude']
#         for j in range(i + 1, len(df)):
#             if not df.loc[df.index[j], 'keep']:
#                 continue
#             lon2 = df.loc[df.index[j], 'longitude']
#             lat2 = df.loc[df.index[j], 'latitude']
#             d = haversine((lon1, lat1), (lon2, lat2))
#             if d < 0.1:
#                 if df.loc[df.index[i], 'population'] > df.loc[df.index[j], 'population']:
#                     df.loc[df.index[j], 'keep'] = 0
#                 else:
#                     df.loc[df.index[i], 'keep'] = 0
#         print(sum(df['keep']))
#     print(len(df))
#     df = df[df['keep'] == 1]
#     df.to_csv('hospitals_processed.csv')
#     print(len(df))
# #