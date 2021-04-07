from req import MinerDataRequester
from startMiner import StartMiner
from gpu import GPU
import json, time, math, socket, hashlib
from log import Log
import platform, subprocess

miningSoftwareCooldown = 1
maxWaitForMiningSoftwareApi = 3
sleepBetweenTuningRuns = 1

class Controller:
    def __init__(self, miner, mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, marginInMH, coreUCs, memOCs, powerLimits):
   
        # give the worker a name to separate data on pool
        self.workerName = socket.gethostname().replace("-","").replace(".","").replace("_","")
        # anonymize workerName
        self.workerName = hashlib.md5(self.workerName.encode('utf-8')).hexdigest()

        # initialize logging utils
        self.log = Log("DEBUG")

        # prepare unix systems
        if platform.system() != "Windows":
            subprocess.call(['./prepareUnix.sh'])

        # utility
        if mode < 0 or mode > 1:
            self.log.Warning("invalid optimization mode \"%i\" - will default to best efficiency" % mode)
            mode = 0
        self.modeText = "MOST EFFICIENCY"
        if mode == 1:
            self.modeText = "BEST SPEED"

        # save base hw settings
        self.devIds = devIds

        # if no devices were specified, take all
        if devIds == None:
            devIds = range(64)

        # collect all GPUs connected and initialize
        self.gpus = []
        ids = []
        for i in devIds:
            # set default values if no enough values were specified
            if len(powerLimits) <= i:
                powerLimits.append(None)
            if len(memOCs) <= i:
                memOCs.append(0)
            if len(coreUCs) <= i:
                coreUCs.append(0)
            if len(fanSpeeds) <= i:
                fanSpeeds.append(70)
            gpu = GPU(self.log, i, mode, memOCs[i], coreUCs[i], fanSpeeds[i], steps, powerLimits[i], nbrOfShares, nbrOfDatapoints, marginInMH)
            if gpu.found:
                ids.append(i)
                self.gpus.append(gpu)
                # set starting power level
                self.gpus[i].SetPowerLevel(powerLimits[i])
                self.log.Info("found GPU%i - %s" % (i, self.gpus[i].name))
            else:
                self.log.Warning("could not find GPU%i - will work with the found onces" % i)
                break


        self.log.Info("initialized %i GPUs" % len(self.gpus))

        # if we could not find any GPU, we will exit
        if len(self.gpus) == 0:
            self.log.Error("could not find any GPUs with given IDs %s - cannot tune clocks and will exit now" % devIds)
            exit(1)

        # initialize mining software starter
        self.ms = StartMiner(self.log, self.workerName, miner, ids, fanSpeeds)

        # initialize mining data requester - miner is not started yet, so we cannot request any data for now
        self.req = MinerDataRequester(self.log, miner, self.ms)

        # first tune mem and core clocks until all GPUs are finished
        tuningDone = 0
        self.requiresRestart = True
        saveOldData = False
        while tuningDone < len(self.gpus):
            # test if running mining Software has crashed
            crashed = False
            if self.ms.isRunning and self.ms.ProcessesChanged():
                self.log.Info("Mining Software seems to have crashed/changed")
                self.MiningSoftwareCrashed()
                crashed = True

            # start mining software if it is not running
            if not self.ms.isRunning:
                self.ReStartMiningSoftware()

            elif (self.requiresRestart and self.GPUsFinishedTuning()) or crashed:
                self.ResetGPUs(saveOldData, crashed)
                self.ReStartMiningSoftware()

            elif self.requiresRestart:
                self.log.Debug("restart pending but not all GPUs are finished with their tuning")

            saveOldData = True
            minerData = self.req.getData()
            tuningDone = self.OC(minerData)
            time.sleep(sleepBetweenTuningRuns)

        # as we are complete, print resultdata of each GPU
        self.log.Info("### TUNING COMPLETED FOR %i GPUS with Mode: \"%s\" ###" % (len(self.gpus), self.modeText))
        for gpu in self.gpus:
            plPerc = math.ceil(100.0 / int(gpu.powerReadings["default_power_limit"]["$"].split(".")[0]) * gpu.powerLimit)
            self.log.Info("GPU%i: Max Memory Overclock: %i\tMax Core UnderClock: %i\tMin Power Level: %iW (%i%%)" % (gpu.id, gpu.memOC, gpu.coreUC, gpu.powerLimit, plPerc))

    def GPUsFinishedTuning(self):
        finishedTuning = True
        for gpu in self.gpus:
            if not gpu.tuningRanThrough:
                finishedTuning = False
        return finishedTuning

    def ResetGPUs(self, saveOldData, crashed):
        for gpu in self.gpus:
            gpu.ResetData(saveOldData, crashed)

    def MiningSoftwareCrashed(self):
        for gpu in self.gpus:
            gpu.MiningSoftwareCrashed()
        
        # kill old process as it may have "self-repaired"
        self.requiresRestart = True

    def OC(self, minerData):
        # execute GPU clock-changes (require mining restart) and see if they are done
        clockingDone = 0
        if minerData == None:
            self.log.Warning("Received Mining Data could not be read, wait and skip")
            time.sleep(1)
            return 0

        self.requiresRestart = False
        for i in range(len(self.gpus)):
            gpu = self.gpus[i]
            if gpu.Tune(minerData[i]):
                clockingDone += 1
            if gpu.requiresRestart:
                self.requiresRestart = True
        
        self.log.Debug("clocktuning finished for %i/%i GPUs" % (clockingDone, len(self.gpus)))
        return clockingDone >= len(self.gpus)

    def ReStartMiningSoftware(self):
        # stop miner if it was already running
        if self.ms is not None and self.ms.isRunning:
            self.ms.Stop()
            time.sleep(miningSoftwareCooldown)
        
        # collect GPU OC/UC Data
        memOCs = ""
        coreUCs = ""
        for i in range(len(self.gpus)):
            memOCs += str(self.gpus[i].memOC) + " "
            coreUCs += str(self.gpus[i].coreUC) + " "

        # start MiningSoftware with gatheres settings
        self.ms.Start(memOCs, coreUCs)

        # wait for the first API request to answer correctly
        res = None
        waited = 0
        while res is None:
            time.sleep(1)
            waited += 1
            res = self.req.getData()
            if waited > maxWaitForMiningSoftwareApi:
                self.log.Error("could not connect to mining software API after %is via path: \t%s" % (maxWaitForMiningSoftwareApi, self.req.path))
                return False

        # mining software was started and API returned some data
        self.log.Debug("mining software started and API answers correctly")
        return True
        