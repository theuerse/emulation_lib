from . import preprocessing_step

class CutOutPartOfFile(preprocessing_step.PreprocessingStep):
    def __init__(self, start, stop, includeFilesWithOnlyOneEntry):
        super(CutOutPartOfFile, self).__init__()
        self.start_second = start
        self.stop_second = stop
        self.includeFilesWithOnlyOneEntry = includeFilesWithOnlyOneEntry
        # intermediate files with only one entry indicate a static link
        # setup-only, no changes during runtime!


    def run(self, block, path):
        conditions = []
        newIfFileContent = []
        interval = float(block.selectedInterval)/1000 #seconds

        # read intermediate-file contents
        with open(path, mode="r") as ifFile:
            lines = ifFile.readlines()
            newIfFileContent.append(lines[0].rstrip()) # add header

            for line in lines[1:]:
                if len(line) > 0:
                    parts = line.split("\t")
                    time_index = float(parts[0])
                    if time_index < self.start_second:
                        continue  # skip all content happening before start_second
                    elif time_index > self.stop_second:
                        break   # stop collecting content after passing stop_second
                    conditions.append("\t".join(line.split("\t")[1:]).rstrip())

        # avoid needless duplication of single command in "setup-only"/static connection IFs
        if not self.includeFilesWithOnlyOneEntry and len(conditions) == 1:
            return

        lastTimeIndex = 0.0
        for condition in conditions:
            newIfFileContent.append('{:.6f}'.format(lastTimeIndex) + "\t" + condition)
            lastTimeIndex += interval

        # overwrite old file
        with open(path, mode='w') as ifFile:
            ifFile.write("\n".join(newIfFileContent)+"\n")
