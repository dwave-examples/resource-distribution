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
from solve_lp import lp_problem, haversine, distance_matrix_haversine
import dimod
import pickle
from os.path import exists
from os import makedirs
from forms import OptimizationParametersForm
import folium
from folium.features import DivIcon


def us_hospitals(num_hospitals: int) -> pd.DataFrame:
    """
    Load the hospitals dataset and assign random values of shortage/surplus of resources proportional to the size of
        the hospitals.

    :param num_hospitals: The number of hospitals to keep
    :return: pandas.DataFrame
    """
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


def create_utility_function(form: OptimizationParametersForm, include_first_neighbor=False):
    """
    Given the parameters set by the user specified in `form`, create partitions of hospitals, compute the optimal
        cost and utility of each partition
    :param form: A user form specified by the class `OptimizationParametersForm`
    :param include_first_neighbor: To reduce complexity of the problem, always consider the first nearest neighbor.
    :return:
    """
    num_hospitals = int(form.num_hospitals.data)
    num_neighbors = int(form.num_neighbors.data)
    partition_size = int(form.partition_size.data)
    alpha = float(form.alpha.data)

    dataframe = us_hospitals(num_hospitals).sort_values(by='Population', ascending=False)
    positions = dataframe[['longitude', 'latitude']].values
    excess = dataframe['excess_beds'].values
    d = distance_matrix_haversine(positions)
    num_hospitals = len(d)
    if num_hospitals % partition_size != 0:
        return None, None, dataframe, num_hospitals, None

    # for each hospital find the first few nearest neighbors up to num_neighbors
    nearest_neighbors = []
    for i in range(num_hospitals):
        nearest_neighbors.append(np.argsort(d[i])[1:num_neighbors+1])

    # find all partitions that include num_neighbors of the nearest neighbors
    partitions = set()
    for idx, neighbor in enumerate(nearest_neighbors):
        if include_first_neighbor:
            combs = list(map(lambda x: frozenset(x).union({idx}).union({neighbor[0]}),
                             combinations(neighbor[1:], partition_size - 2)))
        else:
            combs = list(map(lambda x: frozenset(x).union({idx}), combinations(neighbor, partition_size - 1)))
        partitions = partitions.union(set(combs))

    # for each partition compute the cost and utility
    utility = []
    utility_dict = {}
    objective = {}
    for partition in partitions:
        beds = excess[list(partition)]
        transfer = transfer_score(beds)
        xys = positions[list(partition)]
        solutions, cst, status, transfer = lp_problem(xys, beds, transfer, verbose=False)
        utility.append([partition, transfer, cst])
    utility = np.array(utility)
    transfer_stdev = np.std(utility[:, 1])
    cost_stdev = np.std(utility[:, 2])
    for partition, transfer, cst in utility:
        objective[partition] = (1 - alpha) * transfer / transfer_stdev - alpha * cst / cost_stdev
        utility_dict[partition] = [transfer, cst]
    partitions = list(partitions)
    return partitions, utility_dict, dataframe, num_hospitals, objective


def transfer_score(resources):
    """
    compute the maximum transfer
    :param resources: the amount of shortage/surplus in each location of the partition
    :return: maximum transfer
    """
    surplus = resources[resources > 0]
    shortage = resources[resources < 0]
    if len(surplus) == 0:
        return 0
    if len(shortage) == 0:
        return 0
    surplus = np.sum(surplus)
    shortage = np.sum(-shortage)
    return np.min([surplus, shortage])


def k_clique_from_combinations(utility=None, lagrange=3):
    """
    # TODO use dwave-networkx weighted maximum clique or weighted maximum independent set
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

def get_sampler(form: OptimizationParametersForm):
    """
    Given a set of user inputs, return the selected solver and a minimal set of default parameters
    :param form: user input form
    :return: solver, parameters
    """
    name = form.solver.data
    if name == 'SimulatedAnnealing':
        return SimulatedAnnealingSampler(), {}
    elif name == 'LeapHybridSampler':
        return LeapHybridSampler(), {'time_limit': float(form.time_limit.data)}
    elif name == 'TabuSampler':
        return TabuSampler(), {'timeout': int(form.time_limit.data) * 1000}
    else:
        raise ValueError

def get_empty_map(form: OptimizationParametersForm):
    """Creates a Folium map with hospital markers.
    :param form: User form specified by the class `OptimizationParametersForm`
    :return: folium.Map object
    """
    df = us_hospitals(int(form.num_hospitals.data))
    df['size'] = np.abs(df['excess_beds'])

    start_coords = (40.758896, -73.985130)
    zoom = 12 if len(df) > 25 else 13

    folium_map = folium.Map(location=start_coords, tiles=None, zoom_start=zoom, height=700, width=1800)
    folium.TileLayer(tiles='openstreetmap', opacity=0.5).add_to(folium_map)

    # Marker color is based on number of excess_beds (scale is from red (shortage) to blue (surplus))
    df['marker_color'] = pd.cut(df['excess_beds'], bins=8, labels=['#fc0009',
                                                                   '#e10435',
                                                                   '#b30963',
                                                                   '#910b81',
                                                                   '#5f0aad',
                                                                   '#4f08ba',
                                                                   '#2606de',
                                                                   '#1702f6'])

    # Add one marker per hospital
    for latitude, longitude, size, excess_beds, color in zip(df['latitude'], df['longitude'], df['size'], df['excess_beds'], df['marker_color']):
        folium.CircleMarker([latitude, longitude],
                            radius=0.25*abs(excess_beds),
                            tooltip=('Size: ' + str(size) + '<br>'
                                     'Latitude: ' + str(latitude) + '<br>'
                                     'Longitude: ' + str(longitude) + '<br>'
                                     'Excess beds: ' + str(excess_beds)),
                            fill=True,
                            stroke=False,
                            fill_color=color,
                            fill_opacity=0.8).add_to(folium_map)

    return folium_map

def add_result_marker(figure, dataframe, sorg, utility):
    """Adds a marker to figure representing one partition/result
    :param figure: folium.Map object to be added to
    :param dataframe: Pandas DataFrame containing hospital data
    :param sorg: immutable set containing one partition of hospitals
    :param utility: dict containing utility values
    :return: None
    """
    s = np.array(list(sorg))
    dfxy = dataframe.iloc[s]
    dfxy = dfxy[['longitude', 'latitude']]

    u = utility[sorg]

    if u[0] > 0:
        if len(s) > 2:
            hull = ConvexHull(dfxy.values)
            vertices = hull.vertices
        else:
            vertices = range(len(s))

        locations = [(dfxy.values[idx][1], dfxy.values[idx][0]) for idx in vertices]

        colors = ['red', 'blue', 'green', 'purple']
        color = np.random.choice(colors)

        folium.vector_layers.Polygon(locations,
                                     fill=True,
                                     stroke=True,
                                     color=color,
                                     fill_color=color,
                                     fill_opacity=0.3,
                                     opacity=0.2).add_to(figure)

        text = f'Transfers {u[0]:.2f} <br> Cost {u[1]:.2f}'
        cm = np.mean(dfxy.values[vertices], axis=0)

        folium.map.Marker([cm[1], cm[0]],
                          icon=DivIcon(icon_size=(150,36),
                          icon_anchor=(75,18),
                          html='<div style="font-size: 12pt">%s</div>' % text)).add_to(figure)

def plot_results(form: OptimizationParametersForm):
    """

    :param form:
    :return: figure, success, message, run_time, result
    """
    message = ''
    figure = get_empty_map(form)

    name = f'saved_problems/main_problem_{form.partition_size.data}_{form.num_hospitals.data}_{form.num_neighbors.data}_{form.alpha.data:.2f}'
    success = 0
    run_time = 0
    result = None
    if not exists('saved_problems/'):
        makedirs('saved_problems/')
    if exists(name):
        print('loading')
        with open(name, 'rb') as f:
            p_combinations, utility, dataframe, n, objective = pickle.load(f)
    else:
        p_combinations, utility, dataframe, n, objective = create_utility_function(form)
        print('writing')
        with open(name, 'wb') as f:
            pickle.dump((p_combinations, utility, dataframe, n, objective), f)
    if utility is None:
        message = f'Number of cities {n} is not divisible by partition size {form.partition_size.data}'
        return figure, success, message, run_time, result

    bqm, _, p_combinations = k_clique_from_combinations(utility=objective, lagrange=10)
    num_variables = len(set().union(*p_combinations))
    partition_size = len(p_combinations[0])

    sampler, params = get_sampler(form)
    t0 = time()
    try:
        if form.solver.data == 'SimulatedAnnealing':
            response = sampler.sample(bqm)
            beta_range = response.info['beta_range']
            t0 = time()
            response = sampler.sample(bqm, beta_range=beta_range)
            run_time = time() - t0
            nsw = int(float(form.time_limit.data) / run_time * 1000 / 10)
            run_time = 0
            while run_time < float(form.time_limit.data):
                t0 = time()
                response = dimod.concatenate((response, sampler.sample(bqm, num_sweeps=nsw, beta_range=beta_range)))
                run_time += time() - t0
            response = response.truncate(1)
        else:
            response = sampler.sample(bqm, **params).truncate(1)
            run_time = time() - t0
            if form.solver.data == 'LeapHybridSampler':
                run_time = response.info['run_time'] / 1e6

    except ValueError as err:
        message = str(err)
        success = 0
        run_time = 0
        result = None
        return figure, success, message, run_time, result
    variables = np.array(response.variables)

    num_variables = len(set().union(*p_combinations))
    num_partitions = num_variables // partition_size
    response = Result(response, p_combinations, variables, num_variables, utility,
                      num_partitions, run_time, solver=form.solver.data)
    if response.total_cost is None or response.total_utility is None or response.energy is None:
        message = f'No feasible solution found'
        success = 1
        result = None
        return figure, success, message, run_time, result
    sample = response.sample
    sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
    np.random.seed(123)
    for sorg in sol:
        add_result_marker(figure, dataframe, sorg, utility)

    success = 2
    return figure, success, message, run_time, response


class Result:
    def __init__(self, response, p_combinations, variables, num_variables, utility, k, t, solver):
        total_cost = None
        self.solver = solver
        total_utility = None
        self.t = t
        energy = None
        for sample, energy, occ in response.record:
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
        self.sample = response.truncate(1).record.sample[0]
        self.total_utility = total_utility
        self.total_cost = total_cost
        self.energy = energy

    def __repr__(self):
        return f'{self.solver:40s}: Utility {self.total_utility:.2f}, cost {self.total_cost:.2f}, energy {self.energy:.2f}, in {self.t:.2f} seconds'
