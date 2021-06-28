import os

import streamlit as st

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_page():
    """Runs when user visits home page."""
    st.write("The ongoing Covid-19 pandemic has caused millions of people being infected and has \
             overwhelmed the health system. Many hospitals are facing a critical shortage for \
             essential resources such as invasive ventilators, ICU beds and personal protective \
             gears. It becomes imperative to optimize the allocation of resources. The goal is to \
             group hospitals in such a way that shared goods and services are maximized within each \
             of the groups while ensuring fair distribution across different groups. In resource \
             distribution optimization, we would like to find the optimal partitioning of a fixed \
             amount of resources to users or processes such that the total cost is minimized or \
             utility is maximized.")

    _, center, __ = st.beta_columns([1,1,1])
    center.image(os.path.join(root, "assets/partitioning.png"), use_column_width=True)

    st.subheader("Utility Function")

    st.write("The goal is to divide the medical centers into groups such that the maximum amount of \
             transfer is achieved at minimum cost. The transfer is quantified as the smaller number \
             of total excess and total shortage. The cost is the sum of all costs associated with \
             transferring resources from one place to another. Let’s say that there are eight medical \
             centers with the various number of ICU beds $u = (a_1, ..., a_8)$. The values $a_i$ \
             can be positive (excess) or negative (shortage). Let’s assume that $u_p = (a_1, ..., a_4)$ \
             are positive and $u_n = (a_5, ..., a_8)$ are negative. The transfer is equal to:")

    st.write("$$\n t = min(\sum_{i \in u_p} a_i, -\sum_{i \in u_n} a_i) \n$$")

    st.write("For example, if the magnitude of positive ones is smaller, transfer is equal to the \
             magnitude of $\sum_{i \in u_p} a_i$. The cost for each group $u$ is calculated for \
             pairs of centers for which a transfer only occurs, i.e. between members of $u_p$ and \
             $u_n$ and not within. So all the possibilities are:")

    st.write("$$\n c = \sum_{i \in u_p, j \in u_n} d_{i,j} x_{i,j} \n$$")

    st.write("Finally, we can define utility as a balance between cost and transfer:")

    st.write("$$\n U[u] = (1 - \\alpha) t - \\alpha c \n$$")

    _, center, __ = st.beta_columns([1,1,1])
    center.image(os.path.join(root, "assets/partition_with_distance.png"), use_column_width=True)

    st.subheader("Formulation")
    st.write("Given the utility function above, or any utility function that can compute a value for \
             a given subset $u$, we can use the following k-clique problem to find the best \
             division of medical centers to k groups [1]. First, we define the set of partitions \
             of size $n/k$ as:")
    st.write("$$\n \mathcal{V} = \\left\{ u: \\forall ~ u \\subset S ~\land ~|u| = \\frac{n}{k} \\right\} \n$$")

    st.write("We can define the set of edges as a pair of nodes that share elements (this is the \
             complement set of the original definition in [1]).")

    st.write("$$\n \mathcal{E} = \left\{ (u, v): \\forall ~ u,v \in \mathcal{V} ~\\land ~~ u \cap v \\neq \{\} \\right\}. \n$$")

    st.write("Because the nodes in $\mathcal{E}$ are derived from partitions of size $n/k$, \
             there can be no clique larger than $k$. Therefore, all we need to do is to solve the \
             weighted maximum independent set problem with weights equal to the utility function and \
             some regularization factor. If the utility function is defined as: \
             $U: \mathcal{V} \\rightarrow R$, we can write the objective function as:")

    st.write("$$\n H = - \sum_u (U_u + R)~ x_u + \lambda \sum_{u, n \in \mathcal{E}} x_u x_u \n$$")

    st.write("where $x_u$ is a binary variable that decides if the group $u$ is selected.")

    st.markdown("""---""")
    st.write("1] Bass, Gideon, et al. 'Heterogeneous quantum computing for satellite constellation \
            optimization: solving the weighted k-clique problem.' Quantum Science and Technology \
            3.2 (2018): 024010.")
