import os
from . import static_connection, network_block

class StaticNetworkBlock(network_block.NetworkBlock):
    def __init__(self, blockDirectory, staticConnections, interval_size):
        absdir = os.path.abspath(blockDirectory)
        if not os.path.isdir(absdir):
            os.makedirs(absdir)
        # remove all (possibly) pre-existing files
        for f in os.listdir(absdir):
            os.remove(os.path.join(absdir, f))

        for staticConnection in staticConnections:
            self.createIntermediateFile(absdir, staticConnection, interval_size)
        super(StaticNetworkBlock, self).__init__(absdir)
        self.selectInterval(interval_size)

    def createIntermediateFile(self, outputFolder, staticConn, interval_size):
        content = ['start, delay, loss random, rate']
        content.append('{:f}\t{:f}\t{:f}\t{:f}'.format(0.0, staticConn.delay, staticConn.loss, staticConn.bandwidth))

        with open(os.path.join(outputFolder, str(staticConn.src) + '_' + str(staticConn.dst) + '_' + str(interval_size) + '.txt'), 'w') as ifFile:
            ifFile.write('\n'.join(content))