
import os, pathlib
import subprocess
import time, signal
from subprocess import Popen, PIPE

class StartMiner:
    def __init__(self, log, workerName, miner, devIds, fans, memOCs, coreUCs):
        self.log = log
        self.proc = None
        self.subChilds = None
        curr = pathlib.Path(__file__).parent.absolute()
        minerFolder = "%s\\%s" % (curr, "miners")
        dirs = os.listdir(minerFolder)
        for folder in dirs:
            if folder.find(miner) == 0:
                self.Start("%s\\%s" % (minerFolder, folder), workerName, devIds, fans, memOCs, coreUCs)


    def Start(self, activefolder, workerName, devIds, fans, memOCs, coreUCs):
        exePath = activefolder + "\\miner.exe"
        #print ("ExePath: %s" % exePath)
        configPath = activefolder + "\\config.cfg"
        #print (configPath)
        parameters = open(configPath, 'r').read().replace("#core#", str(coreUCs)).replace("#mem#", str(memOCs)).replace("#fan#", str(fans)).replace("#dev#", str(devIds)).replace("#worker#", workerName)
        self.log.Debug(parameters)
        self.log.Debug("will start %s\\miner" % activefolder)
        self.proc = subprocess.Popen(["powershell", exePath, parameters], creationflags = subprocess.CREATE_NEW_CONSOLE)
        self.log.Debug("started miner with pid: %i" % self.proc.pid)
        time.sleep(1)
        self.GetMinerChildProcessID()

    def Stop(self):
        subprocess.call(['taskkill', '/F', '/T', '/PID',  str(self.proc.pid)])

    def GetMinerChildProcessID(self):
        self.directChilds = self.GetSubProcessIDs(self.proc.pid)
        self.log.Debug("directChilds: %s" % self.directChilds)
        self.subChilds = []
        for child in self.directChilds:
            subchild = self.GetSubProcessIDs(str(child))
            self.subChilds.append(self.GetSubProcessIDs(str(child)))
            self.log.Debug("subchild: %s" % subchild)

    def ProcessesChanged(self):
        childs = self.GetSubProcessIDs(self.proc.pid)
        if len(childs) != len(self.directChilds):
            return True

        subchilds = []
        for i in range(len(childs)):
            if childs[i] != self.directChilds[i]:
                return True
            subchilds.append(self.GetSubProcessIDs(childs[i]))

        if len(subchilds) != len(self.subChilds):
            return True

        for i in range(len(subchilds)):
            if subchilds[i] != self.subChilds[i]:
                return True

        return False

    

    def GetSubProcessIDs(self, pid):
        command = "Get-WmiObject Win32_Process | Select ProcessID, ParentProcessID"
        #print("PID command: \n%s" % command)
        process = Popen(["powershell", command], stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        
        if exit_code == 0 and err == None:
            lines = output.decode("utf-8").split("\r\n")
            res = []
            for line in lines:
                if line.find(str(pid)) >= 0:
                    arr = self.Strip(line)
                    if arr[1] == str(pid):
                        res.append(arr[0])
            return res
        else:
            self.log.Warning("could not get subprocesses: \"%s\"" % command)
            self.log.Debug("Code: %i:\n%s" %(exit_code, err))
            return None

    def Strip(self, txt):
        while txt.find("  ") >= 0:
            txt = txt.replace("  ", " ")
        res = txt.split(" ")
        newRes = []
        for item in res:
            if item != "":
                #print("adding item %s" % item.split(" ")[0])
                newRes.append(item)
        return newRes