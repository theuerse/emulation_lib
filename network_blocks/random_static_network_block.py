import os
import random
from igraph import *
from . import static_connection, network_block


class RandomStaticNetworkBlock(network_block.NetworkBlock):
    def __init__(self, blockDirectory, nodes, edge_probability, seed, bandwidth_limits, delay_limits, loss_limits, interval_size):
        absdir = os.path.abspath(blockDirectory)
        if not os.path.isdir(absdir):
            os.makedirs(absdir)
        # remove all (possibly) pre-existing files
        for f in os.listdir(absdir):
            os.remove(os.path.join(absdir, f))

        for staticConnection in self.generateRandomNetwork(absdir, nodes, edge_probability, seed, bandwidth_limits, delay_limits, loss_limits, interval_size):
            self.createIntermediateFile(absdir, staticConnection, interval_size)

        super(RandomStaticNetworkBlock, self).__init__(absdir)
        self.selectInterval(interval_size)


    def generateRandomNetwork(self, absdir, nodes, edge_probability, seed, bw_limits, delay_limits, loss_limits, interval_size):
        connections = []
        random.seed(seed)

        is_connected = False
        while not is_connected:
            g = Graph.Erdos_Renyi(n=nodes, p=edge_probability, directed=False, loops=False) #TODO: fully parameterize?
            is_connected = g.is_connected()

        for edge in g.es: # 0 <--> 1
            # 0 --> 1
            connections.append(static_connection.StaticConnection(edge.source, edge.target, random.uniform(bw_limits[0], bw_limits[1]),
                                                random.uniform(delay_limits[0], delay_limits[1]),
                                                random.uniform(loss_limits[0], loss_limits[1])))
            # 1 --> 0
            connections.append(static_connection.StaticConnection(edge.target, edge.source, random.uniform(bw_limits[0], bw_limits[1]),
                                                random.uniform(delay_limits[0], delay_limits[1]),
                                                random.uniform(loss_limits[0], loss_limits[1])))

        g.vs['label'] = range(0,nodes)
        #out = plot(g) # display image of generated graph
        #out.save(os.path.join(absdir, 'network.png'))
        return connections


    def createIntermediateFile(self, outputFolder, staticConn, interval_size):
        content = ['start, delay, loss random, rate']
        content.append('{:f}\t{:f}\t{:f}\t{:f}'.format(0.0, staticConn.delay, staticConn.loss, staticConn.bandwidth))

        with open(os.path.join(outputFolder, str(staticConn.src) + '_' + str(staticConn.dst) + '_' + str(interval_size) + '.txt'), 'w') as ifFile:
            ifFile.write('\n'.join(content))