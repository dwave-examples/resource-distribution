import itertools

import dimod

from neal import Neal
from dwave.system import LeapHybridCQMSampler
from resource_distribution import us_hospitals
from solve_lp import distance_matrix_haversine

num_hospitals = 50

# load the data
data = us_hospitals(num_hospitals)

# make sure we have a net surplus of beds
total_beds = sum(data['excess_beds'])
if total_beds < 0:
    data['excess_beds'] -= total_beds

# calculate the distances
distance_matrix = distance_matrix_haversine(data[['longitude', 'latitude']].values)


# put the data into forms that are easier to manage
hospitals = dict(zip(data['name'], data['excess_beds']))
distances = dict(((data['name'][i], data['name'][j]), distance_matrix[i, j])
                 for i in range(num_hospitals) for j in range(num_hospitals))


# easy optimization, the number of groups cannot be larger than the number
# of hospitals with a positive excess_beds
num_groups = sum(beds >= 0 for beds in hospitals.values())


# create a variable matching each hospital to a group
variables = {}
for hospital in hospitals:
    for group in range(num_groups):
        variables[hospital, group] = dimod.Binary((hospital, group))

print('num variables:', len(variables))

# build the CQM
cqm = dimod.ConstrainedQuadraticModel()

# enforce the constraint that no hospital can be in more than one group
for hospital in hospitals:
    cqm.add_discrete([(hospital, group) for group in range(num_groups)])

# enforce the constraint that each group must have a net positive number of beds
for group in range(num_groups):
    cqm.add_constraint(sum(variables[hospital, group]*beds for hospital, beds in hospitals.items()) >= 0)

# we can enforce the exactly-4 constraint, but we don't need to

# minimize the transfer cost
objective = 0
for h0, beds0 in hospitals.items():
    for h1, beds1 in hospitals.items():
        if beds0 > 0 and beds1 < 0:
            for group in range(num_groups):
                objective += variables[h0, group]*variables[h1, group]*distances[h0, h1]
cqm.set_objective(objective)


bqm, inverter = dimod.cqm_to_bqm(cqm)

print(bqm.num_variables)

bqm_sampler = Neal()

print(bqm_sampler.sample(bqm).first.energy)


sampler = LeapHybridCQMSampler(solver=dict(name='hybrid_constrained_quadratic_model_version1_test'))
sampleset = sampler.sample_cqm(cqm, time_limit=10)

# get the lowest-energy feasible solution
datum = next(itertools.filterfalse(lambda d: not getattr(d, 'is_feasible'), list(sampleset.data())))

print("total cost:",  datum.energy)

# groups = [list() for _ in range(num_groups)]

# for (hospital, group), value in datum.sample.items():
#     if value:
#         groups[group].append(hospital)

# for group in groups:
#     if not group:
#         continue

#     print(group)
#     print(sum(hospitals[hospital] for hospital in group))
