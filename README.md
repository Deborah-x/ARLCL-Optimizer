# ARLCL-Optimizer

Dimitris Xenakis, Antonio Di Maio, Torsten Braun

[![ARLCL-Optimizer](https://webarchive.inf.unibe.ch/cds/publications/files/Cycles_in_ARLCL.jpg "ARLCL-Optimizer")](https://webarchive.inf.unibe.ch/cds/publications/files/Cycles_in_ARLCL.jpg "ARLCL-Optimizer")

ARLCL-Optimizer is an application implementing the cooperative localization method **ARLCL: Anchor-free Ranging-Likelihood-based Cooperative Localization**. This method has been developed by the Communication and Distributed Systems research group at the University of Bern.

The application supports both Graphical (for single scenario executions) and Headless (useful for batch executions) modes.

*Supported Models:*
<br />
- RSS-based ranging using Bluetooth Low Energy signals [BLE] (model's units are in meters)
- Time-based ranging using Ultra-Wideband signals [UWB] (model's units are in centimeters)

We provide also two localization implementations based on **Mass Springs** (*MS_Localization.py*) and **Maximum Likelihood - Particle Swarm Optimization** (*ML-PSO_Localization.py*) that were used as baselines with ARLCL. Their dependencies are mentioned in *requirements.txt*.

## Ranging Database

Depending on the execution mode, two different types of files can be used. GUI mode makes use of single database files (.rss or .smpl) containing the ranging measurements for a specific scenario. Headless mode makes use of an additional index file containing the scenario names of multiple database files.

This repo provides sample databases and index files (see Examples).
The complete databases used for the evaluation of ARLCL are also openly available:

Complete Evaluation Dataset for BLE : [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7552462.svg)](https://doi.org/10.5281/zenodo.7552462)
<br />
Complete Evaluation Dataset for UWB: To be published

For the creation of new database files and to support the resulted localization performance, the structure of a database file needs to be specific and contain a) for each node, the positions' ground truth and b) for each pair, the ranging measurement (dBm/time) used by arlcl and the distance measurement (cm) used by the baselines.

DB ("T_4,5,6_1.rss") example for BLE measurements:

	#POSITIONS GROUND TRUTH#
	4:-5.682;-4.377
	5:-5.237;-3.921
	6:-3.808;-2.652

	#RSS_0#
	4;5:-47.292382240617094&0.6372
	5;4:-47.292382240617094&0.6372
	4;6:-64.94839708270037&2.5471
	6;4:-64.94839708270037&2.5471
	5;6:-61.288393078461255&1.9111
	6;5:-61.288393078461255&1.9111
	
	...

	#RSS_100#
	4;5:-49.4872253506454&0.7569
	5;4:-49.4872253506454&0.7569
	4;6:-64.72211723091444&2.5022
	6;4:-64.72211723091444&2.5022
	5;6:-58.29407210961294&1.5109
	6;5:-58.29407210961294&1.5109

DB ("A_2,4,18,30,34_5.smpl") example for UWB measurements:

	#POSITIONS GROUND TRUTH#
	2:-213.725998;-196.776993
	4:-212.324997;-196.675003
	18:-213.651993;-193.326004
	30:-212.774994;-186.389999
	34:-211.026993;-188.248001

	#TIME_0#
	2;4:12.058198919907305&361.3872928528868
	2;18:45.38120426134302&1360.0862503051758
	4;2:11.966366375597334&358.635048110168
	4;30:39.7734261513773&1192.0197120484183
	18;2:45.52596614645396&1364.4248008728027
	18;34:27.9284414707915&837.0225042536639
	30;4:39.99122473425343&1198.5471910505153
	30;34:29.63656320286695&888.2153476225702
	34;18:27.28812194275694&817.8319649090843
	34;30:28.18789569155599&844.7984133329657

	...

	#TIME_100#
	2;4:12.423001798192777&372.3205280303955
	2;18:45.38120426134302&1360.0862503051758
	4;2:12.413611670373811&372.0391035079956
	4;30:40.67758376713238&1219.117546081543
	18;2:45.52596614645396&1364.4248008728027
	18;34:26.041666825515573&780.4753875732422
	30;4:40.98119519518652&1228.2168579101562
	30;34:25.118313882410856&752.8022646903992
	34;18:21.750425825083774&651.8658018112183
	34;30:31.040289340698912&930.2853775024414



An index file contains (per line) a scenario name available in the following in a database file, in the following format:

    T (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21) 20
    T (4,5,6) 1 
    ...

## GUI mode
- Executes a cooperative localization optimization for the selected database of ranging measurements.

The application may start by executing the provided *arlcl-optimizer_gui-run.bat* or directly from CLI using

`$ java --add-exports java.base/java.lang=ALL-UNNAMED --add-exports java.desktop/sun.awt=ALL-UNNAMED --add-exports java.desktop/sun.java2d=ALL-UNNAMED -jar arlcl-optimizer.jar`

### Parameters

| Parameter                                 | Description                                                                                                                          |
|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| Results per                               | Optimization state after which results shall be presented [Step/Cycle].                                                              |
| Rang. Model                               | Type of ranging measurement (should correspond to the loaded DB file) [BLE/UWB].                                                     |
| Export function                           | For storing the likelihood function as a Wolfram plot [Free account at https://www.wolframcloud.com/].                               |
| Contours                                  | Number of contours to be drawn. Setting this to 0 will draw a 3D plot (Used for 3D localization).                                    |
| Min Effective Measurement                 | Measurements above this threshold will not be considered during the localization. The effective neighbors are represented in yellow. |
| k Nearest Nodes for Effectiveness Check   | The k closest neighbors to be considered for identifying the optimization order.                                                     |
| Extent of Random Positions Initialization | How far nodes can be randomly spawn during their initialization.                                                                     |
| Seed for Random Positions Initialization  | Seed for any random values generated during the optimization.                                                                        |
| Iteration in scenario to evaluate         | The is the ID of the last iteration. Each DB file can contain multiple evaluation iterations (e.g. 100 for the case of #RSS_100#).   |
| Optimization Threads                      | Number of optimization thread workers to be used. For identical reproducibility this should be set to 1.                             |
| Optimization Iterations per Thread        | How deep each optimization worker will be searching for the optimal solution at each step.                                           |
| Max Step-Opt. Runtime per Thread          | A time threshold to be used per step optimization. Has a higher priority compared to the “Optimization Iterations per Thread”.       |
| Optimization's ftol                       | Tolerance for the optimization based on the Nelder–Mead method.                                                                      |
| Optimization's Initial Step Size          | The step size considered by the Nelder–Mead method.                                                                                  |
| Optimization Cycles                       | For how many cycles to perform localization.                                                                                         |

----

### Demo
www.youtube.com/watch?v=2DhkNLAwHkw
[![ARLCL-Optimizer GUI Usage/Export demo with UWB measurements](https://indoorpaths.com/3rd_sources/ARLCL/GUI_screenshot.png)](https://youtu.be/2DhkNLAwHkw)

## Headless mode

For batch execution (with results per cycle), the application may be launched in a scripted manner by executing the jar in headless mode and passing the selected parameters.
The user needs to configure and call sequentially the provided *arlcl-optimizer_batch-run.bat*, or use directly the CLI according to the following example:

`$ java -jar "arlcl-optimizer.jar" out="Export/ARLCL/BLE" db="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/DB" batch="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/Batch.txt" scenario_id=0 model=ble contours=30 min_m=95 kn=6 pos_extent=10 seed=0 end_iter=100 threads=5 opts=1000 max_t=1000000 f_tol=1e-2 step=100 cycles=50`

### Parameters

| Parameter     | Description                                                                                                                                                                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *out*         | Export folder where to store the archived results. All evaluated iterations of a specific scenario (e.g. "T (1,6,8,9,12,16) 15") are stored as a group in a single .zip archive.                                                                |
| *db*          | DB folder containing all measurements. Each evaluated scenario that is considered in the index batch file (e.g. "T (1,6,8,9,12,16) 15") should have a single corresponding DB file that includes the measurements for all evaluated iterations. |
| *batch*       | Path to the batch file containing all evaluated scenarios.                                                                                                                                                                                      |
| *scenario_id* | Index (i.e. line number) of the scenario in the batch file to evaluate. An automated (and possibly parallel) batch execution of multiple scenarios would require that this ID is set dynamically.                                               |
| *model*       | Type of ranging measurement (should correspond to the loaded DB file) [ble/uwb].                                                                                                                                                                |
| *contours*    | Number of contours to be used in the exported Wolfram plotting command (set to 0 for disabling plot export). [Free account at https://www.wolframcloud.com/]                                                                                    |
| *min_m*       | Measurements above this threshold will not be considered during the localization. The effective neighbors are represented in yellow.                                                                                                            |
| *kn*          | The k closest neighbors to be considered for identifying the optimization order.                                                                                                                                                                |
| *pos_extent*  | How far nodes can be randomly spawn during their initialization.                                                                                                                                                                                |
| *seed*        | Seed for any random values generated during the optimization.                                                                                                                                                                                   |
| *end_iter*    | The ID of the last evaluated iteration in a DB file. Each DB file can contain multiple evaluation iterations (e.g. 100 for the case of #RSS_100#).                                                                                              |
| *threads*     | Number of optimization thread workers to be used. For identical reproducibility this should be set to 1.                                                                                                                                        |
| *opts*        | How deep each optimization worker will be searching for the optimal solution at each step.                                                                                                                                                      |
| *max_t*       | A time threshold to be used per step optimization. Has a higher priority compared to the “Optimization Iterations per Thread”.                                                                                                                  |
| *f_tol*       | Tolerance for the optimization based on the Nelder–Mead method.                                                                                                                                                                                 |
| *step*        | The step size considered by the Nelder–Mead method.                                                                                                                                                                                             |
| *cycles*      | For how many cycles to perform localization.                                                                                                                                                                                                    |

----

# CL based on Mass Springs
The cooperative localization engine based on **Mass Spring** which was used as a baseline.

The python script supports only headless mode (for batch execution) and requires batch results being available from ARLCL-Optimizer.
The user needs to configure and call sequentially the provided *ms-localizer_batch-run.bat*, or use directly the CLI according to the following example:

`$ venv\Scripts\python.exe MS_Localization.py log="Export/MS/BLE.log" out="Export/MS/BLE" arlcl_out="Export/ARLCL/BLE" db="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/DB" batch="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/Batch.txt" scenario_id=0 model=ble seed=0 end_iter=100 opts=50000 learn_rate=1e-2`

### Parameters

| Parameter     | Description                                                                                                                                                                                                                                     |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *log*         | Path where to store the localization log.                                                                                                                                                                                                       |
| *out*         | Export folder where to store the archived results. All evaluated iterations of a specific scenario (e.g. "T (1,6,8,9,12,16) 15") are stored as a group in a single .zip archive.                                                                |
| *arlcl_out*   | Export folder of ARLCL's archived results. This is used only for setting the same Nodes' initialization (could be easily bypassed if MS is only required).                                                                                      |
| *db*          | DB folder containing all measurements. Each evaluated scenario that is considered in the index batch file (e.g. "T (1,6,8,9,12,16) 15") should have a single corresponding DB file that includes the measurements for all evaluated iterations. |
| *batch*       | Path to the batch file containing all evaluated scenarios.                                                                                                                                                                                      |
| *scenario_id* | Index (i.e. line number) of the scenario in the batch file to evaluate. An automated (and possibly parallel) batch execution of multiple scenarios would require that this ID is set dynamically.                                               |
| *model*       | Type of ranging measurement (should correspond to the loaded DB file) [ble/uwb].                                                                                                                                                                |
| *seed*        | Seed for any random values generated during the optimization.                                                                                                                                                                                   |
| *end_iter*    | The ID of the last evaluated iteration in a DB file. Each DB file can contain multiple evaluation iterations (e.g. 100 for the case of #RSS_100#).                                                                                              |
| *opts*        | How deep each optimization worker will be searching for the optimal solution at each step.                                                                                                                                                      |
| *learn_rate*  | The learn rate of the optimization.                                                                                                                                                                                                             |

----

# CL based on Maximum Likelihood - Particle Swarm Optimization
The cooperative localization engine based on **Maximum Likelihood - Particle Swarm Optimization** which was used as a baseline.

The python script supports only headless mode (for batch execution) and requires batch results being available from ARLCL-Optimizer.
The user needs to configure and call sequentially the provided *ml-pso-localizer_batch-run.bat*, or use directly the CLI according to the following example:

`$ venv\Scripts\python.exe ML-PSO_Localization.py log="Export/ML-PSO/BLE.log" out="Export/ML-PSO/BLE" arlcl_out="Export/ARLCL/BLE" db="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/DB" batch="Examples/BLE-RSS_Evaluation-Samples_Lecture-Room (Examples)/Batch.txt" scenario_id=0 model=ble seed=0 end_iter=100 opts=1000 particles=500 c1=0.7 c2=0.3 w=0.9`

### Parameters

| Parameter     | Description                                                                                                                                                                                                                                   |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| *log*         | Path where to store the localization log.                                                                                                                                                                                                     |
| *out*         | Export folder where to store the archived results. All evaluated iterations of a specific scenario (e.g. "T (1,6,8,9,12,16) 15") are stored as a group in a single .zip archive.                                                              |
| *arlcl_out*   | Export folder of ARLCL's archived results. This is used only for setting the same Nodes' initialization (could be easily bypassed if MS is only required).                                                                                    |
| *db*          | DB folder containing all measurements. Each evaluated scenario that is considered in the index batch file (e.g. "T (1,6,8,9,12,16) 15") should have a single corresponding DB file that includes the measurements for all evaluated iterations. |
| *batch*       | Path to the batch file containing all evaluated scenarios.                                                                                                                                                                                    |
| *scenario_id* | Index (i.e. line number) of the scenario in the batch file to evaluate. An automated (and possibly parallel) batch execution of multiple scenarios would require that this ID is set dynamically.                                             |
| *model*       | Type of ranging measurement (should correspond to the loaded DB file) [ble/uwb].                                                                                                                                                              |
| *seed*        | Seed for any random values generated during the optimization.                                                                                                                                                                                 |
| *end_iter*    | The ID of the last evaluated iteration in a DB file. Each DB file can contain multiple evaluation iterations (e.g. 100 for the case of #RSS_100#).                                                                                            |
| *opts*        | How deep each optimization worker will be searching for the optimal solution at each step.                                                                                                                                                    |
| *particles*   | How many searching particles to launch per optimization.                                                                                                                                                                                      |
| *c1*          | c1 acceleration coefficient of PSO.                                                                                                                                                                                             |
| *c2*          | c2 acceleration coefficient of PSO.                                                                                                                                                                                                                     |
| *w*           | w hyperparameter of PSO.                                                                                                                                                                                                                      |

----
