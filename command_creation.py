# IPs encoded in intermediate-format-file-headers are EMU-(PREFIX)-IPs
import os
import sys
import math
from . import constants

CONFIG = {}
OUTPUT_DIRECTORY = ""
INTERVAL = ""

CMD_DICT = {}


def readIntermediateFile(filename):
    node_Ids = os.path.basename(filename).replace(constants.INTERMED_FILE_FILEEXT, '').split(constants.SEPERATOR)

    local_id = node_Ids[0]
    remote_id = node_Ids[1]

    backend = CONFIG["LINK_CMD_BACKEND"]

    with open(filename, 'r') as intermediate_file:
                 lines = intermediate_file.readlines()

    if not local_id in CMD_DICT:
        CMD_DICT[local_id] = {-1: backend.get_common_setup_commands(CONFIG)}
    if not remote_id in CMD_DICT:
        CMD_DICT[remote_id] = {-1: backend.get_common_setup_commands(CONFIG)}

    mapping = {}
    for entry in lines[0].rstrip().split(","):
        mapping[entry.strip()] = len(mapping.keys())

    initial_configuration = lines[1]
    local_cmds, remote_cmds = backend.get_indiv_setup_commands(CONFIG, mapping, initial_configuration, local_id, remote_id)

    # negative time-index stands for preparation/setup-phase before the emulation starts
    CMD_DICT[local_id][-1] += local_cmds
    CMD_DICT[remote_id][-1] += remote_cmds

    # create application-start command (executes at offset 0.0, right at the beginning of the runtime-emulation)
    # cmds.append("0.0\t" + CONFIG["get_runtime_begin_cmd"](receiver_IPs))  # Hook for runtime-emulation begin

    last_changes = initial_configuration.split()[1:] # keep track of last line as to avoid doing the same thing n-times

    for line in lines[2:]:
        changes = line.split()[1:]
        if  changes == last_changes:
            continue # nothing changed => nothing to do
        else:
            last_changes = changes

        starting_offset = float(line.split()[mapping["start"]])

        # experimental pre-request to account for tc-change duration
        #preschedule_interval = 0.050 # 0.050 ... 50ms in seconds
        #if starting_offset > preschedule_interval:
        #    starting_offset -= preschedule_interval

        local_cmds, remote_cmds = backend.get_indiv_change_commands(CONFIG, mapping, line, local_id, remote_id)

        if not starting_offset in CMD_DICT[local_id]:
            CMD_DICT[local_id][starting_offset] = []
        if not starting_offset in CMD_DICT[remote_id]:
            CMD_DICT[remote_id][starting_offset] = []
        CMD_DICT[local_id][starting_offset] += local_cmds
        CMD_DICT[remote_id][starting_offset] += remote_cmds


def writeSetupFiles():
    for id in CMD_DICT:
        if -1 in CMD_DICT[id]:
            # create setup-script
            with open (os.path.join(OUTPUT_DIRECTORY, CONFIG["MNG_PREFIX"] + str(CONFIG["HOST_IP_START"] + int(id)) + "_setup.sh"), 'w') as setup_script:
                for cmd in CMD_DICT[id][-1]:
                    setup_script.write("%s\n" % cmd)


def writeChangeFiles():
    for id in CMD_DICT:
        timePoints = list(CMD_DICT[id].keys())
        timePoints.sort()

        # create runtime_script
        with open(os.path.join(OUTPUT_DIRECTORY, CONFIG["MNG_PREFIX"] + str(CONFIG["HOST_IP_START"] + int(id)) + "_runtime.cmd"), 'w') as runtime_script:
            for time_point in timePoints:
                if time_point < 0: continue
                if len(CMD_DICT[id][time_point]) == 0: # only create line/entry if there is actually something to do
                    continue

                tc_cmds = []
                other_cmds = []
                for cmd in CMD_DICT[id][time_point]:
                    if cmd.startswith("qdisc"):
                        tc_cmds.append(cmd)
                    else:
                        other_cmds.append(cmd)

                tc_cmd = 'printf "' + "\\n".join(tc_cmds) + '\\n" | sudo tc -batch -'
                cmd = tc_cmd if len(tc_cmds)> 0 else ""

                # append other cmds after tc-batch cmd (avoid concatenating commands ending with & using ; [problematic])
                for other_cmd in other_cmds:
                    other_cmd = other_cmd.rstrip()

                    # try to connect cmd with other command
                    if len(cmd) > 0 and not cmd.rstrip().endswith(';') and not cmd.endswith('&'):
                        cmd = ' '.join([cmd,'&'])

                    if other_cmd.endswith('&'):
                        cmd += " " + other_cmd
                    else:
                        cmd += "; " + other_cmd

                while cmd.startswith(';'): # remove unsightly preceding ';'
                    cmd = cmd[2:]

                cmd = str(time_point) + "\t" + cmd.lstrip()
                runtime_script.write("%s\n" % cmd)

# appends the explicit commands from the configfile to to command-dictionary
def import_scheduled_commands():
    global CMD_DICT

    scheduled_commands = CONFIG["SCHEDULED_CMD_DICT"]

    for node_id in scheduled_commands:
        if not node_id in CMD_DICT:
            CMD_DICT[node_id] = {}

        for time_point in scheduled_commands[node_id]:
            if not time_point in CMD_DICT[node_id]:
                CMD_DICT[node_id][time_point] = []

            CMD_DICT[node_id][time_point] += scheduled_commands[node_id][time_point]

#
# main entry point of the application
#
def createEmulationCommands(src_directory, output_directory, config):
    global OUTPUT_DIRECTORY
    global CONFIG
    global INTERVAL
    global CMD_DICT

    CMD_DICT = {} # reset command-dictionary

    src_directory = os.path.abspath(src_directory)
    OUTPUT_DIRECTORY = output_directory
    CONFIG = config

    for intermediateFile in os.listdir(src_directory):
        readIntermediateFile(os.path.join(src_directory,intermediateFile))

    import_scheduled_commands()
    writeSetupFiles()
    writeChangeFiles()