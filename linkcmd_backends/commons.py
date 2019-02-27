# returns the commands to setup common interface-properties indifferent of the number of connections
# returns commands for the local node only
def get_common_setup_commands(config):
    # common part
    cmds = ["#!/bin/sh"]

    # shutdown existing cmdScheduler-instance
    cmds.append("sudo killall cmdScheduler")

    # drop everything by default
    cmds.append("sudo iptables --flush")  # delete all old entries
    cmds.append("sudo iptables -P INPUT DROP")
    cmds.append("sudo iptables -P FORWARD DROP")
    cmds.append("sudo iptables -P OUTPUT DROP")

    # allow local-to-local connections
    cmds.append("sudo iptables -A INPUT -s localhost -d localhost  -j ACCEPT")
    cmds.append("sudo iptables -A FORWARD -d localhost -s localhost -j ACCEPT")
    cmds.append("sudo iptables -A OUTPUT -d localhost -s localhost -j ACCEPT")

    # setup/allow the connection to the ITEC gateway
    cmds.append("sudo iptables -A INPUT -s " + config['GATEWAY_SERVER'] + " -j ACCEPT")
    cmds.append("sudo iptables -A FORWARD -j ACCEPT")
    cmds.append("sudo iptables -A OUTPUT -d " + config['GATEWAY_SERVER'] + " -j ACCEPT")

    # delete all old tc settings (default ceil = rate)
    cmds.append("sudo tc qdisc del dev " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc qdisc del dev " + config["EMU_INTERFACE"] + " ingress")
    cmds.append("sudo tc qdisc del dev ifb0 root")
    cmds.append("sudo tc filter del dev " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc filter del dev ifb0 root")
    cmds.append("sudo tc class del " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc class del ifb0 root")
    cmds.append("")

    return cmds


# returns the commands to setup common interface-properties indifferent of the number of connections
# returns commands for the local node only
def get_common_IFBsetup_commands(config):
    # common part
    cmds = ["#!/bin/sh"]

    # drop everything by default
    cmds.append("sudo iptables --flush")  # delete all old entries
    cmds.append("sudo iptables -P INPUT DROP")
    cmds.append("sudo iptables -P FORWARD DROP")
    cmds.append("sudo iptables -P OUTPUT DROP")

    # setup/allow the connection to the ITEC gateway
    cmds.append("sudo iptables -A INPUT -s " + config['GATEWAY_SERVER'] + " -j ACCEPT")
    cmds.append("sudo iptables -A FORWARD -j ACCEPT")
    cmds.append("sudo iptables -A OUTPUT -d " + config['GATEWAY_SERVER'] + " -j ACCEPT")

    # bring up ifb0
    cmds.append("sudo ip link set ifb0 up")

    # delete all old tc settings (default ceil = rate)
    cmds.append("sudo tc qdisc del dev " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc qdisc del dev " + config["EMU_INTERFACE"] + " ingress")
    cmds.append("sudo tc qdisc del dev ifb0 root")
    cmds.append("sudo tc filter del dev " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc filter del dev ifb0 root")
    cmds.append("sudo tc class del " + config["EMU_INTERFACE"] + " root")
    cmds.append("sudo tc class del ifb0 root")

    cmds.append("sudo tc qdisc add dev " + config["EMU_INTERFACE"] + " ingress")
    cmds.append(
        "sudo tc filter add dev " + config["EMU_INTERFACE"] + " parent ffff: protocol ip u32 match ip src " +
        config["EMU_PREFIX"] + "0/24 flowid 1:1 action mirred egress redirect dev ifb0")
    cmds.append("sudo tc qdisc add dev ifb0 root handle 2: htb default " + str(8))
    cmds.append("sudo tc class add dev ifb0 parent 2: classid 2:" + str(8) + " htb rate 100mbit")

    # setup "normal" qdiscs (outgoing)
    # delete all old tc settings (default ceil = rate)
    cmds.append("sudo tc qdisc add dev " + config["EMU_INTERFACE"] + " root handle 1: htb default " + str(7))
    cmds.append("sudo tc class add dev " + config["EMU_INTERFACE"] + " parent 1: classid 1:" + str(
        7) + " htb rate 100mbit")
    cmds.append("")

    return cmds
