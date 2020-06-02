import numpy as np
import matplotlib.pyplot as plt
from get_graphs import distance_matrix
from itertools import product
from pulp import LpProblem, LpVariable, LpMinimize, LpInteger, lpSum, LpContinuous, LpStatus, LpBinary

np.random.seed(1234567)
n = 8
xy = np.random.rand(*(n, 2))
shortage = np.random.randint(-30, 31, size=n)
shortage = np.round(shortage - np.mean(shortage))
indp = shortage > 0
indn = shortage < 0

xyps = xy[indp]
xyns = xy[indn]

sps = shortage[indp]
sns = shortage[indn]

transfer = np.min([np.sum(sps), -np.sum(sns)])
print(transfer)
psize = len(sps)
nsize = len(sns)
prob = LpProblem("Transfer_cost", LpMinimize)
data = {}
iix = 0
for (idx, (xyp, sp)), (jdx, (xyn, sn)) in product(enumerate(zip(xyps, sps)), enumerate(zip(xyns, sns))):
    distance = np.sqrt(np.sum(np.square(xyp - xyn)))
    t = np.min([sp, -sn])
    data[(idx, jdx)] = [
        LpVariable(f'x_{iix}', cat=LpInteger, lowBound=0, upBound=t),
        distance,
        t,  # 2
        sp,  # 3
        -sn  # 4
    ]
    iix += 1

prob += lpSum([data[(i, j)][1] * data[(i, j)][0] for i in range(psize) for j in range(nsize)])
prob += lpSum([data[(i, j)][2] * data[(i, j)][0] for i in range(psize) for j in range(nsize)]) >= transfer
for i in range(psize):
    prob += lpSum([data[(i, j)][2] * data[(i, j)][0] for j in range(nsize)]) <= data[(i, 0)][3]
for j in range(nsize):
    prob += lpSum([data[(i, j)][2] * data[(i, j)][0] for i in range(psize)]) <= data[(0, j)][4]

print(data)
exit()
status = prob.solve()
print(LpStatus[status])
prob.writeLP('simple_model.lp')
solutions = np.zeros(len(data))
for variable in prob.variables():
    print(f"{variable.name} = {variable.varValue}")
    idx = int(variable.name.split('_')[-1])
    solutions[idx] = variable.varValue
cost = (prob.objective.value())
print(cost)
# exit()
#
# best_sol = None
# best_t = 0
# best_d = 1e100
# for sol in sols:
#     tt = sum([ts[i] * sol[i] for i in range(len(ds))])
#     dd = sum([ds[i] * sol[i] for i in range(len(ds))])
#     if tt >= transfer:
#         if dd < best_d:
#             best_d = dd
#             best_t = tt
#             best_sol = np.copy(sol)
# print(best_sol)
for idx, ((xyp, sp), (xyn, sn)) in enumerate(product(zip(xyps, sps), zip(xyns, sns))):
    plt.plot(*zip(xyp, xyn), color='k', alpha=0.25)
    plt.text(*xyp, str(int(sp)))
    plt.text(*xyn, str(int(sn)))
    v = solutions[idx]
    if v:
        # print(xyp, sp, xyn, sn, v)
        points = np.array(list(zip(xyp, xyn)))
        print(xyp, xyn, points)
        x = points[0]
        y = points[1]
        # plt.plot(*zip(xyp, xyn), linewidth=10, color='m', alpha=.2)
        plt.plot(x, y, linewidth=10, color='m', alpha=.2)
        plt.text(x.mean(), y.mean(), str(int(np.min([sp, -sn]))))
plt.scatter(*xyps.T, sps * 10, color='g', alpha=1)
plt.scatter(*xyns.T, -sns * 10, color='r', alpha=1)

plt.show()