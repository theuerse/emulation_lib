import os
from .. import constants
from . import application

class NDN_DemoAppsWLDR(application.Application):
    def __init__(self, server, clients, gateways, start, duration, server_params, client_params, routingcmds):
        self.server = server
        self.clients = clients
        self.gateways = gateways
        self.startTime = start
        self.duration = duration
        self.server_params = server_params
        self.client_params = client_params


    def generateCommands(self, config):
        server_exe = "dashproducer"
        client_exe = "dashplayer_WLDR"

        # (sudo chrt -o -p 0 $BASHPID &&  dashplayer_WLDR --name /Node1/BBB_first100.mpd -r 12000 -l 500 -a buffer -o /home/nfd/emulation/results/consumer.log &) &
        wldr_daemon_cmd = "(sudo chrt -o -p 0 $BASHPID && wldrdaemon_udp -l /var/run/shm/nfd_packet_log/nfd_packet_log.csv"

        # start new server instance
        self.server.scheduleCmd(constants.SETUP_TIME,"sudo " + server_exe + " " + self.server_params.strip() + " &")

        # explicitly stop server at end of emulation
        self.server.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall " + server_exe)

        wlans = {}
        # add commands for clients
        for i in range(0, len(self.clients)):
            client = self.clients[i]
            gateway = self.gateways[i]
            client_accessPoint_ip = gateway.getEmuIP(config)

            if gateway not in wlans:
                wlans[gateway] = [client.getEmuIP(config)]
            else:
                wlans[gateway].append(client.getEmuIP(config))

            # start new client instance at begin of emulation
            output_path = os.path.join(config['REMOTE_RESULT_DIR'], "consumer.log")

            client.scheduleCmd(constants.SETUP_TIME, "sudo killall wldrdaemon_udp")
            client.scheduleCmd(constants.SETUP_TIME, "fuser -k 12345/udp")  # kill all application occupying the TCP-port 12345

            # schedule server-side wldr-instance to start
            client.scheduleCmd(self.startTime, wldr_daemon_cmd + " -d " + client_accessPoint_ip + " > demonlog.txt 2>&1 &) & ")


            client.addAppResult(output_path, os.path.join(config['RESULT_DIR'], "consumer_" + str(client.getId()) + ".log_%RUN%"))
            client.scheduleCmd(self.startTime , "(sudo chrt -o -p 0 $BASHPID &&  " + client_exe + " " + self.client_params + " -o " + output_path
                               + " > /home/nfd/dashplayerlog.txt 2>&1 &) &")

            # explicitly stop client at end of emulation
            client.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall " + client_exe)
            client.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall wldrdaemon_udp")
            client.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall tail")

        for accessPoint in wlans:
            client_str = " -i ".join(wlans[accessPoint])
            accessPoint.scheduleCmd(constants.SETUP_TIME, "sudo killall wldrdaemon_udp")
            accessPoint.scheduleCmd(constants.SETUP_TIME, "fuser -k 12345/udp ")
            accessPoint.scheduleCmd(constants.SETUP_TIME, wldr_daemon_cmd + " -i " + client_str + " > demonlog.txt 2>&1 &) &")
            accessPoint.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall wldrdaemon_udp")
            accessPoint.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall tail")
