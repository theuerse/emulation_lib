from . import preprocessing_step
import os

class SetConstantValueForColumn(preprocessing_step.PreprocessingStep):
    def __init__(self,filePrefix,columnIndex,value):
        super(SetConstantValueForColumn, self).__init__()
        self.filePrefix = filePrefix
        self.columnIndex = columnIndex
        self.value = value


    def run(self, block, path):
        # skip all files without matching prefix
        if not os.path.basename(path).startswith(self.filePrefix):
            return

        newIfFileContent = []

        # read intermediate-file contents
        with open(path, mode="r") as ifFile:
            lines = ifFile.readlines()
            newIfFileContent.append(lines[0].rstrip()) # add header

            for line in lines[1:]:
                if len(line) > 0:
                    parts = line.rstrip().split("\t")
                    parts[self.columnIndex] = str(self.value)
                    newIfFileContent.append("\t".join(parts))

        # overwrite old file
        with open(path, mode='w') as ifFile:
            ifFile.write("\n".join(newIfFileContent)+"\n")

