import random
import networkx as nx
import time
import minizinc
import pulp
# you will likely need to import other things


#
# This function should run your ILP implementation
# for infectious vaccine 
# - instance_graph will be a networkx graph object
# - start_node is the node where the fire starts
# - timeout is the maximum time in ms you should let the search run for
# The function should return a dictionary that has 'num_saved' mapped to 
# the number saved in the solution
# or None if the model does not halt in the time allowed
# (The dictionary structure is so you can return other things if it's 
# useful for your pipeline)
def run_ilp(instance_graph, start_node = 1, timeout=1000):
    
  num_nodes = 4
  time_steps = num_nodes + 1
  from_list = [0, 1, 2, 3]
  to_list = [1, 2, 3, 0]
  initially_on_fire = [0]

  firefighter = pulp.LpVariable.dicts("firefighter", ((time, node) for time in range(time_steps) for node in range(num_nodes)), cat="Binary")
  on_fire = pulp.LpVariable.dicts("on_fire", ((time, node) for time in range(time_steps) for node in range(num_nodes)), cat="Binary")

  # Objective: Minimize the number of nodes on fire at the final time step
  model = pulp.LpProblem("Firefighter_Problem", pulp.LpMinimize)
  model += pulp.lpSum(on_fire[time_steps-1, node] for node in range(num_nodes))
  
  #Pre-compute list of neighbors of each node
  neighbor_dict = {}
  for node in range(num_nodes):
    list_of_neighbors = []
    
    for i in range(len(from_list)):
      if from_list[i] == node:
        list_of_neighbors.append(to_list[i])
        
      elif to_list[i] == node:
        list_of_neighbors.append(from_list[i])
        
    neighbor_dict[node] = list_of_neighbors
                     

  # Constraints
  # Node(s) start on fire
  for node in range(num_nodes):
    if node in initially_on_fire:
        model += on_fire[0, node] == 1
        model += firefighter[0, node] == 0
    else:
        model += on_fire[0, node] == 0

  # One additional node can be defended at each step
  model += pulp.lpSum(firefighter[0, node] for node in range(num_nodes)) <=1
  for time in range(1, time_steps):
        model += pulp.lpSum(firefighter[time, node] for node in range(num_nodes)) <= pulp.lpSum(firefighter[time, node] for node in range(num_nodes)) + 1
        
  # Constraints for fire spread and defense behavior over time
  for time in range(1, time_steps):
    for node in range(num_nodes):
      # Nodes continue burning once ignited
      model += on_fire[time, node] >= on_fire[time - 1, node]

      # Nodes continue being defended once protected
      model += firefighter[time, node] >= firefighter[time - 1, node]

      # Protected nodes do not catch fire
      model += on_fire[time, node] <= 1 - firefighter[time, node]

      # Nodes on fire cannot be defended
      model += firefighter[time, node] <= 1 - on_fire[time - 1, node]

      # Check for any burning neighbors and, if found, spread the fire
      burning_neighbor = pulp.lpSum(on_fire[time - 1, neighbor] for neighbor in neighbor_dict[node])
      # Normalise sum to be 1 
      model += on_fire[time, node] >= burning_neighbor/len(burning_neighbor) - firefighter[time-1, node]

  model.solve(pulp.GLPK_CMD())
  result_dict = {"num_saved": num_nodes-pulp.value(model.objective)}
  
  if __name__ == "__main__":
    for time in range(time_steps):
      # Defended nodes and their values
      defended_nodes = [(node, pulp.value(firefighter[time, node])) for node in range(num_nodes) if pulp.value(firefighter[time, node]) is not None]
      
      # On fire nodes and their values
      on_fire_nodes = [(node, pulp.value(on_fire[time, node])) for node in range(num_nodes) if pulp.value(on_fire[time, node]) is not None]
      
      print(f"Time {time}:")
      print("  Defended nodes and values:", defended_nodes)
      print("  On fire nodes and values:", on_fire_nodes)
      print("\n")
    print(neighbor_dict)
    
  return result_dict


#
# This function should run your CP implementation
# for infectious vaccine 
# - instance_graph will be a networkx graph object
# - start_node is the node where the fire starts
# - timeout is the maximum time in ms you should let the search run for
# The function should return a dictionary that has 'num_saved' mapped to 
# the number saved in the solution
# or None if the model does not halt in the time allowed
# (The dictionary structure is so you can return other things if it's 
# useful for your pipeline)
# There are many ways to deal with the instance_graph, and 
# this is intentionally left up to you. 
# For example, you could create a .dzn file in whatever encoding you want
# and add it using the https://python.minizinc.dev/en/latest/api.html#minizinc.model.Model.add_file capability

def run_cp(instance_graph, start_node = 1, timeout=1000):
  file_name = "Graph_to_solve.dzn"
  from_list, to_list, num_nodes, start_node = reformat_graph(instance_graph, start_node)
  write_file(from_list, to_list, num_nodes, start_node, file_name)
  
  model = minizinc.Model()
  model.add_file("Firefighter.mzn")
  model.add_file(file_name)

  solver = minizinc.Solver.lookup("chuffed")
  instance = minizinc.Instance(solver, model)
  
  result = instance.solve()
  result_dict = {"num_saved": num_nodes-result.objective}
    
  return (result_dict)


def reformat_graph(graph,start_node):
  edges, start_node = flatten_graph(graph,start_node)
  num_nodes = len(list(graph.nodes()))

  # Separate into 'from' and 'to' lists
  from_list = [edge[0] for edge in edges]
  to_list = [edge[1] for edge in edges]
  
  return from_list, to_list, num_nodes, start_node


def write_file(from_list, to_list, n, r, file_name):
  with open(file_name, 'w') as file:
    file.write(f"from = {from_list};\n")
    file.write(f"to = {to_list};\n")
    file.write(f"n = {n};\n")
    file.write(f"r = {r};\n")
    
    
def flatten_graph(graph,node_to_start):
    # Flatten graph into a 1d representation
    one_D_mapping = {}
    node_counter = 0
    
    edges = list(graph.edges)
    
    for edge in edges:
        for node in edge:
            if node not in one_D_mapping:
                #Creates a dictionary that maps a 2d coordinate to its equivalent in 1d
                one_D_mapping[node] = node_counter
                node_counter += 1
    
    # Convert the edges to 2d
    # ((0,0),(0,1)) becomes (0,1)
    converted_edges = [(one_D_mapping[edge[0]], one_D_mapping[edge[1]]) for edge in edges]
    
    node_to_start = one_D_mapping[node_to_start]
    
    return converted_edges, node_to_start
        
if __name__=="__main__":
  graph = nx.path_graph(12)
  # graph = nx.grid_2d_graph(10,10)
  # cp = run_cp(graph, start_node = (0,5))
  # print(cp)
  print(run_ilp(graph))