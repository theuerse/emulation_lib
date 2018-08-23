import os
from .. import constants
from . import application

class NDN_DemoApps(application.Application):
    def __init__(self, server, clients, start, duration, server_params, client_params, routingcmds):
        self.server = server
        self.clients = clients
        self.startTime = start
        self.duration = duration
        self.server_params = server_params
        self.client_params = client_params


    def generateCommands(self, config):
        server_exe = "dashproducer"
        client_exe = "dashplayer_WLDR"

        self.server.scheduleCmd(constants.SETUP_TIME, "sudo killall wldrdaemon_udp")
        self.server.scheduleCmd(constants.SETUP_TIME, "fuser -k 12345/udp ")

        # start new server instance
        self.server.scheduleCmd(constants.SETUP_TIME,"sudo " + server_exe + " " + self.server_params.strip() + " &")

        # explicitly stop server at end of emulation
        self.server.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall " + server_exe)

        # add commands for clients
        for client in self.clients:

            client.scheduleCmd(constants.SETUP_TIME, "sudo killall wldrdaemon_udp")
            client.scheduleCmd(constants.SETUP_TIME, "fuser -k 12345/udp")  # kill all application occupying the TCP-port 12345

            # start new client instance at begin of emulation
            output_path = os.path.join(config['REMOTE_RESULT_DIR'], "consumer.log")

            client.addAppResult(output_path, os.path.join(config['RESULT_DIR'], "consumer_" + str(client.getId()) + ".log_%RUN%"))
            client.scheduleCmd(self.startTime , "(sudo chrt -o -p 0 $BASHPID &&  " + client_exe + " " + self.client_params + " -o " + output_path + " > /home/nfd/dashplayerlog.txt 2>&1 & )&")

            # explicitly stop client at end of emulation
            client.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall " + client_exe)


# usage examples of the applications
# sudo ./dashproducer --prefix /Server --document-root /home/nfd/data/concatenated/ --data-size 4096
# dashplayer --name /Server/BBB_small.mpd -r 2000 -t 20 -l 200 -a buffer -o ./consumer.log

