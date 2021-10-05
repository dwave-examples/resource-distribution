# Resource Distribution

The ongoing Covid-19 pandemic has resulted in millions of people being infected and has 
overwhelmed health systems. Many hospitals are facing a critical shortage of essential resources 
such as invasive ventilators, ICU beds, and personal protective gear. It is imperative to 
optimize the allocation of resources. The goal is to group hospitals in such a way that shared 
resources are maximized within each group while ensuring fair distribution across different groups.

In resource-distribution optimization, we would like to find the optimal partitioning of a fixed 
amount of resources to users or processes such that the total cost is minimized or utility is maximized.
We are going to consider two scenarios. In the first scenario, the objective is at most a
quadratic function of resources. For example, the utility function of medical centres only depends on 
the location and other attributes of each medical centre or each pair of medical centres. In the 
second scenario, the objective can be more general, and it could depend on the collective property 
of a set of variables.

## Usage

To run the web-app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

You'll see that the app is now running on port 5000 of your local. Now, you can
copy and paste the provided link into your browser for access.

## Snapshot

![demo](demo_app.png)
