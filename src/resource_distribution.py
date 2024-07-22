# Copyright 2024 D-Wave Systems Inc.
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

import pickle
import time
from os import makedirs
from collections import defaultdict, namedtuple
from itertools import combinations, filterfalse
from typing import Union, Tuple

import folium
import numpy as np
import pandas as pd
import dimod
from dimod import BinaryQuadraticModel
from dwave.system import LeapHybridSampler, LeapHybridCQMSampler
from neal import SimulatedAnnealingSampler
from src.enums import Formulation, SamplerType
from tabu import TabuSampler

from src.solve_lp import lp_problem, distance_matrix_haversine
from src.utils import check_feasibility, add_result_markers, get_transfer, get_cost

form_fields = ['formulation', 'num_hospitals', 'partition_size', 'num_neighbors', 'dof', 'solver',
               'time_limit']
FormInput = namedtuple('FormInput', form_fields, defaults=(None,)*len(form_fields))

result_fields = ['figure', 'total_cost', 'total_transfer', 'energy', 'error_msgs', 'run_time']
Result = namedtuple('Result', result_fields, defaults=(None,)*len(result_fields))


def create_utility_function(form: FormInput, hospital_df: pd.DataFrame, 
                            include_first_neighbor: bool = False) -> Tuple[dict, dict]:
    """Helper function for BQM solution. Given user parameters specified in `form` and hospital data, 
    create partitions of hospitals and compute the optimal cost and utility of each partition.

    Args:
        form: User input form.

        hospital_df: DataFrame containing hospital data for all hospitals in the problem.

        include_first_neighbor: To reduce problem complexity, always consider the first nearest neighbor.

    Returns:
        A 2-tuple containing dictionaries for utility (keys are hospital groupings, values are 
        (transfer, cost)), and objective (keys are hospital groupings, values are objective values).
    """
    positions = hospital_df[['longitude', 'latitude']].values
    excess = hospital_df['excess_beds'].values
    distance_matrix = distance_matrix_haversine(positions)
    
    # for each hospital find the first few nearest neighbors up to num_neighbors
    nearest_neighbors = []
    for i in range(form.num_hospitals):
        nearest_neighbors.append(np.argsort(distance_matrix[i])[1:form.num_neighbors+1])

    # find all partitions that include num_neighbors of the nearest neighbors
    partitions = set()
    for idx, neighbor in enumerate(nearest_neighbors):
        if include_first_neighbor:
            combs = map(lambda x: frozenset(x).union({idx, neighbor[0]}),
                        combinations(neighbor[1:], form.partition_size - 2))
        else:
            combs = map(lambda x: frozenset(x).union({idx}),
                        combinations(neighbor, form.partition_size - 1))

        partitions = partitions.union(set(combs))

    # for each partition compute the cost and utility
    utility = []
    utility_dict = {}
    objective = {}
    for partition in partitions:
        beds = excess[list(partition)]
        transfer = get_transfer(beds)
        xys = positions[list(partition)]
        solutions, cst, status, transfer = lp_problem(xys, beds, transfer, verbose=False)
        utility.append([partition, transfer, cst])

    utility = np.array(utility)
    transfer_stdev = np.std(utility[:, 1])
    cost_stdev = np.std(utility[:, 2])

    alpha = form.dof
    for partition, transfer, cst in utility:
        if transfer_stdev != 0 and cost_stdev != 0:
            objective[partition] = (1 - alpha) * transfer / transfer_stdev - alpha * cst / cost_stdev
        else:
            objective[partition] = (1 - alpha) * transfer - alpha * cst

        utility_dict[partition] = (transfer, cst)

    return utility_dict, objective


def k_clique_from_combinations(utility: dict, lagrange: int = 3) -> Tuple[dimod.BinaryQuadraticModel, list]:
    """Helper function for BQM solution.
    # TODO use dwave-networkx weighted maximum clique or weighted maximum independent set
    This function naively generates all possible combinations of size
    number_variables/num_partitions and then using a given utility function
    (generated randomly here), creates an objective function that find the
    clique of size num_partitions that has the maximum utility function.

    Args:
        utility: Keys are groups (frozensets) of hospitals (represented by indices for a dataframe). 
                 Values are the objectives.

        lagrange: Lagrange parameter to weight constraints (no edges within set) versus objective 
                  (largest set possible).

    Returns:
        The BQM and a list of all possible combinations of hospital groupings.
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
    return bqm, p_combinations


def get_sampler(form: FormInput) -> Tuple[dimod.Sampler, dict]:
    """Given a set of user inputs, return the selected solver and a minimal set of default parameters.

    Args:
        form: User input form.

    Returns:
        The user selected solver and default parameters for the solver.
    """
    sampler_type = form.solver
    if isinstance(sampler_type, int):
        sampler_type = SamplerType(sampler_type)

    if sampler_type is SamplerType.SIM_ANNEAL:
        return SimulatedAnnealingSampler(), {}
    elif sampler_type is SamplerType.BQM:
        solver = LeapHybridSampler.default_solver
        solver.update(name__regex=".*(?<!bulk)$")  
        sampler = LeapHybridSampler(solver=solver)
        return sampler, {'time_limit': float(form.time_limit), 
                         'label': 'Demo from Leap - Resource Distribution Optimization'}
    elif sampler_type is SamplerType.TABU:
        return TabuSampler(), {'timeout': int(form.time_limit) * 1000}
    elif sampler_type is SamplerType.CQM:
        solver = LeapHybridCQMSampler.default_solver
        solver.update(name__regex=".*(?<!bulk)$")  
        sampler = LeapHybridCQMSampler(solver=solver)
        return sampler, {'time_limit': float(form.time_limit),
                         'label': 'Demo from Leap - Resource Distribution Optimization'}
    else:
        raise ValueError(f"Incorrect sampler: {sampler_type}")


def solve_bqm(hospital_df: pd.DataFrame, form: FormInput, 
              sampler: dimod.Sampler, params: dict) -> Tuple[dict, float, float]:
    """Builds a BQM from the user input and finds a solution.

    Args:
        hospital_df: DataFrame containing hospital data for all hospitals in the problem.

        form: User input form.

        sampler: A `dimod` sampler object.

        params: Default parameters for the sampler.

    Returns:
        Group data from the best solution found (keys are frozensets of hospitals (represented by 
        indices for `hospital_df`), values are (transfer, cost)), the energy of the best solution,
        and the run time.
    """
    # Get problem
    makedirs('saved_problems/', exist_ok=True)
    name = "saved_problems/main_problem_{}_{}_{}_{:.2f}".format(form.partition_size, 
                                                                form.num_hospitals, 
                                                                form.num_neighbors, 
                                                                form.dof)
    try:
        with open(name, 'rb') as f:
            utility, objective = pickle.load(f)
            print('Load saved problem file: ', name)
    except:
        print('Writing new problem file: ', name)
        utility, objective = create_utility_function(form, hospital_df)
        if utility and objective:
            with open(name, 'wb') as f:
                pickle.dump((utility, objective), f)

    # Get BQM and all combinations of hospitals to use later
    bqm, p_combinations = k_clique_from_combinations(objective, lagrange=10)

    if len(bqm) == 1:
        # Only one group, so no need to sample
        response = dimod.SampleSet.from_samples_bqm({0: 1}, bqm)
        run_time = 0
    else:
        # Solve problem
        if form.solver is SamplerType.SIM_ANNEAL:
            response = sampler.sample(bqm)
            beta_range = response.info['beta_range']

            t0 = time.perf_counter()
            response = sampler.sample(bqm, beta_range=beta_range)
            run_time = time.perf_counter() - t0

            nsw = int(float(form.time_limit) / run_time * 1000 / 10)

            run_time = 0
            t0 = time.perf_counter()
            while run_time < float(form.time_limit):
                onerun = sampler.sample(bqm, num_sweeps=nsw, beta_range=beta_range).truncate(1)
                response = dimod.concatenate((response, onerun)).truncate(1)
                run_time = time.perf_counter() - t0

        else:
            t0 = time.perf_counter()
            response = sampler.sample(bqm, **params).truncate(1)
            run_time = time.perf_counter() - t0

            if form.solver is SamplerType.BQM:
                run_time = response.info['run_time'] / 1e6

    variables = np.array(response.variables)
    sample = response.record.sample[0]
    energy = response.record.energy[0]
    
    # Parse sample and get the previously calculated transfer and cost for each group
    sol = [p_combinations[x] for idx, x in enumerate(variables) if sample[idx]]
    group_data = dict()
    for group in sol:
        transfer, cost = utility[group]
        group_data[group] = (transfer, cost)

    return group_data, energy, run_time


def build_cqm(hospital_df: pd.DataFrame, distances: dict) -> dimod.ConstrainedQuadraticModel:
    """Build CQM from data provided.
    
    Args:
        hospital_df: Contains hospital data for all hospitals in the problem.

        distances: Keys are pairs of hospital names and values are the distances between the 
                   two hospitals.

    Return:
        The CQM.
    """
    # put the data into forms that are easier to manage
    hospitals = dict(zip(hospital_df['name'], hospital_df['excess_beds']))

    # easy optimization, the number of groups cannot be larger than the number
    # of hospitals with a positive excess_beds
    num_groups = sum(beds >= 0 for beds in hospitals.values())

    # create a variable matching each hospital to a group
    variables = {}
    for hospital in hospitals:
        for group in range(num_groups):
            variables[hospital, group] = dimod.Binary((hospital, group))

    # build the CQM
    cqm = dimod.ConstrainedQuadraticModel()

    # enforce the constraint that no hospital can be in more than one group
    for hospital in hospitals:
        cqm.add_discrete([(hospital, group) for group in range(num_groups)])

    # enforce the constraint that each group must have a net positive number of beds
    for group in range(num_groups):
        cqm.add_constraint(sum(variables[hospital, group]*beds for hospital, beds in hospitals.items()) >= 0)

    # minimize the transfer cost
    objective = 0
    for h0, beds0 in hospitals.items():
        for h1, beds1 in hospitals.items():
            if beds0 > 0 and beds1 < 0:
                for group in range(num_groups):
                    objective += variables[h0, group]*variables[h1, group]*distances[h0, h1]
    cqm.set_objective(objective)

    return cqm


def get_results(form: FormInput, hospital_df: pd.DataFrame, figure: folium.Map) -> Result:
    """Generate problem based on user input and solve.
    
    Args:
        form: User input form.

        hospital_df: Contains hospital data for all hospitals in the problem.

        figure: Map to add result markers to.
    
    Returns:
        Result tuple containing solution.
    """
    # Calculate the distances between hospitals
    distance_matrix = distance_matrix_haversine(hospital_df[['longitude', 'latitude']].values)
    distances = dict(((hospital_df['name'][i], hospital_df['name'][j]), distance_matrix[i, j])
                    for i in range(form.num_hospitals) for j in range(form.num_hospitals))

    sampler, params = get_sampler(form)

    print("Solving problem with the {}".format(sampler))

    if form.solver is SamplerType.CQM:
        cqm = build_cqm(hospital_df, distances)

        sampleset = sampler.sample_cqm(cqm, **params)
        run_time = sampleset.info['run_time'] / 1e6

        try:
            # get the lowest-energy feasible solution
            solution = next(filterfalse(lambda d: not getattr(d, 'is_feasible'), list(sampleset.data())))
        except:
            # no feasible solution, so use the first one
            solution = sampleset.first

        energy = solution.energy
    else:
        # solve problem as a bqm
        if form.formulation is Formulation.CQM:
            # on the cqm page, a bunch of bqm tuning parameters are missing -> fill them in here
            partition_size = 0
            sizes = [5, 4, 3, 2]
            for size in sizes:
                if size != form.num_hospitals and form.num_hospitals % size == 0:
                    # make sure partition size is divisible by the number of hospitals
                    partition_size = size
                    break

            if partition_size == 0:
                # no other option, one partition
                partition_size = form.num_hospitals

            form = FormInput(
                num_hospitals=form.num_hospitals,
                partition_size=partition_size,
                num_neighbors=min(2*partition_size, 8),
                dof=0.2,   # decreasing dof maximizes transfer
                solver=form.solver,
                time_limit=form.time_limit
            )

        try:
            solution, energy, run_time = solve_bqm(hospital_df, form, sampler, params)
        except ValueError as err:
            print(err)  # report error but move on
            return None

    # parse solution (and get cost and transfer data for each group)
    groups = get_group_data(hospital_df, distances, solution)

    # Print out groups and do some validation
    for group in groups:
        print(group)

        max_cost = get_cost(group.names, group.excess_beds, distances)
        if max_cost < group.cost:
            # TODO: find out why optimal cost is sometimes greater than max cost
            print("Something strange: max cost: {}, optimal cost: {}".format(max_cost, group.cost))

        max_transfer = get_transfer(group.excess_beds)
        if max_transfer < group.transfer:
            print("Something strange: max transfer: {}, optimal transfer: {}".format(max_transfer, group.transfer))

    # check feasibility of solution
    net_positive_beds, only_one_group = check_feasibility(groups)

    error_msgs = []
    if not net_positive_beds:
        error_msgs.append("One or more groups did not have a net positive number of excess beds.")
    
    if not only_one_group:
        error_msgs.append("One or more hospitals were in more than one group.")

    # add results to the map
    add_result_markers(figure, groups)

    # calculate totals
    total_cost = 0
    total_transfer = 0

    for group in groups:
        total_cost += group.cost
        total_transfer += group.transfer

    print("Total cost: ", total_cost)
    print("Total transfer: ", total_transfer)

    return Result(figure=figure, total_cost=total_cost, total_transfer=total_transfer, energy=energy, 
                  error_msgs=error_msgs, run_time=run_time)


def get_group_data(hospital_df: pd.DataFrame, distances: dict, solution: Union[tuple, dict]) -> list:
    """Parse the solution provided and return a list of hospital group information in the form of a
    HospitalGroup tuple.

    Args:
        hospital_df: DataFrame containing hospital data for all hospitals in the problem.

        distances: Keys are pairs of hospital names and values are the distances between the 
                   two hospitals.

        solution: Either the lowest energy sample containing the solution, or a dict in which keys 
                  are array-like objects that each represent a group of hospitals and values are the
                  (transfer, cost) of the group.

    Return:
        List of HospitalGroup.
    """
    group_data = []

    if isinstance(solution, tuple):
        is_satisfied = solution.is_feasible if hasattr(solution, 'is_feasible') else None

        # split hospitals into groups according to the sample
        groups = defaultdict(list)
        for var, value in solution.sample.items():
            if isinstance(var, tuple) and value:
                groups[var[1]].append(var[0])

        # get data for each group
        for _, hospital_names in groups.items():
            group_df = hospital_df.loc[hospital_df['name'].isin(hospital_names)][['name', 
                                                                                  'longitude', 
                                                                                  'latitude', 
                                                                                  'excess_beds']]
            group_data.append(HospitalGroup(group_df, distances, net_positive_beds=is_satisfied))
    
    elif isinstance(solution, dict):
        for group in solution:
            transfer, cost = solution[group]    # already calculated when building the bqm
            group_df = hospital_df.iloc[np.array(list(group))][['name', 
                                                                'longitude', 
                                                                'latitude', 
                                                                'excess_beds']]
            group_data.append(HospitalGroup(group_df, distances, transfer=transfer, cost=cost))

    else:
        raise ValueError("Wrong solution type.")

    return group_data


class HospitalGroup:
    def __init__(self, group_df, distances, transfer=None, cost=None, net_positive_beds=None):
        """Class for holding information about hospital groupings.
        
        Args:
            group_df (pd.DataFrame):
                Contains hospital data for one group.

            distances (dict):
                Keys are pairs of hospital names and values are the distances between the two hospitals.

            transfer (float, optional):
                Number of beds that can be transferred in the group. Calculated if not passed in.

            cost (float, optional):
                Sum of distances between pairs of hospitals in the group, in which one hospital has 
                a shortage of beds and the other has a surplus. Calculated if not passed in.

            net_positive_beds (bool, optional):
                True if the group has a net positive number of beds. Calculated if not passed in.
        """
        self.names = group_df['name'].values
        self.positions = group_df[['longitude', 'latitude']].values
        self.excess_beds = group_df['excess_beds'].values


        self.transfer = transfer if transfer else get_transfer(self.excess_beds)
        self.cost = cost if cost else get_cost(self.names, self.excess_beds, distances)

        if net_positive_beds is None:
            total_beds = np.sum(self.excess_beds)
            net_positive_beds = total_beds >= 0

        self.net_positive_beds = net_positive_beds

    
    def __repr__(self):
        return "\nGroup: {}\n, Excess Beds: {}\n, Transfer: {}\n, Cost: {}\n".format(self.names,
                                                                                     self.excess_beds,
                                                                                     self.transfer,
                                                                                     self.cost)
