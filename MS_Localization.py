# --------------------------------------------------------------
# This module is used to generate the positioning estimations
# using the Mass-Spring Localization method.
# The DB loading, loads the initial positions from ARLCL results,
# to have a common initialization (could be disabled).
# --------------------------------------------------------------
# TODO: Allow user to set custom model parameters
import os
import shutil
import sys
import numpy as np
import zipfile
import torch
import torch.nn as nn
import argparse

# 加文件工作目录，不然debug模式下相对路径会报错
os.chdir('/home/guest/shared/lx/ARLCL-Optimizer')  # 确保工作目录与相对路径一致
logged_lines = []

measurement = {"ble": {"unit": "RSS", "db_ext": ".rss"},
               "uwb": {"unit": "TIME", "db_ext": ".smpl"}}

args = sys.argv
str_params = {}
ARLCL_zipped_scenario_path = None

# Parse all parameters and put the in the corresponding dictionary in unconstrained order
# for parameter in sys.argv[1:]:
#     key_value_pair = parameter.split("=")   # 命令行输入的参数是以等号分隔的
#     # key_value_pair = parameter.split(" ")  # 调试时参数是以空格分隔的
#     str_params[key_value_pair[0]] = key_value_pair[1]

# MS_export_path = str_params["out"]
# zipped_arlcl_results_path = str_params["arlcl_out"]
# DB_path = str_params["db"]
# scenarios_path = str_params["batch"]
# input_log_path = str_params["log"]
# model = str_params["model"]
# scenario_idx = int(str_params["scenario_id"])
# input_seed = int(str_params["seed"])
# last_evaluation_id = int(str_params["end_iter"])
# optimization_iterations = int(str_params["opts"])
# learn_rate = float(str_params["learn_rate"])

# np.random.seed(input_seed)


parser = argparse.ArgumentParser(description='Mass-Spring Localization')
parser.add_argument('--out', type=str, default="MS_Results", help='Path to store the Mass-Spring results')
parser.add_argument('--arlcl_out', type=str, default="ARLCL_Results", help='Path to the ARLCL results')
parser.add_argument('--db', type=str, default="DB", help='Path to the database')
parser.add_argument('--batch', type=str, default="scenarios.txt", help='Path to the scenarios file')
parser.add_argument('--log', type=str, default="logs", help='Path to the logs')
parser.add_argument('--model', type=str, default="ble", help='Model to use (ble or uwb)')
parser.add_argument('--scenario_id', type=int, default=0, help='Scenario ID to process')
parser.add_argument('--seed', type=int, default=0, help='Seed for random number generator')
parser.add_argument('--end_iter', type=int, default=0, help='Last evaluation iteration')
parser.add_argument('--opts', type=int, default=1000, help='Number of optimization iterations')
parser.add_argument('--learn_rate', type=float, default=0.1, help='Learning rate for the optimizer')
args = parser.parse_args()
# print(args, flush=True)
# print(sys.argv[0])
MS_export_path = args.out
zipped_arlcl_results_path = args.arlcl_out
DB_path = args.db
scenarios_path = args.batch
input_log_path = args.log
model = args.model
scenario_idx = args.scenario_id
input_seed = args.seed
last_evaluation_id = args.end_iter
optimization_iterations = args.opts
learn_rate = args.learn_rate

np.random.seed(input_seed)

def get_cur_scenario(eval_scenarios, eval_scenario_id):
    with open(eval_scenarios) as fp:
        for i, line in enumerate(fp):
            if i == eval_scenario_id:
                split_line = line.replace("\n", "").split(" ")
                filename = split_line[0] + "_" + split_line[1].replace("(", "").replace(")", "") + "_" + split_line[2]
                break
    return filename


# Use the provided ID to identify the scenario
# TODO: One can implement his own way of loading the scenario. Current approach is used for the needs of SLURM cluster
scenario = get_cur_scenario(scenarios_path, scenario_idx)
# ONE CAN EVEN UNCOMMENT THIS TO SET MANUALLY A SCENARIO
# scenario = "A_1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40_5"


def log_progress(entry):
    global logged_lines
    # print(entry, flush=True)
    logged_lines.append(str(entry)+"\n")



class MassSprings(nn.Module):
    def __init__(self, indices, l0, k, num_vertices):
        super().__init__()
        self.indices = indices
        self.register_buffer("incidence", make_incidence(indices, num_vertices))
        self.register_buffer("l0", l0)
        self.register_buffer("k", k)

    def energy(self, x):
        d = self.incidence.mm(x)
        q = d.pow(2).sum(1)
        l = (q + 1e-6).sqrt()
        dl = l - self.l0
        e = 0.5 * (self.k * dl.pow(2)).sum()
        # print(e, flush=True)
        return e


def make_incidence(indices, num_vertices):
    # this creates a dense matrix (incidence), but
    # sparse matrices or convolutions might be more appropriate
    # in certain cases
    num_springs = len(indices)
    incidence = torch.zeros(num_springs, num_vertices, dtype=torch.float32)
    for i, item in enumerate(indices):
        i1, i2 = item
        incidence[i, i1] = 1
        incidence[i, i2] = -1
    return incidence


def get_reference_node_id_from_log_entry(parsed_line):
    flag = "Node: "

    start_index = parsed_line.find(flag)
    end_index = parsed_line.find(", ", start_index, -1)

    return int(parsed_line[start_index + len(flag): end_index])


def get_initial_random_node_pos_from_log_entry(parsed_line):
    x_start_flag = "["
    x_start_index = find_nth(parsed_line, x_start_flag, 1)
    x_end_flag = ", "
    x_end_index = find_nth(parsed_line, x_end_flag, 3)
    x_pos = float(parsed_line[x_start_index + len(x_start_flag): x_end_index].replace(",", "."))

    y_start_flag = ", "
    y_start_index = find_nth(parsed_line, y_start_flag, 3)
    y_end_flag = "]"
    y_end_index = find_nth(parsed_line, y_end_flag, 1)
    y_pos = float(parsed_line[y_start_index + len(y_start_flag): y_end_index].replace(",", "."))

    return [x_pos, y_pos]


def find_nth(given_string, part, n):
    parts = given_string.split(part, n + 1)
    if len(parts) <= n+1:
        return -1
    return len(given_string) - len(parts[-1]) - len(part)


def unzip_arlcl_results():
    # Check if we have already extracted the ARLCL results
    if not file_exists(ARLCL_temp_export_scenario_path):
        log_progress("Extracting the ARLCL data at " + ARLCL_temp_export_scenario_path)
        with zipfile.ZipFile(ARLCL_zipped_scenario_path, 'r') as zipObj:
            for sub_file in zipObj.namelist():
                if sub_file.endswith(".log"):
                    zipObj.extract(sub_file, path=ARLCL_temp_export_path, pwd=None)


def get_initial_positions(eval_iter):

    temp_initial_vertex_positions = []

    arlcl_exported_eval_scenario_results_path = ARLCL_temp_export_scenario_path + "/" + str(eval_iter) + "/results.log"

    log_progress("Opening " + arlcl_exported_eval_scenario_results_path)

    with open(arlcl_exported_eval_scenario_results_path, 'r') as arlcl_results_file:
        for line in arlcl_results_file:

            # print(line, flush=True)

            if line[0:4] == "Node":

                # print(line, flush=True)

                # Get the reference Node ID
                node_id = get_reference_node_id_from_log_entry(line)

                # Get the initial random Node pos
                temp_initial_vertex_positions.append(get_initial_random_node_pos_from_log_entry(line))
                # print("Node: " + str(node_id) + ", Pos: " + str(node_pos), flush=True)

    torch.tensor(temp_initial_vertex_positions, dtype=torch.float32)
    # print(temp_initial_vertex_positions, flush=True)
    return torch.tensor(temp_initial_vertex_positions, dtype=torch.float32)


# springs, specified as vertex indices
def get_spring_connections(eval_iter):

    temp_original_index_to_custom_index_mapping = {}
    temp_custom_index_to_original_index_mapping = {}

    temp_indices = []
    temp_weights = []

    with open(scenario_DB_path, 'r') as input_data:

        new_section_for_averaged_resampling = False

        for line in input_data:

            line = line.replace("\n", "")
            if line == "#" + measurement[model]["unit"] + "_" + str(eval_iter) + "#":
                new_section_for_averaged_resampling = True
                continue
            if new_section_for_averaged_resampling:
                # Identify the end of current iter section to exit
                # (to avoid parsing sampled measurements corresponding to other evaluation repetitions)
                if line == "":
                    return temp_indices, torch.tensor(temp_weights,
                                                      dtype=torch.float32), temp_custom_index_to_original_index_mapping

                line_parts = line.split(":")
                node_id_parts = line_parts[0].split(";")

                nodeA_id = int(node_id_parts[0])
                nodeB_id = int(node_id_parts[1])

                if (nodeA_id not in temp_original_index_to_custom_index_mapping):
                    custom_index = len(temp_original_index_to_custom_index_mapping)

                    temp_original_index_to_custom_index_mapping[nodeA_id] = custom_index
                    temp_custom_index_to_original_index_mapping[custom_index] = nodeA_id

                if (nodeB_id not in temp_original_index_to_custom_index_mapping):
                    custom_index = len(temp_original_index_to_custom_index_mapping)

                    temp_original_index_to_custom_index_mapping[nodeB_id] = custom_index
                    temp_custom_index_to_original_index_mapping[custom_index] = nodeB_id

                custom_nodeA_id = temp_original_index_to_custom_index_mapping[nodeA_id]
                custom_nodeB_id = temp_original_index_to_custom_index_mapping[nodeB_id]

                node_id_pairs = [custom_nodeA_id, custom_nodeB_id]
                temp_indices.append(node_id_pairs)

                current_distance = float(line_parts[1].split("&")[1].replace(",", "."))

                # print(current_distance, flush=True)

                temp_weights.append(current_distance)

        # Being here means that we have finished iterating the file
        return temp_indices, torch.tensor(temp_weights, dtype=torch.float32), temp_custom_index_to_original_index_mapping


def store_positioning_results(exported_results_filename, vertex_positions, index_mapping):
    # print(vertex_positions, flush=True)
    # print(index_mapping, flush=True)

    with open(exported_results_filename, "w") as out_data:
        for nodeID in range(len(index_mapping)):
            line_to_write = "Node:" + str(index_mapping[nodeID]) + ";" + str(round(vertex_positions[nodeID][0].item(), 3)) + ":" + str(round(vertex_positions[nodeID][1].item(), 3)) + "\n"
            # print(line_to_write, flush=True)
            # line_to_write = str(round(vertex_positions[nodeID][0].item(), 3)) + ";" + str(round(vertex_positions[nodeID][1].item(), 3)) + "\n"  # TODO Debugging line
            out_data.write(line_to_write)


def calculate_swarm_positions(eval_iter, total_opts, scenario_eval_results_path):

    # vertex positions
    vertex_positions = get_initial_positions(eval_iter)
    vertex_positions.requires_grad_()
    # print(vertex_positions, flush=True)

    # springs, specified as vertex indices and rest_lengths as weights
    indices, rest_lengths, custom_index_to_original_index_mapping = get_spring_connections(eval_iter)

    # print(indices, flush=True)
    # print(rest_lengths, flush=True)
    # print(custom_index_to_original_index_mapping, flush=True)

    num_vertices, d = vertex_positions.shape
    num_springs = len(indices)

    # stiffness
    k = torch.ones(num_springs, dtype=torch.float32)

    springs = MassSprings(indices, rest_lengths, k, num_vertices)

    optimizer = torch.optim.Adam([vertex_positions], lr=learn_rate)

    for i in range(total_opts):
        optimizer.zero_grad()
        loss = springs.energy(vertex_positions)
        # Check the loss
        print('epoch: ', i, "; loss: ", loss, flush=True)
        loss.backward()
        optimizer.step()

    store_positioning_results(scenario_eval_results_path, vertex_positions, custom_index_to_original_index_mapping)


def file_exists(filepath):
    if os.path.exists(filepath):
        return True
    return False


def eval_id_already_available(export, eval_scenario, eval_id):
    filepath = export + eval_scenario
    if os.path.isfile(filepath):
        log_progress("Folder exists")
        return True
    return False


def delete_folder(path):
    log_progress("Deleting possible leftovers at " + path)
    try:
        shutil.rmtree(path)
    except OSError as e:
        log_progress("Notice: %s - %s." % (e.filename, e.strerror))


def run():
    log_progress("\nCheck whether the final Mass-Spring results for current scenario (" + scenario + ") already exist.")
    # Check first whether the final Mass-Spring results for this scenario (a zip file) already exist
    if file_exists(MS_zip_scenario_path):
        log_progress("Current scenario (" + scenario + ") has already been processed successfully.")

        # Clean any probable old temporal ARLCL or Mass-Spring data, related to current scenario
        delete_folder(ARLCL_temp_export_scenario_path)
        delete_folder(MS_export_scenario_path)

        # Since the file already exists, we can terminate the script here
        raise Exception
    else:
        log_progress("The final Mass-Spring results for current scenario (" + scenario + ") do not exist.")
        # Clean any probable old temporal ARLCL data, related to current scenario
        delete_folder(ARLCL_temp_export_scenario_path)

        # Since the final Mass-Spring results for current scenario is not yet available,
        # unzip in the temp folder, the corresponding ARLCL results for this scenario
        unzip_arlcl_results()

    # At this point we are sure that we have unzipped the ARLCL results related to this scenario
    # Also, although we did not find the final Mass-Spring results for this scenario,
    # check whether there are any older preprocessed data
    if not file_exists(MS_export_scenario_path):
        log_progress("Scenario " + scenario + " has not been initiated before. Creating folder.")
        # if not, then we can create the folder and continue
        os.mkdir(MS_export_scenario_path)
    else:
        log_progress("Scenario " + scenario + " has been initiated before but is not complete. Continuing the evaluations.")

    # Remember that eval=0 is perfect
    for eval_iter in range(last_evaluation_id + 1):
        log_progress("\nStart optimizing evaluation scenario of ID: " + str(eval_iter))

        ms_exported_eval_scenario_path = os.path.join(MS_export_scenario_path, str(eval_iter))
        ms_exported_eval_scenario_results_path = os.path.join(ms_exported_eval_scenario_path, "results.log")
        log_progress("Searching for previous optimization results at: " + ms_exported_eval_scenario_results_path)

        # Check first whether current evaluation iteration has results ready
        if file_exists(ms_exported_eval_scenario_results_path):
            log_progress("Previous results for eval scenario " + scenario + " found")
            log_progress("Skipping current evaluation iteration")
            pass
        else:
            log_progress("No previous results found")
            # Clean and recreate the target Mass-Spring results folder, related to current scenario
            delete_folder(ms_exported_eval_scenario_path)
            os.mkdir(ms_exported_eval_scenario_path)

            calculate_swarm_positions(eval_iter, optimization_iterations, ms_exported_eval_scenario_results_path)

        # exit()  # Used to constraint only to 1 iteration


def zip_ms_results():
    log_progress("Storing the Mass-Spring Results data at " + MS_zip_scenario_path)

    zipf = zipfile.ZipFile(MS_zip_scenario_path, 'w', zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(MS_export_scenario_path):
        for file in files:
            zipf.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(MS_export_scenario_path, '..')))
    zipf.close()


def set_paths():
    global DB_path, scenario, scenario_DB_path, MS_export_scenario_path, MS_zip_scenario_path, \
        ARLCL_zipped_scenario_path, ARLCL_temp_export_path, ARLCL_temp_export_scenario_path, measurement, model, \
        zipped_arlcl_results_path, MS_export_path

    parent_arlcl_results_dir = os.path.dirname(zipped_arlcl_results_path)

    scenario_DB_path = os.path.join(DB_path, scenario + measurement[model]["db_ext"])

    if not os.path.exists(MS_export_path):
        os.makedirs(MS_export_path)
        os.chmod(MS_export_path, 0o777)

    MS_export_scenario_path = os.path.join(MS_export_path, scenario)
    MS_zip_scenario_path = MS_export_scenario_path + ".zip"
    ARLCL_zipped_scenario_path = os.path.join(zipped_arlcl_results_path, scenario + ".zip")
    ARLCL_temp_export_path = os.path.join(parent_arlcl_results_dir, model.upper() + "_Estimations_temp_unzipped")

    if not os.path.exists(ARLCL_temp_export_path):
        os.makedirs(ARLCL_temp_export_path)
        os.chmod(ARLCL_temp_export_path, 0o777)

    ARLCL_temp_export_scenario_path = os.path.join(ARLCL_temp_export_path, scenario)

    log_progress("\nSetting other paths: ")
    log_progress("scenario db path: " + scenario_DB_path)
    log_progress("MS export path: " + MS_export_path)
    log_progress("MS export scenario path: " + MS_export_scenario_path)
    log_progress("MS zip scenario path: " + MS_zip_scenario_path)
    log_progress("ARLCL zipped scenario path: " + ARLCL_zipped_scenario_path)
    log_progress("ARLCL export path: " + ARLCL_temp_export_path)


try:
    log_progress("Starting")
    log_progress("\nInput params: ")
    log_progress(str_params)

    # Set the required paths first
    set_paths()

    # Execute the optimization
    run()

    # Store the results and clean the temp folder
    zip_ms_results()

    print(MS_export_scenario_path, flush=True)
    print(ARLCL_temp_export_scenario_path, flush=True)

    delete_folder(MS_export_scenario_path)
    # Clean any probable old temporal ARLCL data, related to current scenario
    delete_folder(ARLCL_temp_export_scenario_path)

except Exception as e:
    print("Termination %s" % e, flush=True)

with open(os.path.join(input_log_path, scenario + ".log"), "w") as log_data:
    for line in logged_lines:
        log_data.write(line)