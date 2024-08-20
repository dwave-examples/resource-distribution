[![Open in GitHub Codespaces](
  https://img.shields.io/badge/Open%20in%20GitHub%20Codespaces-333?logo=github)](
  https://codespaces.new/dwave-examples/resource-distribution?quickstart=1)

# Resource Distribution

The Covid-19 pandemic has resulted in millions of people being infected and 
has overwhelmed health systems. Many hospitals are facing a critical shortage of 
essential resources such as invasive ventilators, ICU beds, and personal protective gear. 
It is imperative to optimize the allocation of resources. The goal is to group hospitals 
in such a way that shared resources are maximized within each group while ensuring fair 
distribution across different groups.

This demo presents two ways of formulating the problem: as a binary quadratic model (BQM)
and as a constrained quadratic model (CQM).

![demo](static/demo.png)

## Installation

You can run this example without installation in cloud-based IDEs that support the
[Development Containers specification](https://containers.dev/supporting) (aka "devcontainers")
such as GitHub Codespaces.

For development environments that do not support `devcontainers`, install requirements:

```bash
pip install -r requirements.txt
```

If you are cloning the repo to your local system, working in a
[virtual environment](https://docs.python.org/3/library/venv.html) is recommended.

## Usage
Your development environment should be configured to access the
[Leap&trade; Quantum Cloud Service](https://docs.ocean.dwavesys.com/en/stable/overview/sapi.html).
You can see information about supported IDEs and authorizing access to your Leap account
[here](https://docs.dwavesys.com/docs/latest/doc_leap_dev_env.html).

Run the following terminal command to start the Dash app:

```bash
python app.py
```

Access the user interface with your browser at http://127.0.0.1:8050/.

The demo program opens an interface where you can configure problems and submit these problems to
a solver.

Configuration options can be found in the [demo_configs.py](demo_configs.py) file.

> [!NOTE]\
> If you plan on editing any files while the app is running,
please run the app with the `--debug` command-line argument for live reloads and easier debugging:
`python app.py --debug`


## Problem Formulation

![home-img](static/partitioning.png)

### BQM

In the BQM formulation, the goal is to divide the hospitals into groups such that the maximum
number of transfers is achieved at minimum cost. Transfer is quantified as the smaller
number between total excess and total shortage in a group of hospitals. Cost is the sum of all
costs associated with transferring resources from one hospital to another: In this demonstration,
only distance is considered as a cost.

#### Variables

- **Partition Size**: The size of the groups to divide the hospitals into. If there are 12 hospitals
and the partition size is 4, the hospitals will be divided into 3 groups of 4.
- **Number of Neighbors**: Finding all possible groups of size `partition_size` is very time
consuming, instead we will only consider the possible groups within the `num_neighbors` closest
neighbors. If `num_neighbors` is 8, the 9th farthest away hospital from hospital x will not be
permitted in groups containing hospital x.
- **Distance Objective Fraction**: The balance between optimizing for maximum transfer or
minimum distance traveled cost. If the distance objective fraction is low the transfer is high.
If the DOF is high the transfer is low and the distance traveled/cost is low.

![home-img](static/partition_with_distance.png)

### CQM

The BQM formulation requires multiple mathematical transformations to run on an unconstrained
solver: the original problem is reformulated as a maximum-independent-set problem.

The CQM formulation enables the direct solution of the original problem in an intuitive way.

```
objective = 0
for i, beds0 in hospitals.items():
    for j, beds1 in hospitals.items():
        if beds0 > 0 and beds1 < 0:
            for g in range(num_groups):
                objective += distances[i, j]*variables[i, g]*variables[j, g]
cqm.set_objective(objective)
```

We now have a CQM that is ready to be sampled with the `LeapHybridCQMSampler`.

In the code above, note that:
- `cqm` is a `dimod.ConstrainedQuadraticModel`
- `hospitals` is a `dict` in which keys are hospital names and values
are the number of excess beds in each hospital
- `num_groups` is the number of groups to separate the hospitals into
- `variables` is a `dict` in which keys are `(i, g)` 
and values are the binary variables that determine whether hospital `i` should be 
in group `g`
- `distances` is a `dict` in which keys are pairs of hospitals and 
values are the distances between the two hospitals

## References

[1] Bass, Gideon, et al. "Heterogeneous quantum computing for satellite constellation optimization:
solving the weighted k-clique problem." Quantum Science and Technology 3.2 (2018): 024010.

## License

Released under the Apache License 2.0. See [LICENSE](LICENSE) file.
