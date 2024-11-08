include "alldifferent.mzn";
int: n;
int: m;
int: no_m;
int: no_friends = n; %no_friedns
int: no_meetings = m; %no_meetings
int: max_time;

set of int: NODE  = 1..no_friends;
set of int: EDGE  = 1..no_meetings;

int: no_cant_meet = no_m;

set of int: NO_EDGE = 1..no_cant_meet;

array[EDGE] of NODE: from;
array[EDGE] of NODE: to;
array[NO_EDGE] of NODE: no_from;
array[NO_EDGE] of NODE: no_to;

array[NODE] of var 1..max_time: start_times;
array[NODE] of var 1..max_time: end_times;

% No two people can arrive or leave on the same day
constraint alldifferent([start_times[i] | i in NODE]);
constraint alldifferent([end_times[i] | i in NODE]);

% Everyone must stay for at least one day/ cannot leave the day they arrive
constraint forall(i in 1..no_friends)(start_times[i]<end_times[i]);

%If x must meet y, then x must arrive before y and leave after y has arrived
constraint forall(i in EDGE)(start_times[from[i]] < start_times[to[i]]); 
constraint forall(i in EDGE)(end_times[from[i]] > start_times[to[i]]);

%If x must not meet y, then x must have left by the day that y arrives
constraint forall(no_meet in no_from)(end_times[no_from[no_meet]] <= start_times[no_to[no_meet]] \/ end_times[no_to[no_meet]] <= start_times[no_from[no_meet]]);
solve minimize(max(end_times))