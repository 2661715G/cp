% Number of nodes
int: n;
set of int: NODE = 0..n-1;

%Start node
int: r;
int: fire_start = r;

%Graph connections
array[int] of NODE: from;
array[int] of NODE: to;
int: num_edges = length(from);

% Number of time steps
int: length = n+1;
set of int: TIME = 0..length;

% Shows where a firefighter is being placed at a given time step
array[0..length] of var NODE: firefighter;

%Keeps track of each node and if it is defended
array[TIME, NODE] of var bool: defended;

constraint forall(node in NODE where node != firefighter[0])(
    defended[0,node] = 0
);

constraint forall(t in 1..max(TIME), node in NODE)(
    if (on_fire[t,node] = 1)then(
       defended[t,node] = 0
    )
    elseif (firefighter[t] = node)then(
       defended[t,node] = 1
    )
    else 
       defended[t, node] = (defended[t-1, node] \/
                            exists(i in 1..num_edges)(
                            (from[i] == node /\ defended[t-1, to[i]]) \/
                            (to[i] == node /\ defended[t-1, from[i]])
                            )
                          )
    endif
);

% Array to store which nodes are on fire at each time step
array[TIME, NODE] of var bool: on_fire;

% Initial state: fire starts at the fire_start node at time 0
constraint on_fire[0, fire_start] = true;

constraint forall(node in NODE where node != fire_start) (
    on_fire[0, node] = false
);

% For every time step t, propagate the fire and place a firefighter
constraint forall(t in 1..length, node in NODE) (
    % If a firefighter is placed on a node prior to the current time step, it cannot catch fire
    if (defended[t-1,node] == 1) then
        on_fire[t, node] = false
    else
      %Node is on fire if it was previously on fire; Or if any of the nodes it has a connection from (or to) were previously on fire
      on_fire[t, node] = (on_fire[t-1, node] \/
                            exists(i in 1..num_edges)(
                            (from[i] == node /\ on_fire[t-1, to[i]]) \/
                            (to[i] == node /\ on_fire[t-1, from[i]])
                            )
                          )
    endif
);

% Objective: minimize the number of nodes that are on fire at the final time step
var int: total_on_fire = sum([on_fire[max(TIME), node] | node in NODE]);

solve minimize total_on_fire;
