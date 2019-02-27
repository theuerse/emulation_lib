from . import preprocessing_step

class RepeatIntermedFileUntil(preprocessing_step.PreprocessingStep):
    def __init__(self,second, includeFilesWithOnlyOneEntry):
        super(RepeatIntermedFileUntil, self).__init__()
        self.stop_second = second
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

            if len(lines) == 1: # ignore empty files (only header)
                return

            newIfFileContent.append(lines[0].rstrip()) # add header

            for line in lines[1:]:
                if len(line) > 0:
                    conditions.append("\t".join(line.split("\t")[1:]).rstrip())

        # avoid needless duplication of single command in "setup-only"/static connection IFs
        if not self.includeFilesWithOnlyOneEntry and len(conditions) == 1:
            return

        lastTimeIndex = 0.0
        idx = 0
        while lastTimeIndex <= self.stop_second:
            newIfFileContent.append('{:.6f}'.format(lastTimeIndex) + "\t" + conditions[idx])
            lastTimeIndex += interval
            idx = (idx + 1) % len(conditions)

        # overwrite old file
        with open(path, mode='w') as ifFile:
            ifFile.write("\n".join(newIfFileContent)+"\n")
