import os
import emulation_lib.ssh_lib as ssh
import logging
from datetime import datetime
from datetime import timedelta
from multiprocessing.dummy import Pool as ThreadPool
import time
from . import constants

CONFIG = {}
EXPECTED_RESULTFILES = {}
CONFIG_FILES = {}

REMOTE = 0
LOCAL = 1

setup_scripts = []
runtime_scripts = []
cmd = ""
logger = logging.getLogger("emulation_lib")
logger.setLevel(logging.INFO)


def inventorize_scripts():
    global setup_scripts
    global runtime_scripts

    # setup-scripts
    for filename in [f for f in os.listdir(CONFIG["COMMAND_DIR"]) if f.endswith(constants.SETUP_SCRIPT_POSTFIX)]:
        name = filename.replace(constants.SETUP_SCRIPT_POSTFIX, "")
        if name not in setup_scripts:
            setup_scripts.append(name)

    # runtime-scripts
    for filename in [f for f in os.listdir(CONFIG["COMMAND_DIR"]) if f.endswith(constants.RUNTIME_SCRIPT_POSTFIX)]:
        name = filename.replace(constants.RUNTIME_SCRIPT_POSTFIX, "")
        if name not in runtime_scripts:
            runtime_scripts.append(name)
    return


def perform_sanity_checks():
    for ip in setup_scripts:
        if ip not in runtime_scripts:
            raise ValueError(ip + " is missing a corresponding runtime-script, aborting ...")

    for ip in runtime_scripts:
        if ip not in setup_scripts:
            raise ValueError(ip + " is missing a corresponding setup-script, aborting ...")


def perform_setup(ip):
    s = ssh.Connection(ip, CONFIG["SSH_USER"], password=CONFIG["SSH_PASSWORD"])

    # create folder structure
    foldercmd = "mkdir -p " + CONFIG["REMOTE_EMULATION_DIR"] + " " + CONFIG["REMOTE_CONFIG_DIR"] + " " + CONFIG["REMOTE_RESULT_DIR"] + " " + CONFIG["REMOTE_DATA_DIR"]
    s.execute(foldercmd)

    target_setup_file = os.path.join(CONFIG["REMOTE_CONFIG_DIR"], constants.SETUP_SCRIPT_POSTFIX)
    target_runtime_file = os.path.join(CONFIG["REMOTE_CONFIG_DIR"], constants.RUNTIME_SCRIPT_POSTFIX)

    # transmit setup- and runtime-scripts
    s.put(os.path.join(CONFIG["COMMAND_DIR"], ip + constants.SETUP_SCRIPT_POSTFIX), target_setup_file)
    s.put(os.path.join(CONFIG["COMMAND_DIR"] + "/" + ip + constants.RUNTIME_SCRIPT_POSTFIX), target_runtime_file)

    # transmit config-files
    for config_file in CONFIG_FILES[ip]:
        s.put(config_file[LOCAL], config_file[REMOTE]) # transmit config-file

    s.execute("chmod +x " + target_setup_file)

    result = s.execute(target_setup_file + " > /dev/null 2>&1 ; date -u; echo 'finished setup'") # wait for completion
    logger.info(ip + ": " + str(result))

    s.close()
    return


def execute_runtime_script(ip):
    s = ssh.Connection(ip, CONFIG["SSH_USER"], password=CONFIG["SSH_PASSWORD"])
    result = s.execute("screen -d -m " + cmd)
    #logger.info(result)
    s.close()
    return


def collect_traces(ip):
    s = ssh.Connection(ip, CONFIG["SSH_USER"], password=CONFIG["SSH_PASSWORD"])
    for fileTuple in EXPECTED_RESULTFILES[ip]:
        parentdir = os.path.dirname(fileTuple[LOCAL])
        if not os.path.isdir(parentdir):
            os.makedirs(parentdir) # ensure local folder structure exists

        if fileTuple[LOCAL].endswith(".zip"): # zip first
            s.execute("rm " + fileTuple[REMOTE] + ".zip") # remove eventually already existing file
            s.execute("cd " + os.path.dirname(fileTuple[REMOTE]) + " && zip -j " + os.path.basename(fileTuple[REMOTE]) +
                      ".zip " + os.path.basename(fileTuple[REMOTE]))
            s.get(fileTuple[REMOTE] + ".zip", fileTuple[LOCAL])
        else:
            s.get(fileTuple[REMOTE], fileTuple[LOCAL])
    s.close()


#
# main entry-point of the program
#
def start_emulation_run(duration, expectedResultfiles, configFiles, config):
    global cmd
    global CONFIG
    global EXPECTED_RESULTFILES
    global CONFIG_FILES

    CONFIG = config
    EXPECTED_RESULTFILES = expectedResultfiles
    CONFIG_FILES = configFiles

    # inventorize scripts
    inventorize_scripts()

    # perform sanity-checks (e.g. there must be a runtime-script for every setup-script and vice versa)
    perform_sanity_checks()

    # deploy scripts + run all setup-scripts and await their termination
    logger.info("Performing the setup (script-distribution + run all setup-scripts) ...")
    pool = ThreadPool()
    results = pool.map(perform_setup, setup_scripts)
    pool.close()
    pool.join()
    # logger.info(results)

    # run all runtime-scripts (async ssh-ops towards single starting-time for all nodes)
    logger.info("Starting all runtime-scripts (" + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ")")
    start = datetime.utcnow() + timedelta(seconds=CONFIG["MIN_START_TIME_OFFSET"]) + timedelta(seconds=1)

    start_time = start.strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(CONFIG["RESULT_DIR"] + 'start_times.txt'), 'a') as time_index: # save common start time for every run
        time_index.write(str(CONFIG["RUN"]) + '\t' + start_time + '\n')
    logger.info("Coordinated start at: " + start_time)

    # build runtime-script-command
    cmd = "cmdScheduler " + os.path.join(CONFIG["REMOTE_CONFIG_DIR"],constants.RUNTIME_SCRIPT_POSTFIX) + " " + start_time

    # call start-scripts
    pool = ThreadPool()
    pool.map(execute_runtime_script, setup_scripts)
    pool.close()
    pool.join()

    logger.info("Waiting for emulation to end")
    emulationEnd = start + timedelta(seconds=duration)
    time.sleep((emulationEnd - datetime.utcnow()).seconds + 1) # '+1' ... account for rounding errors

    # collect result-files
    logger.info("Waiting five seconds for logfiles to be written (" + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ")")
    time.sleep(5)  # wait for (eventual) logfiles to be written
    logger.info("Collecting results (" + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') + ")")
    pool = ThreadPool()
    pool.map(collect_traces, expectedResultfiles)
    pool.close()
    pool.join()