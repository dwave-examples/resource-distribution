import json
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dwave.system import LeapHybridSampler
from load_datasets import distance_matrix
from neal import SimulatedAnnealingSampler
from scipy.spatial import ConvexHull
import pandas as pd
from collections import defaultdict
import numpy as np
from itertools import combinations
from dimod import BinaryQuadraticModel
from time import time


def us_cities(longitude, population):
    df = pd.read_csv('1000-largest-us-cities-by-population-with-geographic-coordinates.csv', sep=';')
    xy = df['Coordinates'].str.split(',', expand=True).applymap(float)
    xy.columns = ['latitude', 'longitude']
    df = pd.concat((df, xy), axis=1).drop('Coordinates', axis=1)
    df = df[df['longitude'] > longitude]
    df = df[df['Population'] > population]
    return df


def poly_area(xy):
    xy = np.array(xy)
    x = xy[:, 0]
    y = xy[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def create_utility_function(form, include_first_neighbor=False):
    longitude = float(form.longitude.data)
    population = int(form.population.data)
    num_neighbors = int(form.num_neighbors.data)
    partition_size = int(form.partition_size.data)

    df = us_cities(longitude, population).sort_values(by='Population', ascending=False)
    df = df[df['longitude'] > longitude]
    df = df[df['Population'] > population].reset_index()
    xy = df[['longitude', 'latitude']].values
    print('Number of cities: {}'.format(xy.shape[0]))
    d = distance_matrix(xy)
    n = len(d)
    if n % partition_size != 0:
        return None, None, df, n
    nn = []
    for i in range(n):
        nn.append(np.argsort(d[i])[1:num_neighbors])
    p_combinations = set()
    for idx, neighb in enumerate(nn):
        if include_first_neighbor:
            combs = list(map(lambda x: frozenset(x).union({idx}).union({neighb[0]}),
                             combinations(neighb[1:], partition_size - 2)))
        else:
            combs = list(map(lambda x: frozenset(x).union({idx}), combinations(neighb, partition_size - 1)))
        p_combinations = p_combinations.union(set(combs))
    utility = {}
    for part in p_combinations:
        # xys = xy[list(part)]
        # hull = ConvexHull(xys)
        # xys = xys[hull.vertices]
        c = d[list(part), :][:, list(part)]
        utility[part] = - np.linalg.norm(c) ** 2  # - poly_area(xys)
    p_combinations = list(p_combinations)
    return p_combinations, utility, df, n


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


def display_result(res, p_combinations, variables, k, num_variables, utility):
    success = False
    for sample, energy, occ in res.record:
        if k != sum(sample):
            continue
        print('Number of partitions, {}, is equal to sum(sample)'.format(k))
        sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
        union = set().union(*sol)
        inter = [set().intersection(a, b) for a, b in combinations(sol, 2)]
        inter = [len(x) for x in inter]
        intersect_length = sum(inter)
        if intersect_length > 0:
            continue
        if len(union) != num_variables:
            continue
        print('Utility (higher better): {}'.format(np.sum([utility[x] for x in sol])))
        print('Energy (lower better): {}'.format(energy))
        success = True
    return success


def get_sampler(form):
    name = form.solver.data
    if name == 'SimulatedAnnealing':
        parameters = {
            'num_reads': int(form.num_reads.data),
            'num_sweeps': int(form.num_sweeps.data),
        }
        return SimulatedAnnealingSampler(), parameters
    elif name == 'LeapHybridSampler':
        return LeapHybridSampler(), {'time_limit': float(form.time_limit.data)}
    else:
        raise ValueError


def plot(form):
    px.set_mapbox_access_token(open(".mapbox_token").read())
    df = us_cities(float(form.longitude.data), int(form.population.data))
    df['size'] = 8
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", color="Population", size='size',  # "Population",
                            color_continuous_scale=px.colors.cyclical.IceFire, size_max=8, zoom=4, height=800)
    return fig


def plot_results(form):
    message = ''
    fig = plot(form)
    p_combinations, utility, df, n = create_utility_function(form)
    if utility is None:
        message = f'Number of cities {n} is not divisible by partition size {form.partition_size.data}'
        success = 0
        return fig, success, message, 0

    bqm, _, p_combinations = k_clique_from_combinations(utility=utility, lagrange=10)
    num_variables = len(set().union(*p_combinations))
    partition_size = len(p_combinations[0])
    print('Partition size: {}'.format(partition_size))
    k = num_variables // partition_size
    print('Number of variables: {}, Number of edges: {}'.format(*bqm.shape))

    sampler, params = get_sampler(form)
    t0 = time()
    try:
        res = sampler.sample(bqm, **params)
    except ValueError as err:
        message = str(err)
        success = 0
        return fig, success, message, 0
    min_en = np.min(res.record.energy)
    t = time() - t0
    variables = np.array(res.variables)

    num_variables = len(set().union(*p_combinations))
    k = num_variables // partition_size

    success = 1
    for sample, energy, occ in res.record:
        if k != sum(sample):
            continue
        print('Number of partitions, {}, is equal to sum(sample)'.format(k))
        sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
        union = set().union(*sol)
        inter = [set().intersection(a, b) for a, b in combinations(sol, 2)]
        inter = [len(x) for x in inter]
        intersect_length = sum(inter)
        if intersect_length > 0:
            continue
        if len(union) != num_variables:
            continue
        print('Utility (higher better): {}'.format(np.sum([utility[x] for x in sol])))
        print('Energy (lower better): {}'.format(energy))
        success = 2
    if success == 2:
        sample = res.truncate(1).record.sample[0]
        sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
        for s in sol:
            s = np.array(list(s))
            dfxy = df.iloc[s]
            dfxy = dfxy[['longitude', 'latitude']]
            hull = ConvexHull(dfxy.values)
            fig.add_trace(
                go.Scattermapbox(
                    lon=[dfxy.values[idx][0] for idx in hull.vertices],
                    lat=[dfxy.values[idx][1] for idx in hull.vertices],
                    fill='toself',
                    showlegend=False
                ))
    else:
        message = f'No feasible solution found'
    return fig, success, message, t


def get_graphs(form):
    graphs = [plot(form)]
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return ids, graphJSON


def get_graphs_results(form):
    fig, success, message, run_time = plot_results(form)
    graphs = [fig]
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return ids, graphJSON, success, message, run_time


class Obj:
    def __init__(self, value):
        self.data = value


class Dummy:
    partition_size = Obj(5)
    longitude = Obj(-90)
    population = Obj(100000)
    solver = Obj('LeapHybridSampler')


if __name__ == '__main__':
    form = Dummy()
    fig, success = plot_results(form)
    print(success)
    if success:
        fig.show()
