import os
from .. import constants
from . import application

class CPUlogApp(application.Application):
    def __init__(self, nodes, interval):
        self.nodes = nodes
        self.interval = interval

    def generateCommands(self, config):
        output_path = os.path.join(config['REMOTE_RESULT_DIR'], "cpulog.txt")
        sar_exe = "(sudo chrt -o -p 0 $BASHPID && sar -u " + str(self.interval) + " > " + output_path + " & )&"

        for node in self.nodes:
            node.scheduleCmd(constants.SETUP_TIME, "sudo killall sar")
            node.scheduleCmd(0, sar_exe)
            node.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall sar")

            node.addAppResult(output_path,
                                os.path.join(config['RESULT_DIR'], "cpulog_" + str(node.getId()) + ".txt_%RUN%"))

