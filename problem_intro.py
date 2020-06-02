import numpy as np
import matplotlib.pyplot as plt
from itertools import product
from pulp import LpProblem, LpVariable, LpMinimize, LpInteger, lpSum, LpContinuous, LpStatus, LpBinary


def main():
    np.random.seed(12346)
    n = 8
    xy = np.random.rand(*(n, 2))
    # shortage = np.random.randint(-30, 31, size=n)
    # shortage = np.round(shortage - np.mean(shortage))
    shortage = np.array([4, -6, 2, -2, 2, -4, 6, -2])
    indp = shortage > 0
    indn = shortage < 0

    xyps = xy[indp]
    xyns = xy[indn]

    sps = shortage[indp]
    sns = shortage[indn]

    transfer = np.min([np.sum(sps), -np.sum(sns)])
    solutions, cost, status, limit = lp_problem(xy, shortage, transfer)
    print(transfer, limit)
    for idx, ((xyp, sp), (xyn, sn)) in enumerate(product(zip(xyps, sps), zip(xyns, sns))):
        # plt.plot(*zip(xyp, xyn), color='k', alpha=0.25)
        # plt.text(*xyp, str(int(sp)))
        # plt.text(*xyn, str(int(sn)))
        v = solutions[idx]
        if v:
            points = np.array(list(zip(xyp, xyn)))
            x = points[0]
            y = points[1]
            plt.plot(x, y, linewidth=10, color='m', alpha=.2)
            plt.text(x.mean(), y.mean(), str(int(np.min([sp, -sn]))))
    plt.scatter(*xyps.T, sps ** 2 * 10, color='g', alpha=1)
    plt.scatter(*xyns.T, sns ** 2 * 10, color='r', alpha=1)
    plt.title(f'Transfer {limit}, cost {cost:.2f}')
    plt.axis('off')
    plt.savefig('static/partition_with_distance.png')
    plt.show()


def lp_problem(xy, shortage, transfer, verbose=False):
    indp = shortage > 0
    indn = shortage < 0

    xyps = xy[indp]
    xyns = xy[indn]

    sps = shortage[indp]
    sns = shortage[indn]
    psize = len(sps)
    nsize = len(sns)
    if psize == 0 or nsize == 0:
        return [], 0, 'Optimal', 0
    prob = LpProblem("Transfer_cost", LpMinimize)
    data = {}
    iix = 0
    for (idx, (xyp, sp)), (jdx, (xyn, sn)) in product(enumerate(zip(xyps, sps)), enumerate(zip(xyns, sns))):
        distance = np.sqrt(np.sum(np.square(xyp - xyn)))
        t = np.min([sp, -sn])
        data[(idx, jdx)] = [
            LpVariable(f'x_{iix}', cat=LpBinary),
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

    status = prob.solve()
    status = LpStatus[status]
    solutions = np.zeros(len(data))
    for variable in prob.variables():
        if verbose:
            print(f"{variable.name} = {variable.varValue}")
        idx = int(variable.name.split('_')[-1])
        solutions[idx] = variable.varValue
    cost = (prob.objective.value())

    if status != 'Optimal':
        return lp_problem(xy, shortage, transfer - 1)

    return solutions, cost, status, transfer


if __name__ == '__main__':
    main()