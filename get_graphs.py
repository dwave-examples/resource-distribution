import plotly
import plotly.express as px
import plotly.graph_objects as go
from dwave.system import LeapHybridSampler
from neal import SimulatedAnnealingSampler
from scipy.spatial import ConvexHull
import pandas as pd
from itertools import combinations
from time import time
import numpy as np
from dimod import BinaryQuadraticModel
from collections import defaultdict
import json
from numba import jit
from itertools import product
from problem_intro import lp_problem


def haversine(p1, p2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    lon1, lat1 = p1
    lon2, lat2 = p2
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = np.radians([lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


@jit(nopython=True)
def distance_matrix(X, y=None):
    M = X.shape[0]
    N = X.shape[1]
    D = np.zeros((M, M), dtype=np.float32)
    for i in range(M):
        for j in range(M):
            d = 0.0
            for k in range(N):
                tmp = X[i, k] - X[j, k]
                d += tmp * tmp
            D[i, j] = np.sqrt(d)
    return D


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


def us_cities(longitude, num_cities):
    df = pd.read_csv('1000-largest-us-cities-by-population-with-geographic-coordinates.csv', sep=';')
    xy = df['Coordinates'].str.split(',', expand=True).applymap(float)
    xy.columns = ['latitude', 'longitude']
    df = pd.concat((df, xy), axis=1).drop('Coordinates', axis=1)
    df = df[df['longitude'] > longitude].sort_values(by='Population', ascending=False).head(num_cities)

    seed = 123
    np.random.seed(seed)
    rnds = np.random.randint(-100, 100, size=len(df))
    df['excess_beds'] = np.round(rnds - np.mean(rnds))
    return df


def poly_area(xy):
    xy = np.array(xy)
    x = xy[:, 0]
    y = xy[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def create_utility_function(form, include_first_neighbor=False):
    longitude = float(form.longitude.data)
    num_cities = int(form.num_cities.data)
    num_neighbors = int(form.num_neighbors.data)
    partition_size = int(form.partition_size.data)
    alpha = float(form.alpha.data)

    df = us_cities(longitude, num_cities).sort_values(by='Population', ascending=False)
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
        # cst = cost(beds, xys)
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


def cost(beds, xys):
    from pulp import LpProblem, lpSum, LpVariable, LpMinimize, LpInteger
    pos = beds[beds > 0]
    neg = beds[beds < 0]
    xysp = xys[beds > 0]
    xysn = xys[beds < 0]
    if len(pos) == 0:
        return 0
    if len(neg) == 0:
        return 0
    fs = []
    ds = []
    transfer = transfer_score(beds)
    for (p, pp), (n, pn) in product(zip(pos, xysp), zip(neg, xysn)):
        d = haversine(pp, pn)
        f = np.min([p, -n])
        fs.append(f)
        ds.append(d)
    if sum(fs) == transfer:
        return sum(ds)
    if sum(fs) < transfer:
        raise ValueError
    if sum(fs) > transfer:
        prob = LpProblem("Transfer_cost", LpMinimize)
        varbs = LpVariable.dicts('main', list(range(len(fs))), lowBound=0, cat=LpInteger, upBound=1)
        prob += lpSum([ds[i] * varbs[i] for i in range(len(ds))])
        prob += lpSum([fs[i] * varbs[i] for i in range(len(ds))]) >= transfer
        prob.solve()
        sol = [prob.variables()[i].varValue for i in range(len(ds))]
        return np.sum([ds[i] for i in range(len(ds)) if sol[i] > 0])

    return 0


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
    df = us_cities(float(form.longitude.data), int(form.num_cities.data))
    df['size'] = 12  # np.abs(df['excess_beds'].values)
    fig = px.scatter_mapbox(df, lat="latitude", lon="longitude", color="excess_beds", size='size',
                            labels={'latitude': 'Latitude', 'longitude': 'Longitude', 'excess_beds': 'Excess Beds'},
                            color_continuous_scale=px.colors.cyclical.IceFire, size_max=12, zoom=4, height=800)
    return fig


def plot_results(form):
    message = ''
    fig = plot(form)
    p_combinations, utility, df, n, objective = create_utility_function(form)
    if utility is None:
        message = f'Number of cities {n} is not divisible by partition size {form.partition_size.data}'
        success = 0
        return fig, success, message, 0

    bqm, _, p_combinations = k_clique_from_combinations(utility=objective, lagrange=10)
    num_variables = len(set().union(*p_combinations))
    partition_size = len(p_combinations[0])

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
    total_cost = None
    total_utility = None
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
        success = 2
    if total_utility is None or total_cost is None or energy is None:
        message = f'No feasible solution found'
        return fig, 1, message, t
    if success == 2:
        sample = res.truncate(1).record.sample[0]
        sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
        for sorg in sol:
            s = np.array(list(sorg))
            dfxy = df.iloc[s]
            dfxy = dfxy[['longitude', 'latitude']]
            if len(s) > 2:
                hull = ConvexHull(dfxy.values)
                vertices = hull.vertices
            else:
                vertices = range(len(s))
            u = list(map(int, utility[sorg]))
            text = f'Transfers {u[0]:d}, Cost {u[1]:d}'
            cm = np.mean(dfxy.values[vertices], axis=0)
            fig.add_trace(
                go.Scattermapbox(
                    lon=[dfxy.values[idx][0] for idx in vertices],
                    lat=[dfxy.values[idx][1] for idx in vertices],
                    fill='toself',
                    showlegend=False,
                    # text=text,
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
                    marker={'size': 0},
                ))

        fig.update_layout(title=f'Valid solution with utility {total_utility} '
                                f'and total cost {total_cost:.0f}, objective {energy:.2f}')
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
    partition_size = Obj(4)
    longitude = Obj(-95)
    num_cities = Obj(40)
    solver = Obj('SimulatedAnnealing')
    alpha = Obj(0.5)

    num_neighbors = Obj(8)
    time_limit = Obj(10)
    num_sweeps = Obj(1000)
    num_reads = Obj(1)


if __name__ == '__main__':
    form = Dummy()
    fig, success, message, t = plot_results(form)
    print(success)
    if success:
        fig.show()
