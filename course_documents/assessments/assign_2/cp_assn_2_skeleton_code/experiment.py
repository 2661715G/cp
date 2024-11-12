import networkx as nx
import random
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from submitted_solution import run_cp, run_ilp
import time
from scipy.stats import ttest_rel, linregress
import seaborn as sns

def generate_random_graphs(num_graphs=30, max_nodes=110):
    random_graphs = []
    
    for _ in range(num_graphs):
        dimensions = random.choice([1, 2, 3])  # Choose between 1D, 2D, or 3D graph
        num_nodes = random.randint(5, max_nodes)
        
        if dimensions == 1:
            # For 1D graphs, connect nodes randomly with a probability inversely related to the number of nodes
            p = min(0.3, 5 / num_nodes)  # Set connection probability
            graph = nx.gnp_random_graph(num_nodes, p)
        
        elif dimensions == 2:
            # For 2D graphs, create a grid structure, then add random edges
            side_length = int(num_nodes ** 0.5)
            graph = nx.grid_2d_graph(side_length, side_length)
            graph = nx.convert_node_labels_to_integers(graph)
            
            # Add additional random edges to make connections more random
            extra_edges = int(0.3 * graph.number_of_edges())  # 30% more random edges
            nodes = list(graph.nodes())
            for _ in range(extra_edges):
                u, v = random.sample(nodes, 2)
                if not graph.has_edge(u, v):
                    graph.add_edge(u, v)
        
        else:
            # For 3D graphs, create a 3D grid structure, then add random edges
            side_length = int(num_nodes ** (1/3))
            graph = nx.grid_graph(dim=[side_length] * 3)
            graph = nx.convert_node_labels_to_integers(graph)
            
            # Add extra random edges
            extra_edges = int(0.3 * graph.number_of_edges())  # 30% more random edges
            nodes = list(graph.nodes())
            for _ in range(extra_edges):
                u, v = random.sample(nodes, 2)
                if not graph.has_edge(u, v):
                    graph.add_edge(u, v)
        
        random_graphs.append(graph)
    
    return random_graphs

def run_experiments_and_save_results(num_graphs=30, max_nodes=110, timeout=150000):
    graphs = generate_random_graphs(num_graphs, max_nodes)
    results = []

    for i, graph in enumerate(graphs):
        start_node = random.choice(list(graph.nodes()))
        
        # Run ILP
        ilp_result = run_ilp(graph, start_node, timeout)
        ilp_time = ilp_result["run_time"]
        
        ilp_timed_out = ilp_result["Timeout"]
        if ilp_timed_out:
            ilp_time = 150  # Set to 150 seconds in case of timeout

        results.append({
            "Solver": "ILP",
            "Graph_Index": i,
            "Nodes": len(graph.nodes()),
            "Optimal_Result": ilp_result["num_saved"],
            "Time_Taken": ilp_time,
            "Timed_Out": ilp_timed_out
        })

        # Run CP
        cp_result = run_cp(graph, start_node, timeout)
        cp_time = cp_result["run_time"]
        
        cp_timed_out = cp_result["Timeout"]
        if cp_timed_out:
            cp_time = 150  # Set to 150 seconds in case of timeout

        results.append({
            "Solver": "CP",
            "Graph_Index": i,
            "Nodes": len(graph.nodes()),
            "Optimal_Result": cp_result["num_saved"],
            "Time_Taken": cp_time,
            "Timed_Out": cp_timed_out
        })
    
    # Save results to CSV
    df = pd.DataFrame(results)
    df.to_csv("experiment_results.csv", index=False)

    # Plot results
    plt.figure(figsize=(10, 6))
    
    # Plot ILP results
    ilp_data = df[df["Solver"] == "ILP"]
    plt.scatter(
        ilp_data["Nodes"], 
        np.where(ilp_data["Timed_Out"], 150, ilp_data["Time_Taken"]), 
        color="green", alpha=0.5, label="ILP"
    )

    # Plot CP results
    cp_data = df[df["Solver"] == "CP"]
    plt.scatter(
        cp_data["Nodes"], 
        np.where(cp_data["Timed_Out"], 150, cp_data["Time_Taken"]), 
        color="blue", alpha=0.5, label="CP"
    )

    # Configure plot
    plt.xlabel("Total Nodes in Graph")
    plt.ylabel("Time Taken (seconds)")
    plt.title("Performance Comparison of ILP and CP Solvers on Firefighter Problem")
    plt.legend()
    plt.show()

def calculate_p_value(file_path="experiment_results.csv"):
    # Load the data
    df = pd.read_csv(file_path)

    # Separate data for ILP and CP solvers
    ilp_times = df[df["Solver"] == "ILP"].sort_values("Graph_Index")["Time_Taken"].values
    cp_times = df[df["Solver"] == "CP"].sort_values("Graph_Index")["Time_Taken"].values

    # Ensure we have equal-length paired data
    if len(ilp_times) != len(cp_times):
        raise ValueError("Mismatch in the number of instances for ILP and CP.")

    # Calculate the paired t-test for performance differences
    t_stat, p_value = ttest_rel(ilp_times, cp_times)

    print("Paired t-test results:")
    print(f"t-statistic: {t_stat}")
    print(f"p-value: {p_value}")
    
    return p_value

def count_better_performances(csv_file):
    # Load the data
    df = pd.read_csv(csv_file)

    # Initialize counters
    ilp_better_count = 0
    cp_better_count = 0
    tie_count = 0
    timeout_count = 0

    # Group by 'Graph_Index' to compare solvers for each instance
    grouped = df.groupby("Graph_Index")
    
    for graph_index, group in grouped:
        # Separate ILP and CP results
        ilp_row = group[group['Solver'] == 'ILP']
        cp_row = group[group['Solver'] == 'CP']
        
        # Extract performance metrics
        ilp_time = ilp_row['Time_Taken'].values[0]
        cp_time = cp_row['Time_Taken'].values[0]
        ilp_result = ilp_row['Optimal_Result'].values[0]
        cp_result = cp_row['Optimal_Result'].values[0]

        # Handle timeouts based on Time_Taken exceeding 150 seconds
        ilp_timed_out = ilp_time > 150
        cp_timed_out = cp_time > 150
        
        if ilp_timed_out or cp_timed_out:
            timeout_count += 1
            # If only one solver timed out, the other solver gets a win
            if ilp_timed_out and not cp_timed_out:
                cp_better_count += 1
            elif cp_timed_out and not ilp_timed_out:
                ilp_better_count += 1
            continue  # Skip further comparison if either solver timed out

        # Compare results if no timeouts
        if ilp_result > cp_result:  # Higher optimal result indicates better performance
            ilp_better_count += 1
        elif cp_result > ilp_result:
            cp_better_count += 1
        else:  # Results tie, compare time
            if ilp_time < cp_time:
                ilp_better_count += 1
            elif cp_time < ilp_time:
                cp_better_count += 1
            else:
                tie_count += 1

    # Return results in a dictionary
    return {
        "ILP Better": ilp_better_count,
        "CP Better": cp_better_count,
        "Ties": tie_count,
        "Timeouts": timeout_count
    }
    
def plot_performance(datafile):
    # Load data from CSV file
    data = pd.read_csv(datafile)
    
    # Separate data for ILP and CP solvers
    ilp_data = data[data["Solver"] == "ILP"].copy()
    cp_data = data[data["Solver"] == "CP"].copy()
    
    # Cap time values at 150 seconds for plotting
    max_display_time = 150
    ilp_data['Time_Taken'] = ilp_data['Time_Taken'].apply(lambda x: min(x, max_display_time))
    cp_data['Time_Taken'] = cp_data['Time_Taken'].apply(lambda x: min(x, max_display_time))
    
    # Plot scatter points with capped values
    plt.figure(figsize=(12, 8))
    plt.scatter(ilp_data['Nodes'], ilp_data['Time_Taken'], color='green', alpha=0.5, label="ILP")
    plt.scatter(cp_data['Nodes'], cp_data['Time_Taken'], color='blue', alpha=0.5, label="CP")
    
    # Fit degree-3 polynomial to ILP and CP data
    ilp_poly_coeffs = np.polyfit(ilp_data['Nodes'], ilp_data['Time_Taken'], 2)
    cp_poly_coeffs = np.polyfit(cp_data['Nodes'], cp_data['Time_Taken'], 2)
    
    # Generate polynomial trend lines
    x_vals = np.linspace(0, max(data['Nodes']), 500)
    ilp_trend = np.polyval(ilp_poly_coeffs, x_vals)
    cp_trend = np.polyval(cp_poly_coeffs, x_vals)
    
    # Plot trend lines
    plt.plot(x_vals, ilp_trend, color='green', linestyle='--', linewidth=2, label="ILP Polynomial Fit")
    plt.plot(x_vals, cp_trend, color='blue', linestyle='--', linewidth=2, label="CP Polynomial Fit")
    
    # Labels and title
    plt.xlabel("Total Nodes")
    plt.ylabel("Time Taken (seconds)")
    plt.ylim(0, 160)  # Set y-axis limit slightly above cap for visibility
    plt.title("ILP vs CP Solver Performance with Polynomial Fit")
    plt.legend()
    
    # Show plot
    plt.show()
    
# Run the experiments
# run_experiments_and_save_results(num_graphs=100, max_nodes=110)
# print(calculate_p_value())
print(count_better_performances("experiment_results.csv"))
# plot_performance("experiment_results.csv")