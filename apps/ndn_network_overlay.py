import os
from .. import constants
from . import application
from igraph import *
import copy

# Begin of src based on node-parser.py from https://github.com/danposch/BPR-Scripts
class Link(object):
    def __init__(self, n1, n2):
        self.n1 = n1
        self.n2 = n2
        self.ip1 = ""
        self.ip2 = ""

    def __str__(self):
        return "Link(" + self.n1 + ", " + self.n2 + ")"


class Property(object):
    def __init__(self, client, server):
        self.client = client
        self.server = server
        self.ip_client = ""
        self.ip_server = ""

    def __str__(self):
        return "Property(" + str(self.client) + ", " + str(
            self.server) + ") or with IPs: Property(" + self.ip_client + ", " + self.ip_server + ")"


def parseNetwork(topology):
    link_list = []
    property_list = []

    print("Parsing Topology")
    topo_iter = iter(topology)
    for line in topo_iter:
        if line.startswith("#number of nodes"):
            # skip header and read number of nodes
            nodeIds = int( next(topo_iter))

        if line.startswith("#nodes setting"):
            line = next(topo_iter)
            while line[0] != '#':
                parts = line.rstrip('\n').split(',')

                if len(parts) >= 2:
                    link_list.append(Link(parts[0], parts[1]))
                else:
                    raise ValueError("node-setting of incorrect format: " + line)

                if line == topology[-1]:
                    break
                line = next(topo_iter)

        if line.startswith("#properties"):
            line = next(topo_iter)
            while (line[0] != '#'):
                tmp_str = line.rstrip('\n').split(',')

                if (len(tmp_str) != 2):
                    raise ValueError("property of incorrect format: " + line)

                # print Property(tmp_str[0],tmp_str[1]).client
                property_list.append(Property(int(tmp_str[0]), int(tmp_str[1])))

                if line == topology[-1]:
                    break
                line = next(topo_iter)


    print("Network parsed!\n")
    return (nodeIds, link_list, property_list)


# End of src based on node-parser.py from https://github.com/danposch/BPR-Scripts

def getNextFibHops(paths):
    cost_dict = {}
    for path in paths:
        nextHop = path[1]

        if nextHop in cost_dict.keys():
            if len(path) < len(cost_dict[nextHop]):
                cost_dict[nextHop] = path
        else:
            cost_dict[nextHop] = path

    return cost_dict.values()

#Credits: http://stackoverflow.com/questions/29314795/python-igraph-get-all-possible-paths-is-a-directed-graph
def find_all_paths(graph, start, end, mode = 'OUT', maxlen = None):
    def find_all_paths_aux(adjlist, start, end, path, maxlen = None):
        path = path + [start]
        if start == end:
            return [path]
        paths = []
        if maxlen is None or len(path) <= maxlen:
            for node in adjlist[start] - set(path):
                paths.extend(find_all_paths_aux(adjlist, node, end, path, maxlen))
        return paths
    adjlist = [set(graph.neighbors(node, mode = mode)) \
        for node in range(graph.vcount())]
    all_paths = []
    start = start if type(start) is list else [start]
    end = end if type(end) is list else [end]
    for s in start:
        for e in end:
            all_paths.extend(find_all_paths_aux(adjlist, s, e, [], maxlen))
    return all_paths


class NDN_NetworkOverlay(application.Application):
    def __init__(self, nodes, topology, paths = "shortest", forwarding_strategy = "/localhost/nfd/strategy/best-route"):
        self.nodes = nodes
        self.topology = topology
        self.paths = paths
        self.nodeIds, self.link_list, self.property_list = parseNetwork(topology)
        self.forwardingStrategy = forwarding_strategy

    def getNodeSpecificCommands(self, topology):
        nodeSpecificCommands = {}

        return nodeSpecificCommands

    def mapIpAddressesToNodes(self, config):

        # find IPs for node-ids
        for link in self.link_list:
            link.ip1 = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + int(link.n1))
            link.ip2 = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + int(link.n2))

        for prop in self.property_list:
            prop.ip_client = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + int(prop.client))
            prop.ip_server = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + int(prop.server))

    def generateRoutingCommands(self,config):
        # setup static routes before emulation begin

        # 1. we need a graph to calc the shortest / all paths
        g = Graph()
        g = g.as_directed()

        pi_list = []
        for node in self.nodes:
            pi_list.append(node.getId())

        for pi in self.nodes:
            g.add_vertex(pi.getId())

        for link in self.link_list:
            g.add_edges([(int(link.n1), int(link.n2)), (int(link.n2), int(link.n1))])


        for pi_idx, pi in enumerate(pi_list):
            for to_idx, to in enumerate(pi_list[pi_idx + 1:]):

                # print "Start calc for pi:" +str(pi)
                if self.paths == "shortest":
                    paths = g.get_all_shortest_paths(pi, to)
                elif self.paths == "all":
                    paths = find_all_paths(g, pi, to, maxlen=len(self.nodes))
                else:
                    raise ValueError("Invalid Path selection! Please choose \"all\" or \"shortest\"!")
                # print "found " + str(len(paths)) + " for pair (" + str(pi) + "," + str(to) + ")"

                # store reverse pahts for to -> pi
                reverse_paths = copy.deepcopy(paths)
                for path in reverse_paths:
                    path.reverse()

                # first calc and add fib entries from pi -> to
                paths = getNextFibHops(paths)

                # install next hop and costs
                for path in paths:
                    to_prefix = "/Node" + str(path[-1])
                    to_ip = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + path[1])

                    for node in self.nodes:
                        if node.getId() == pi:
                            node.scheduleCmd(constants.SETUP_TIME,"sudo nfdc face create udp://" + to_ip)
                            node.scheduleCmd(constants.SETUP_TIME,"sudo nfdc route add " + to_prefix + " udp://" + to_ip + " cost " + str(len(path) - 1))

                            # set forwarding strategy
                            node.scheduleCmd(constants.SETUP_TIME,
                                             "sudo nfdc strategy set prefix " + to_prefix + " strategy " + self.forwardingStrategy)
                            break


                # now calc and add fib entries from to -> pi
                reverse_paths = getNextFibHops(reverse_paths)

                # install next hop and costs
                for path in reverse_paths:
                    pi_prefix = "/Node" + str(path[-1])
                    pi_ip = config['EMU_PREFIX'] + str(config['HOST_IP_START'] + path[1])

                    for node in self.nodes:
                        if node.getId() == to:
                            node.scheduleCmd(constants.SETUP_TIME, "sudo nfdc face create udp://" + pi_ip)
                            node.scheduleCmd(constants.SETUP_TIME,
                                             "sudo nfdc route add " + pi_prefix + " udp://" + pi_ip + " cost " + str(
                                                 len(path) - 1))

                            # set forwarding strategy
                            node.scheduleCmd(constants.SETUP_TIME,
                                             "sudo nfdc strategy set prefix " + pi_prefix + " strategy " + self.forwardingStrategy)
                            break


    def generateCommands(self, config):
        self.mapIpAddressesToNodes(config)

        for node in self.nodes:
            # (re-)start NFD before emulation-begin
            node.scheduleCmd(constants.SETUP_TIME, "sudo nfd-stop")
            node.scheduleCmd(constants.SETUP_TIME, "sleep 5")
            node.scheduleCmd(constants.SETUP_TIME, "sudo nfd-start")
            node.scheduleCmd(constants.SETUP_TIME, "sleep 5")

            # stop NFD at emulation-end
            node.scheduleCmd(float(config["EMU_DURATION"]), "sudo killall nfd")

        self.generateRoutingCommands(config)

    def getServerClientGroups(self):
        groups = {}
        for property in self.property_list:
            server_node = self.nodes[property.server]
            client_node = self.nodes[property.client]

            if not server_node in groups:
                groups[server_node] = [client_node]
            else:
                groups[server_node].append(client_node)
        return groups