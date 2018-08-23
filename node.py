import copy

EMU_PREFIX = "192.168.0."
class Node:
    def __init__(self, id):
        self.id = id
        self.userCommandDict = {}
        self.commandDict = {}
        # file/folder-paths/destinations of results to be fetched after emulation concluded (remote_path, local_path)
        self.user_results = []
        self.app_results = []
        self.configFiles = []

    def scheduleUserCmd(self, time_point, command):
        if time_point >= 0 and not command.strip().endswith("&"):
            command += " &"   # do not keep exec-engine waiting at runtime

        if time_point not in self.userCommandDict:
            self.userCommandDict[time_point] = [command]
        else:
            self.userCommandDict[time_point].append(command)
        # add cmd to main command-dict
        self.scheduleCmd(time_point, command)

    def scheduleCmd(self, time_point, command):
        if time_point >= 0 and not command.strip().endswith("&"):
            command += " &"   # do not keep exec-engine waiting at runtime

        if time_point not in self.commandDict:
            self.commandDict[time_point] = [command]
        else:
            self.commandDict[time_point].append(command)

    def replaceCmdsAt(self, time_point, commandList):
        self.commandDict[time_point] = commandList

    def scheduleCmds(self, time_point, commandList):
        for cmd in commandList:
            self.scheduleCmd(time_point,cmd)

    def getId(self):
        return self.id

    def getEmuIP(self, config):
        return config['EMU_PREFIX'] + str(config['HOST_IP_START'] + self.id)

    def getMngIP(self, config):
        return config['MNG_PREFIX'] + str(config['HOST_IP_START'] + self.id)

    def getCommandDict(self):
        return self.commandDict

    def setCommandDict(self, cmdDict):
        self.commandDict = cmdDict

    def addUserResult(self, remote_path, localpath):
        self.user_results.append((remote_path, localpath))

    def addAppResult(self, remote_path, localpath):
        self.app_results.append((remote_path, localpath))

    def addConfigFile(self, remote_path, localpath):
        self.configFiles.append((remote_path, localpath))

    def resetApplicationGeneratedData(self):
        self.commandDict = copy.deepcopy(self.userCommandDict)  # keep user-gen commands
        self.app_results = []
        self.configFiles = []

    def __str__(self):
        output = ["Node nr: " + str(self.id)]
        output.append("<Scheduled commands>")
        for time in sorted(self.commandDict.keys()):
            output.append("\t" + str(time) + "\t" + str(self.commandDict[time]))
        output.append("</Scheduled commands>")
        output.append("<ConfigFiles to be distributed>")
        for result in self.configFiles:
            output.append("\t" + str(result))
        output.append("</ConfigFiles to be distributed>")
        output.append("<Results to be fetched>")
        for result in self.app_results + self.user_results:
            output.append("\t" + str(result))
        output.append("</Results to be fetched>")
        return '\n'.join(output)