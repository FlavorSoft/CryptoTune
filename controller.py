from req import MinerDataRequester
from startMiner import StartMiner
from gpu import GPU
import json, time, math, socket
from log import Log

miningSoftwareCooldown = 1
maxWaitForMiningSoftwareApi = 3
sleepBetweenTuningRuns = 1

class Controller:
    def __init__(self, miner, mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, marginInMH, coreUCs, memOCs, powerLimits):
        
        # give the worker a name to separate data on pool
        self.workerName = socket.gethostname().replace("-","").replace(".","").replace("_","")

        # initialize logging utils
        self.log = Log("DEBUG")

        # mining software
        self.ms = None

        # utility
        if mode < 0 or mode > 1:
            self.log.Warning("invalid optimization mode \"%i\" - will default to best efficiency" % mode)
            mode = 0
        self.modeText = "MOST EFFICIENCY"
        if mode == 1:
            self.modeText = "BEST SPEED"

        # save base hw settings
        self.devIds = devIds
        self.fanSpeeds = fanSpeeds

        # if no devices were specified, take all
        if devIds == None:
            devIds = range(64)

        # collect all GPUs connected and initialize
        self.gpus = []
        for i in devIds:
            # set default values if no enough values were specified
            if len(powerLimits) <= i:
                powerLimits.append(None)
            if len(memOCs) <= i:
                memOCs.append(0)
            if len(coreUCs) <= i:
                coreUCs.append(0)
            if len(fanSpeeds) <= i:
                self.fanSpeeds.append(self.fanSpeeds[0])
            gpu = GPU(self.log, i, mode, memOCs[i], coreUCs[i], steps, powerLimits[i], nbrOfShares, nbrOfDatapoints, marginInMH)
            if gpu.found:
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

        # initialize mining data requester - miner is not started yet, so we cannot request any data for now
        self.req = MinerDataRequester(self.log, miner, "127.0.0.1", 3333, "/stat")

        # first tune mem and core clocks until all GPUs are finished
        tuningDone = 0
        self.requiresRestart = True
        saveOldData = False
        while tuningDone < len(self.gpus):
            # test if running mining Software has crashed
            if self.ms is not None and self.ms.ProcessesChanged():
                self.log.Info("Mining Software seems to have crashed/changed")
                self.MiningSoftwareCrashed()

            if self.requiresRestart:
                self.ResetGPUs(saveOldData)
                self.ReStartMiningSoftware()

            saveOldData = True
            minerData = self.req.getData()
            tuningDone = self.OC(minerData)
            time.sleep(sleepBetweenTuningRuns)

        # as we are complete, print resultdata of each GPU
        self.log.Info("### TUNING COMPLETED FOR %i GPUS with Mode: \"%s\" ###" % (len(self.gpus), self.modeText))
        for gpu in self.gpus:
            plPerc = math.ceil(100.0 / int(gpu.powerReadings["default_power_limit"]["$"].split(".")[0]) * gpu.powerLimit)
            self.log.Info("GPU%i: Max Memory Overclock: %i\tMax Core UnderClock: %i\tMin Power Level: %iW (%i%%)" % (gpu.id, gpu.memOC, gpu.coreUC, gpu.powerLimit, plPerc))

    def ResetGPUs(self, saveOldData):
        for gpu in self.gpus:
            gpu.ResetData(saveOldData)

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
        if self.ms is not None:
            self.ms.Stop()
            time.sleep(miningSoftwareCooldown)
        
        # collect GPU OC/UC Data
        memOCs = ""
        coreUCs = ""
        fans = ""
        devs = ""
        for i in range(len(self.gpus)):
            devs += str(i) + " "
            memOCs += str(self.gpus[i].memOC) + " "
            coreUCs += str(self.gpus[i].coreUC) + " "
            fans += str(self.fanSpeeds[i]) + " "

        # initialize MiningSoftware and start
        self.ms = StartMiner(self.log, self.workerName, "gminer", devs, fans, memOCs, coreUCs)

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
        