import os
import time
from shutil import rmtree
import logging
from .node import Node
from . import constants, command_creation, emulation_execution_run
from .linkcmd_backends.bdl_ import BDL_

class Emulation:
    def __init__(self, config_path, nodeIds):
        self.name = "Emulation"
        self.config_path = os.path.abspath(config_path)
        self.numberOfRuns = None
        self.secondsBetweenRuns = 1
        self.nodeCnt = len(nodeIds)
        self.duration = 0  # emulation-duration in seconds
        self.nodes = []
        self.networkBlocks = []
        for id in nodeIds:
            self.nodes.append(Node(id))

        self.applications = []
        self.staticRoutes = []
        self.loadConfigFile(self.config_path)
        self.outputDirectory = None
        self.linkCmdBackend = BDL_
        self.setup_logging()

    def setup_logging(self):
        # config/start simple logging
        self.logger = logging.getLogger("emulation_lib")
        self.logger.setLevel(logging.INFO)
        # create file handler which logs even info messages
        fh = logging.FileHandler('log.txt')
        fh.setLevel(logging.INFO)
        # create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        # add the handlers to logger
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def loadConfigFile(self, config_path):
        config = {}
        exec (open(config_path).read(), config)
        # TODO: check config-integrity/sanity
        self.config = config

    def getNode(self, id):
        for node in self.nodes:
            if node.getId() == id:
                return node
        raise ValueError("Requested node is not part of emulation!")

    def getNodes(self):
        return self.nodes

    def addApplications(self, applications):
        for app in applications:
            if app in self.applications:
                raise ValueError("Any given application can only be added ONCE to the emulation-object!")
            self.applications.append(app)

    def addNetworkBlocks(self, blocklist):
        for block in blocklist:
            if block in self.networkBlocks:
                raise ValueError("Tried to add name NetworkBlock twice!")
            self.networkBlocks.append(block)

    def removeNetworkBlocks(self, blocklist):
        for block in blocklist:
            if not block in self.networkBlocks:
                raise ValueError("Tried to remove non-existing block!")
            self.networkBlocks.remove(block)

    def setLinkCmdBackend(self, backend):
        self.linkCmdBackend = backend

    def setNumberOfRuns(self, n):
        if n < 0:
            raise ValueError("Number of Runs to perform must be >=0!")
        self.numberOfRuns = n

    def setSecondsBetweenRuns(self, seconds):
        self.secondsBetweenRuns = seconds

    def setStaticRoutes(self, staticRoutes):
        self.staticRoutes = staticRoutes

    def setDuration(self, seconds):
        self.duration = seconds

    def getDuration(self):
        return self.duration

    def setOutputDirectory(self, outputDirectory):
        output_dir = os.path.abspath(outputDirectory)
        if not os.path.isdir(output_dir):
            self.logger.info("Output-directory '" + output_dir + "' does not exist! -> creating ...")
            os.makedirs(output_dir, exist_ok=True)

        if not output_dir.endswith("/"): output_dir += "/"
        self.outputDirectory = output_dir

    def setName(self, name):
        self.name = str(name)

    def getName(self):
        return self.name

    def getNumberOfRuns(self):
        return self.numberOfRuns

    # let every application add their required commands to the respective nodes
    def generateApplicationCommands(self):
        for app in self.applications:
            app.generateCommands(self.config)
            app.generateConfigFiles(self.config)

    def checkConfiguration(self):
        reasonsForAbort = []
        if self.numberOfRuns == None:
            reasonsForAbort.append("Number of runs has not yet been configured!")
        if self.outputDirectory == None:
            reasonsForAbort.append("Output-directory has not yet been configured!")
        for nb in self.networkBlocks:
            if not nb.isIntervalSelected():
                reasonsForAbort.append("No interval-size selected\n\t" + str(nb))
            if None in nb.nodes:
                reasonsForAbort.append("One Slot in Network-Block is empty\n\t" + str(nb))
            if len(nb.getNodes()) != len(set(nb.getNodes())):
                reasonsForAbort.append("Duplicate Nodes in Network-Block\n\t" + str(nb))
        return reasonsForAbort

    def __str__(self):
        output = ["Emulation: " + self.name]
        output.append("Output-directory: " + str(self.outputDirectory))
        output.append("Duration: " + str(self.duration))
        output.append("Number of runs: " + str(self.numberOfRuns))
        output.append("Seconds between runs: " + str(self.secondsBetweenRuns))
        output.append("Path to config-file: " + self.config_path)
        output.append("Link command backend: " + str(self.linkCmdBackend))
        output.append("Static routes: " + str(self.staticRoutes))

        output.append("\n")
        for block in self.networkBlocks:
            output.append(str(block) + "\n")

        output.append("\n")
        for node in self.nodes:
            output.append(str(node) + "\n")

        return '\n'.join(output)

    def getConfigDict(self):
        list = {}
        for node in self.nodes:
            list[node.getMngIP(self.config)] = node.configFiles
        return list

    def getResultDict(self):
        results = {}
        for node in self.nodes:
            resultList = []
            for result in node.app_results + node.user_results:
                # if no parent directory given, place file directly under resultdir
                if not result[1].startswith(self.config['RESULT_DIR']):
                    result = (result[0], os.path.join(self.config['RESULT_DIR'], result[1].lstrip('/')))

                for key in self.config.keys():
                    pattern = '%'+ key +'%'
                    if pattern in result[0] or pattern in result[1]:
                        result = (result[0].replace(pattern, str(self.config[key])), result[1].replace(pattern, str(self.config[key])))

                resultList.append(result)


            if len(resultList) > 0:
                results[node.getMngIP(self.config)] = resultList
        return results

    def getEmuIP(self, nodeId):
        return self.config['EMU_PREFIX'] + str(int(nodeId)+10)

    def applyStaticRouting(self):
        for route in self.staticRoutes:  # node-ids (at, to, via)
            print("applying static route: " + str(route))
            # e.g. sudo ip route add 192.168.0.6 via 192.168.0.1 dev eth0.101
            node_at = self.nodes[route[0]]
            routeStr = self.getEmuIP(route[1]) + " via " + self.getEmuIP(route[2]) + " dev " + self.config["EMU_INTERFACE"]
            node_at.scheduleCmd(constants.SETUP_TIME,"sudo ip route add " + routeStr)
            node_at.scheduleCmd(self.duration, "sudo ip route del " + routeStr) # "manual" removal of route (NO auto-reset as contrasted with iptables)

            # add firewall-exception in order to be able to send to remote receiver
            node_at.scheduleCmd(constants.SETUP_TIME,
                                    "sudo iptables -A OUTPUT -d " + self.getEmuIP(route[1]) + " -j ACCEPT")

            #TODO: remove static routes / clear them all at beginning
            #TODO: add static-routes to default-output

    def start(self,runNumber=-1):
        # establish basic directory structure
        emulation_dir =  self.config['EMULATION_DIR'] = self.outputDirectory
        intermediate_dir = self.config['INTERMEDIATE_DIR'] = os.path.join(emulation_dir, "intermediates/")
        command_dir = self.config['COMMAND_DIR'] = os.path.join(emulation_dir, "commands/")
        result_dir = self.config['RESULT_DIR'] = os.path.join(emulation_dir, "results/")

        self.config["NODE_COUNT"] = self.nodeCnt
        self.config["EMU_DURATION"] = self.duration

        # support starting single runs, as well as batches
        if runNumber == -1:
            runs = range(self.numberOfRuns)  # execute runs 0 .. numberOfRuns
        else:
            runs = [runNumber]  # only execute run "run"
            self.setNumberOfRuns(1)

        if os.path.isdir(intermediate_dir): rmtree(intermediate_dir)  # remove possibly already existing intermediate-dir
        if os.path.isdir(command_dir): rmtree(command_dir)  # remove possibly already existing command-dir
        self.ensure_dirs_exist([emulation_dir, intermediate_dir, command_dir, result_dir])


        reasonsForAbort = self.checkConfiguration()

        if len(reasonsForAbort) > 0:
            self.logger.info("Aborting start, reasons: \n\t" + "\n\t".join(reasonsForAbort))
            exit(1)
        else:
            self.logger.info("Configuration seems ok")

        # reset auto-generated node-information (commands, config-files, result-files)
        for node in self.nodes:
            node.resetApplicationGeneratedData()

        self.logger.info("Finalizing setup by generating the commands/configs needed by the apps")
        self.generateApplicationCommands()

        self.applyStaticRouting() # only if given

        self.logger.info(self.__str__()) # log overview of emulation


        self.logger.info("Garthering intermediate-files")
        for block in self.networkBlocks:
            block.generateIntermediateFiles(intermediate_dir)

        self.logger.info("Creating command-files")
        self.config["LINK_CMD_BACKEND"] = self.linkCmdBackend

        # augment configuration file with user/application-scheduled commands
        scheduledCmdDict = {}
        for node in self.nodes:
            node.scheduleCmd(0.0, "echo emulation-start")
            node.scheduleCmd(float(self.duration),"echo emulation-end")
            scheduledCmdDict[str(node.getId())] = node.getCommandDict()
        self.config["SCHEDULED_CMD_DICT"] = scheduledCmdDict

        # create command-files from intermediates + scheduled commands (in "config")
        command_creation.createEmulationCommands(intermediate_dir, command_dir, self.config)
        self.logger.info("Ready to execute " + self.name)

        # start runs sequentially
        for run in runs:
            self.config["RUN"] = run
            runLabel = str(run)


            expectedResultfiles = self.getResultDict()
            resultFileList = []
            for ip, files in expectedResultfiles.items():
                for file in files:
                    resultFileList.append(file[1]) # add local filename of expected result-file

            if all(os.path.isfile(file) for file in resultFileList):
                self.logger.info("skipping run " + runLabel + ", already performed (result-files found)")
                continue
            else:
                self.logger.info("Starting run " + runLabel)

                emulation_execution_run.start_emulation_run(self.duration, expectedResultfiles, self.getConfigDict(), self.config)

                self.logger.info("Finished run " + runLabel)
                if run  < (self.numberOfRuns - 1):
                    self.logger.info("Waiting for " + str(self.secondsBetweenRuns) + " seconds ...")
                    time.sleep(self.secondsBetweenRuns)

        self.logger.info("Finished all runs, end of emulation")
        self.logger.info("\n\n\n")


    def ensure_dirs_exist(self, directories):
        for dir in directories:
            if not os.path.exists(dir):
                os.makedirs(dir)
