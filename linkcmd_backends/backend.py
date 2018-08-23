from math import ceil

#
# "Interface" - methods
# def get_common_setup_commands(CONFIG):
# def get_indiv_setup_commands(CONFIG, line, local_id, remote_id):
# def get_indiv_change_commands(CONFIG, line, local_id, remote_id):
#

class Backend:
    def __init__(self):
        pass


    def calculate_TBF_burstsize(self, target_bitrate, config_hz, link_mtu):
        # burst >= target_bitrate / CONFIG_HZ       # target_bitrate is in kbps/Kbit/s
        burst = ceil((target_bitrate * 1000) / (config_hz * 8))
        return max(link_mtu, burst)  # make sure to stay >= MTU at all times


    def getEmuIpFromId(self, id, config):
        return config["EMU_PREFIX"] + str(config["HOST_IP_START"] + int(id))

    def getHostByteFromId(self, id, config):
        return str(config["HOST_IP_START"] + int(id))


    # returns the commands to setup common interface-properties indifferent of the number of connections
    # returns commands for the local node only
    def get_common_setup_commands(self, config):
        cmds = ["#!/bin/sh"]
        return cmds


    # returns setup-commands specific for a connection to a remote ip
    # returns only commands for the local node
    def get_indiv_setup_commands(self, config, mapping, line, local_id, remote_id):
        local_setup_cmds = []
        remote_setup_cmds = []
        return local_setup_cmds, remote_setup_cmds


    # returns commands to change link properties over time
    # returns only commands for the local node
    def get_indiv_change_commands(self, config, mapping, line, local_id, remote_id):
        local_change_cmds = []
        remote_change_cmds = []
        return local_change_cmds, remote_change_cmds

    def __str__(self):
        return self.__class__.__name__
