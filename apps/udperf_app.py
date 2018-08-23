import os
from .. import constants
from . import application

class UdperfApp(application.Application):
    def __init__(self, sender, receiver, start, duration, rate, server_port, client_port):
        self.sender = sender
        self.receiver = receiver
        self.rate = rate
        self.startTime = start
        self.duration = duration
        self.server_port = server_port
        self.client_port = client_port


    def generateCommands(self, config):
        trafficFlow = str(self.sender.getId()) + "_" + str(self.receiver.getId())
        # stop all currently running instances of server
        self.receiver.scheduleCmd(constants.SETUP_TIME,"sudo killall udperf_sink")

        # start new server instance
        output_path = os.path.join(config['REMOTE_RESULT_DIR'], trafficFlow + ".sink.log")
        #self.receiver.addResult(output_path, os.path.join(config['RESULT_DIR'], trafficFlow + ".sink.log_%RUN%.zip"))
        self.receiver.addAppResult(output_path, os.path.join(config['RESULT_DIR'], trafficFlow + ".sink.log_%RUN%"))
        self.receiver.scheduleCmd(constants.SETUP_TIME,"udperf_sink " + str(self.server_port) + " " + output_path + " > /dev/null 2>&1 &")

        # stop all currently running instances of client/sender
        self.sender.scheduleCmd(constants.SETUP_TIME,"sudo killall udperf_sender")

        # start new client(==sender)-instance at begin of emulation
        output_path = os.path.join(config['REMOTE_RESULT_DIR'], trafficFlow + ".sender.log")
        #self.sender.addResult(output_path, os.path.join(config['RESULT_DIR'], trafficFlow + ".sender.log_%RUN%.zip"))
        self.sender.addAppResult(output_path, os.path.join(config['RESULT_DIR'], trafficFlow + ".sender.log_%RUN%"))
        self.sender.scheduleCmd(self.startTime , "(sudo chrt -o -p 0 $BASHPID && udperf_sender " +
                                self.receiver.getEmuIP(config) + " " + str(self.server_port) + " " + str(self.rate) + " " +
                                str(self.duration) + " " + str(self.client_port) + " " + output_path + " & )&")

        # explicitly stop server/sink at end of emulation
        self.receiver.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall udperf_sink")


