# Terminal Output From Script

```txt
(dev) (base) user@user error_analysis % python classify_errors.py --provider anthropic
Looking for Qwen3-14B trajectories in: /phase_2/JSON_trajectories
Found 6 trajectory file(s)
  14b_ACT_airline: act-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131233237.json
  14b_ACT_retail: act-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201105240.json
  14b_ReAct_airline: react-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131211644.json
  14b_ReAct_retail: react-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131203002.json
  14b_FC_airline: tool-calling-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201005750.json
  14b_FC_retail: tool-calling-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201040648.json

Using anthropic / claude-sonnet-4-5-20250929

============================================================
Config: 14b_ACT_airline
File:   act-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131233237.json
  50 tasks total, 46 unique failures sampled
  [1/46] task_id=0 ... -> wrong_arguments
  [2/46] task_id=1 ... -> reasoning_failure
  [3/46] task_id=2 ... -> incomplete_execution
  [4/46] task_id=3 ... -> reasoning_failure
  [5/46] task_id=4 ... -> reasoning_failure
  [6/46] task_id=5 ... -> reasoning_failure
  [7/46] task_id=6 ... -> wrong_tool
  [8/46] task_id=7 ... -> reasoning_failure
  [9/46] task_id=8 ... -> premature_escalation
  [10/46] task_id=9 ... -> reasoning_failure
  [11/46] task_id=10 ... -> wrong_arguments
  [12/46] task_id=11 ... -> reasoning_failure
  [13/46] task_id=12 ... -> premature_escalation
  [14/46] task_id=13 ... -> reasoning_failure
  [15/46] task_id=14 ... -> premature_escalation
  [16/46] task_id=15 ... -> policy_violation
  [17/46] task_id=16 ... -> user_simulator_error
  [18/46] task_id=17 ... -> reasoning_failure
  [19/46] task_id=18 ... -> policy_violation
  [20/46] task_id=19 ... -> wrong_arguments
  [21/46] task_id=20 ... -> incomplete_execution
  [22/46] task_id=21 ... -> policy_violation
  [23/46] task_id=22 ... -> incomplete_execution
  [24/46] task_id=23 ... -> wrong_arguments
  [25/46] task_id=24 ... -> policy_violation
  [26/46] task_id=25 ... -> premature_escalation
  [27/46] task_id=26 ... -> incomplete_execution
  [28/46] task_id=27 ... -> incomplete_execution
  [29/46] task_id=28 ... -> reasoning_failure
  [30/46] task_id=29 ... -> policy_violation
  [31/46] task_id=30 ... -> incomplete_execution
  [32/46] task_id=31 ... -> incomplete_execution
  [33/46] task_id=32 ... -> wrong_arguments
  [34/46] task_id=33 ... -> wrong_arguments
  [35/46] task_id=34 ... -> policy_violation
  [36/46] task_id=35 ... -> policy_violation
  [37/46] task_id=36 ... -> policy_violation
  [38/46] task_id=39 ... -> wrong_tool
  [39/46] task_id=40 ... -> incomplete_execution
  [40/46] task_id=41 ... -> policy_violation
  [41/46] task_id=42 ... -> wrong_tool
  [42/46] task_id=44 ... -> incomplete_execution
  [43/46] task_id=45 ... -> wrong_arguments
  [44/46] task_id=46 ... -> incomplete_execution
  [45/46] task_id=47 ... -> incomplete_execution
  [46/46] task_id=48 ... -> wrong_arguments
  Saved: /phase_2/error_analysis/results/14b_ACT_airline.json

============================================================
Config: 14b_ACT_retail
File:   act-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201105240.json
  115 tasks total, 50 unique failures sampled
  [1/50] task_id=84 ... -> wrong_arguments
  [2/50] task_id=15 ... -> policy_violation
  [3/50] task_id=3 ... -> policy_violation
  [4/50] task_id=97 ... -> wrong_arguments
  [5/50] task_id=36 ... -> policy_violation
  [6/50] task_id=32 ... -> reasoning_failure
  [7/50] task_id=29 ... -> reasoning_failure
  [8/50] task_id=18 ... -> policy_violation
  [9/50] task_id=111 ... -> policy_violation
  [10/50] task_id=14 ... -> incomplete_execution
  [11/50] task_id=89 ... -> policy_violation
  [12/50] task_id=106 ... -> wrong_arguments
  [13/50] task_id=71 ... -> incomplete_execution
  [14/50] task_id=12 ... -> wrong_arguments
  [15/50] task_id=78 ... -> wrong_arguments
  [16/50] task_id=56 ... -> reasoning_failure
  [17/50] task_id=4 ... -> policy_violation
  [18/50] task_id=112 ... -> incomplete_execution
  [19/50] task_id=101 ... -> incomplete_execution
  [20/50] task_id=28 ... -> information_error
  [21/50] task_id=30 ... -> reasoning_failure
  [22/50] task_id=66 ... -> reasoning_failure
  [23/50] task_id=80 ... -> policy_violation
  [24/50] task_id=103 ... -> reasoning_failure
  [25/50] task_id=73 ... -> incomplete_execution
  [26/50] task_id=26 ... -> policy_violation
  [27/50] task_id=86 ... -> reasoning_failure
  [28/50] task_id=102 ... -> wrong_arguments
  [29/50] task_id=55 ... -> incomplete_execution
  [30/50] task_id=108 ... -> wrong_tool
  [31/50] task_id=59 ... -> wrong_tool
  [32/50] task_id=100 ... -> incomplete_execution
  [33/50] task_id=110 ... -> wrong_arguments
  [34/50] task_id=0 ... -> policy_violation
  [35/50] task_id=21 ... -> incomplete_execution
  [36/50] task_id=99 ... -> incomplete_execution
  [37/50] task_id=44 ... -> wrong_arguments
  [38/50] task_id=82 ... -> reasoning_failure
  [39/50] task_id=20 ... -> incomplete_execution
  [40/50] task_id=95 ... -> incomplete_execution
  [41/50] task_id=83 ... -> reasoning_failure
  [42/50] task_id=105 ... -> incomplete_execution
  [43/50] task_id=96 ... -> wrong_arguments
  [44/50] task_id=49 ... -> incomplete_execution
  [45/50] task_id=13 ... -> wrong_arguments
  [46/50] task_id=46 ... -> policy_violation
  [47/50] task_id=45 ... -> incomplete_execution
  [48/50] task_id=34 ... -> reasoning_failure
  [49/50] task_id=5 ... -> policy_violation
  [50/50] task_id=47 ... -> incomplete_execution
  Saved: /phase_2/error_analysis/results/14b_ACT_retail.json

============================================================
Config: 14b_ReAct_airline
File:   react-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131211644.json
  50 tasks total, 44 unique failures sampled
  [1/44] task_id=0 ... -> premature_escalation
  [2/44] task_id=1 ... -> wrong_tool
  [3/44] task_id=2 ... -> premature_escalation
  [4/44] task_id=3 ... -> reasoning_failure
  [5/44] task_id=4 ... -> reasoning_failure
  [6/44] task_id=5 ... -> reasoning_failure
  [7/44] task_id=6 ... -> wrong_arguments
  [8/44] task_id=7 ... -> reasoning_failure
  [9/44] task_id=8 ... -> wrong_arguments
  [10/44] task_id=9 ... -> wrong_arguments
  [11/44] task_id=10 ... -> incomplete_execution
  [12/44] task_id=11 ... -> reasoning_failure
  [13/44] task_id=13 ... -> policy_violation
  [14/44] task_id=14 ... -> premature_escalation
  [15/44] task_id=15 ... -> policy_violation
  [16/44] task_id=16 ... -> premature_escalation
  [17/44] task_id=17 ... -> wrong_tool
  [18/44] task_id=18 ... -> policy_violation
  [19/44] task_id=19 ... -> wrong_arguments
  [20/44] task_id=20 ... -> wrong_arguments
  [21/44] task_id=21 ... -> policy_violation
  [22/44] task_id=22 ... -> policy_violation
  [23/44] task_id=23 ... -> wrong_arguments
  [24/44] task_id=24 ... -> policy_violation
  [25/44] task_id=25 ... -> reasoning_failure
  [26/44] task_id=26 ... -> reasoning_failure
  [27/44] task_id=27 ... -> incomplete_execution
  [28/44] task_id=28 ... -> reasoning_failure
  [29/44] task_id=30 ... -> policy_violation
  [30/44] task_id=31 ... -> wrong_arguments
  [31/44] task_id=32 ... -> wrong_arguments
  [32/44] task_id=33 ... -> premature_escalation
  [33/44] task_id=34 ... -> incomplete_execution
  [34/44] task_id=35 ... -> policy_violation
  [35/44] task_id=36 ... -> policy_violation
  [36/44] task_id=38 ... -> wrong_tool
  [37/44] task_id=39 ... -> wrong_tool
  [38/44] task_id=41 ... -> policy_violation
  [39/44] task_id=42 ... -> policy_violation
  [40/44] task_id=43 ... -> incomplete_execution
  [41/44] task_id=44 ... -> incomplete_execution
  [42/44] task_id=45 ... -> wrong_arguments
  [43/44] task_id=46 ... -> incomplete_execution
  [44/44] task_id=49 ... -> policy_violation
  Saved: /phase_2/error_analysis/results/14b_ReAct_airline.json


============================================================
Config: 14b_ReAct_retail
File:   react-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0131203002.json
  115 tasks total, 50 unique failures sampled
  [1/50] task_id=86 ... -> wrong_arguments
  [2/50] task_id=15 ... -> policy_violation
  [3/50] task_id=4 ... -> policy_violation
  [4/50] task_id=99 ... -> incomplete_execution
  [5/50] task_id=36 ... -> wrong_arguments
  [6/50] task_id=32 ... -> policy_violation
  [7/50] task_id=29 ... -> reasoning_failure
  [8/50] task_id=18 ... -> incomplete_execution
  [9/50] task_id=110 ... -> incomplete_execution
  [10/50] task_id=14 ... -> wrong_arguments
  [11/50] task_id=91 ... -> policy_violation
  [12/50] task_id=105 ... -> incomplete_execution
  [13/50] task_id=72 ... -> incomplete_execution
  [14/50] task_id=12 ... -> policy_violation
  [15/50] task_id=79 ... -> wrong_arguments
  [16/50] task_id=56 ... -> incomplete_execution
  [17/50] task_id=5 ... -> wrong_tool
  [18/50] task_id=111 ... -> wrong_arguments
  [19/50] task_id=100 ... -> policy_violation
  [20/50] task_id=28 ... -> incomplete_execution
  [21/50] task_id=30 ... -> incomplete_execution
  [22/50] task_id=67 ... -> wrong_arguments
  [23/50] task_id=82 ... -> incomplete_execution
  [24/50] task_id=96 ... -> policy_violation
  [25/50] task_id=75 ... -> wrong_arguments
  [26/50] task_id=26 ... -> incomplete_execution
  [27/50] task_id=101 ... -> reasoning_failure
  [28/50] task_id=55 ... -> policy_violation
  [29/50] task_id=107 ... -> premature_escalation
  [30/50] task_id=59 ... -> wrong_arguments
  [31/50] task_id=102 ... -> policy_violation
  [32/50] task_id=109 ... -> reasoning_failure
  [33/50] task_id=1 ... -> wrong_arguments
  [34/50] task_id=21 ... -> reasoning_failure
  [35/50] task_id=98 ... -> reasoning_failure
  [36/50] task_id=44 ... -> incomplete_execution
  [37/50] task_id=103 ... -> policy_violation
  [38/50] task_id=20 ... -> wrong_arguments
  [39/50] task_id=94 ... -> policy_violation
  [40/50] task_id=77 ... -> policy_violation
  [41/50] task_id=104 ... -> incomplete_execution
  [42/50] task_id=95 ... -> wrong_arguments
  [43/50] task_id=49 ... -> incomplete_execution
  [44/50] task_id=13 ... -> incomplete_execution
  [45/50] task_id=46 ... -> policy_violation
  [46/50] task_id=45 ... -> incomplete_execution
  [47/50] task_id=39 ... -> incomplete_execution
  [48/50] task_id=17 ... -> policy_violation
  [49/50] task_id=53 ... -> reasoning_failure
  [50/50] task_id=3 ... -> policy_violation
  Saved: /phase_2/error_analysis/results/14b_ReAct_retail.json

============================================================
Config: 14b_FC_airline
File:   tool-calling-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201005750.json
  50 tasks total, 50 unique failures sampled
  [1/50] task_id=0 ... -> policy_violation
  [2/50] task_id=1 ... -> wrong_tool
  [3/50] task_id=2 ... -> reasoning_failure
  [4/50] task_id=3 ... -> reasoning_failure
  [5/50] task_id=4 ... -> reasoning_failure
  [6/50] task_id=5 ... -> reasoning_failure
  [7/50] task_id=6 ... -> incomplete_execution
  [8/50] task_id=7 ... -> reasoning_failure
  [9/50] task_id=8 ... -> wrong_arguments
  [10/50] task_id=9 ... -> reasoning_failure
  [11/50] task_id=10 ... -> wrong_arguments
  [12/50] task_id=11 ... -> wrong_arguments
  [13/50] task_id=12 ... -> policy_violation
  [14/50] task_id=13 ... -> reasoning_failure
  [15/50] task_id=14 ... -> reasoning_failure
  [16/50] task_id=15 ... -> policy_violation
  [17/50] task_id=16 ... -> wrong_arguments
  [18/50] task_id=17 ... -> reasoning_failure
  [19/50] task_id=18 ... -> policy_violation
  [20/50] task_id=19 ... -> wrong_arguments
  [21/50] task_id=20 ... -> incomplete_execution
  [22/50] task_id=21 ... -> policy_violation
  [23/50] task_id=22 ... -> wrong_tool
  [24/50] task_id=23 ... -> wrong_arguments
  [25/50] task_id=24 ... -> reasoning_failure
  [26/50] task_id=25 ... -> wrong_arguments
  [27/50] task_id=26 ... -> reasoning_failure
  [28/50] task_id=27 ... -> incomplete_execution
  [29/50] task_id=28 ... -> premature_escalation
  [30/50] task_id=29 ... -> policy_violation
  [31/50] task_id=30 ... -> wrong_arguments
  [32/50] task_id=31 ... -> incomplete_execution
  [33/50] task_id=32 ... -> wrong_arguments
  [34/50] task_id=33 ... -> premature_escalation
  [35/50] task_id=34 ... -> user_simulator_error
  [36/50] task_id=35 ... -> policy_violation
  [37/50] task_id=36 ... -> policy_violation
  [38/50] task_id=37 ... -> wrong_tool
  [39/50] task_id=38 ... -> premature_escalation
  [40/50] task_id=39 ... -> reasoning_failure
  [41/50] task_id=40 ... -> policy_violation
  [42/50] task_id=41 ... -> policy_violation
  [43/50] task_id=42 ... -> policy_violation
  [44/50] task_id=43 ... -> reasoning_failure
  [45/50] task_id=44 ... -> incomplete_execution
  [46/50] task_id=45 ... -> user_simulator_error
  [47/50] task_id=46 ... -> incomplete_execution
  [48/50] task_id=47 ... -> incomplete_execution
  [49/50] task_id=48 ... -> wrong_tool
  [50/50] task_id=49 ... -> policy_violation
  Saved: /phase_2/error_analysis/results/14b_FC_airline.json

============================================================
Config: 14b_FC_retail
File:   tool-calling-Qwen3-14B-0.0_range_0--1_user-Qwen3-32B-llm_0201040648.json
  115 tasks total, 50 unique failures sampled
  [1/50] task_id=87 ... -> wrong_arguments
  [2/50] task_id=15 ... -> policy_violation
  [3/50] task_id=3 ... -> policy_violation
  [4/50] task_id=101 ... -> policy_violation
  [5/50] task_id=37 ... -> premature_escalation
  [6/50] task_id=33 ... -> reasoning_failure
  [7/50] task_id=30 ... -> incomplete_execution
  [8/50] task_id=19 ... -> policy_violation
  [9/50] task_id=111 ... -> policy_violation
  [10/50] task_id=14 ... -> incomplete_execution
  [11/50] task_id=92 ... -> policy_violation
  [12/50] task_id=106 ... -> reasoning_failure
  [13/50] task_id=73 ... -> policy_violation
  [14/50] task_id=12 ... -> policy_violation
  [15/50] task_id=81 ... -> policy_violation
  [16/50] task_id=57 ... -> policy_violation
  [17/50] task_id=4 ... -> policy_violation
  [18/50] task_id=112 ... -> incomplete_execution
  [19/50] task_id=103 ... -> reasoning_failure
  [20/50] task_id=29 ... -> policy_violation
  [21/50] task_id=31 ... -> policy_violation
  [22/50] task_id=68 ... -> policy_violation
  [23/50] task_id=83 ... -> wrong_arguments
  [24/50] task_id=97 ... -> incomplete_execution
  [25/50] task_id=75 ... -> policy_violation
  [26/50] task_id=27 ... -> policy_violation
  [27/50] task_id=102 ... -> incomplete_execution
  [28/50] task_id=56 ... -> reasoning_failure
  [29/50] task_id=108 ... -> wrong_arguments
  [30/50] task_id=60 ... -> wrong_arguments
  [31/50] task_id=100 ... -> incomplete_execution
  [32/50] task_id=110 ... -> policy_violation
  [33/50] task_id=0 ... -> policy_violation
  [34/50] task_id=22 ... -> incomplete_execution
  [35/50] task_id=99 ... -> incomplete_execution
  [36/50] task_id=45 ... -> reasoning_failure
  [37/50] task_id=82 ... -> wrong_arguments
  [38/50] task_id=21 ... -> incomplete_execution
  [39/50] task_id=95 ... -> wrong_arguments
  [40/50] task_id=76 ... -> policy_violation
  [41/50] task_id=105 ... -> policy_violation
  [42/50] task_id=96 ... -> reasoning_failure
  [43/50] task_id=51 ... -> reasoning_failure
  [44/50] task_id=13 ... -> incomplete_execution
  [45/50] task_id=47 ... -> policy_violation
  [46/50] task_id=78 ... -> wrong_arguments
  [47/50] task_id=24 ... -> reasoning_failure
  [48/50] task_id=40 ... -> incomplete_execution
  [49/50] task_id=18 ... -> policy_violation
  [50/50] task_id=54 ... -> policy_violation
  Saved: /phase_2/error_analysis/results/14b_FC_retail.json

Combined summary: phase_2/error_analysis/results/combined_summary.json
Representative examples: /phase_2/error_analysis/results/examples/representative_examples.json (8 categories)

Generating plots...
classify_errors.py:792: MatplotlibDeprecationWarning: The get_cmap function was deprecated in Matplotlib 3.7 and will be removed two minor releases later. Use ``matplotlib.colormaps[name]`` or ``matplotlib.colormaps.get_cmap(obj)`` instead.
  cmap = plt.cm.get_cmap("Set3", len(categories))
  Saved 3 plots to /phase_2/error_analysis/results/plots/

============================================================
SUMMARY
============================================================

14b_ACT_airline:
  incomplete_execution       11 ( 23.9%) ###########
  reasoning_failure          10 ( 21.7%) ##########
  policy_violation            9 ( 19.6%) #########
  wrong_arguments             8 ( 17.4%) ########
  premature_escalation        4 (  8.7%) ####
  wrong_tool                  3 (  6.5%) ###
  user_simulator_error        1 (  2.2%) #

14b_ACT_retail:
  incomplete_execution       15 ( 30.0%) ###############
  policy_violation           12 ( 24.0%) ############
  wrong_arguments            10 ( 20.0%) ##########
  reasoning_failure          10 ( 20.0%) ##########
  wrong_tool                  2 (  4.0%) ##
  information_error           1 (  2.0%) #

14b_FC_airline:
  reasoning_failure          13 ( 26.0%) #############
  policy_violation           12 ( 24.0%) ############
  wrong_arguments             9 ( 18.0%) #########
  incomplete_execution        7 ( 14.0%) #######
  wrong_tool                  4 (  8.0%) ####
  premature_escalation        3 (  6.0%) ###
  user_simulator_error        2 (  4.0%) ##

14b_FC_retail:
  policy_violation           23 ( 46.0%) #######################
  incomplete_execution       11 ( 22.0%) ###########
  reasoning_failure           8 ( 16.0%) ########
  wrong_arguments             7 ( 14.0%) #######
  premature_escalation        1 (  2.0%) #

14b_ReAct_airline:
  policy_violation           12 ( 27.3%) #############
  wrong_arguments             9 ( 20.5%) ##########
  reasoning_failure           8 ( 18.2%) #########
  incomplete_execution        6 ( 13.6%) ######
  premature_escalation        5 ( 11.4%) #####
  wrong_tool                  4 (  9.1%) ####

14b_ReAct_retail:
  incomplete_execution       16 ( 32.0%) ################
  policy_violation           15 ( 30.0%) ###############
  wrong_arguments            11 ( 22.0%) ###########
  reasoning_failure           6 ( 12.0%) ######
  wrong_tool                  1 (  2.0%) #
  premature_escalation        1 (  2.0%) #

Done! All outputs in: /phase_2/error_analysis/results/
```
