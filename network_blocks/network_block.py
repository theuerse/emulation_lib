import os
from shutil import copyfile

class NetworkBlock:
    def __init__(self, blockDirectory):
        self.name = os.path.basename(blockDirectory)
        self.directory = os.path.abspath(blockDirectory)
        self.intervals = self.scanIntervals()
        self.nodes = [None] * self.numberOfNodes
        self.selectedInterval = None
        self.preprocessingSteps = []


    def scanIntervals(self):
        intervals = {}
        involved_nodes = set([])
        for file in os.listdir(self.directory):
            if not file.endswith('.txt'): continue # allow for the presence of files other than the intermediate-files

            parts = file.split(".")[0].split('_') # 0_1_100.txt
            involved_nodes.add(parts[0])
            involved_nodes.add(parts[1])
            if not parts[-1] in intervals:
                intervals[parts[-1]] = [file]
            else:
                intervals[parts[-1]].append(file)
        self.numberOfNodes = len(involved_nodes)
        return intervals


    def setNode(self, index, node):
        if index < 0 or index >= self.numberOfNodes:
            raise ValueError("index out of bounds, must be between 0 and " + str(self.numberOfNodes))
        self.nodes[index] = node


    def setNodes(self, node_list):
        if len(node_list) != self.numberOfNodes:
            raise ValueError("Given list must be of length " + str(self.numberOfNodes))
        self.nodes = node_list


    def getNodes(self):
        return self.nodes


    def selectInterval(self, interval):
        interval = str(interval)
        if interval in self.intervals.keys():
            self.selectedInterval = interval
        else:
            raise ValueError(str(interval) + " is no such interval to be found in " + self.directory)


    def isIntervalSelected(self):
        return (self.selectedInterval != None)


    def getIntermediateFiles(self):
        intermediate_files = []
        if len(self.intervals) > 0:
            for file in self.intervals[self.selectedInterval]:
                src_filepath = os.path.join(self.directory, file)
                parts = file.split('_')  # 0_1_100.txt

                # generate name containing the real node-ids
                parts[0] = str(self.nodes[int(parts[0])].getId())
                parts[1] = str(self.nodes[int(parts[1])].getId())
                dst_filename = '_'.join(parts)

                intermediate_files.append((dst_filename, src_filepath))
        else:
            for file in os.listdir(self.directory):
                parts = file.split('_')  # 0_1.txt
                src_filepath = os.path.join(self.directory, file)

                # generate name containing the real node-ids
                parts[0] = str(self.nodes[int(parts[0])].getId())
                parts[1] = str(self.nodes[int(parts[1])].getId())
                dst_filename = '_'.join(parts)

                intermediate_files.append((dst_filename, src_filepath))
        return intermediate_files


    def generateIntermediateFiles(self, intermediateFileDirectory):
        for if_tuple in self.getIntermediateFiles():  # tuples (dst_filename, src_filepath)
            outputFileName = os.path.join(intermediateFileDirectory, if_tuple[0])
            copyfile(if_tuple[1], outputFileName)
            for step in self.preprocessingSteps: # operate on copy of "master"-if e.g. stretch it to fill simtime
                step.run(self, outputFileName)


    def __str__(self):
        output = ["NetworkBlock: " + self.name]
        output.append("Directory: " + self.directory)
        output.append("Number of Nodes: " + str(self.numberOfNodes))

        nodeIds = ""
        for node in self.nodes:
            nodeIds  += str(node.getId()) + " "
        output.append("Nodes: " + nodeIds)

        output.append("\n")
        output.append("Available interval-sizes: ")
        for interval in self.intervals.keys():
            output.append("\t" + str(interval) + " " + str(self.intervals[interval]))
        output.append("Interval selected: " + str(self.isIntervalSelected()))
        output.append("Selected interval: " + str(self.selectedInterval))
        return '\n'.join(output)


    def addPreprocessingStep(self, procedure):
        if procedure not in self.preprocessingSteps:
            self.preprocessingSteps.append(procedure)


    def addPreprocessingSteps(self, procecureList):
        for procedure in procecureList:
            self.addPreprocessingStep(procedure)


    def getPreprocessingSteps(self):
        return self.preprocessingSteps