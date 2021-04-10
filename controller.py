from req import MinerDataRequester
from startMiner import StartMiner
from gpu import GPU
import gpuSettingsLoader
import json, time, math, socket, hashlib
from log import Log
import platform, subprocess

miningSoftwareCooldown = 1
maxWaitForMiningSoftwareApi = 3
sleepBetweenTuningRuns = 1

class Controller:
    def __init__(self, miner, algo, mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, marginInMH, coreUCs, memOCs, powerLimits, powerCost, dollarPerMHash, loadPreset, skipMem, skipCore, skipPower):
   
        # give the worker a name to separate data on pool
        self.workerName = socket.gethostname().replace("-","").replace(".","").replace("_","")
        # anonymize workerName
        self.workerName = hashlib.md5(self.workerName.encode('utf-8')).hexdigest()
        self.algo = algo

        # initialize logging utils
        self.log = Log("DEBUG")

        # prepare unix systems
        if platform.system() != "Windows":
            subprocess.call(["chmod", "a+x", "./prepareUnix.sh"])
            subprocess.call(["./prepareUnix.sh"])

        # utility
        if mode < 0 or mode > 2:
            self.log.Warning("invalid optimization mode \"%i\" - will default to best efficiency" % mode)
            mode = 0
        self.modeText = "BEST EFFICIENCY"
        if mode == 1:
            self.modeText = "BEST SPEED"
        if mode == 2:
            self.modeText = "BEST PROFITABILITY"

        # save base hw settings
        self.devIds = devIds

        # if no devices were specified, take all
        if devIds == None:
            devIds = range(64)

        # collect all GPUs connected and initialize
        self.gpus = []
        self.overheatedGPUs = []
        ids = []
        for i in range(len(devIds)):
            # set default values if no enough values were specified
            if len(powerLimits) <= i:
                powerLimits.append(None)
            if len(memOCs) <= i:
                memOCs.append(0)
            if len(coreUCs) <= i:
                coreUCs.append(0)
            if len(fanSpeeds) <= i:
                fanSpeeds.append(70)

            # added warning for low fanSpeeds
            if fanSpeeds[i] < 30:
                self.log.Warning("GPU%i: low fanspeed (%i%%) configured - press ENTER to continue anyways" % (devIds[i], fanSpeeds[i]))
                input()

            gpu = GPU(self.log, devIds[i], mode, memOCs[i], coreUCs[i], fanSpeeds[i], steps, powerLimits[i], nbrOfShares, nbrOfDatapoints, marginInMH, powerCost, dollarPerMHash, skipMem, skipCore, skipPower)

            if gpu.found:
                # if preset for GPUs should be loaded, do this now
                if loadPreset:
                    # currently only ethash supported
                    self.ApplyPreset(gpu, self.algo)

                ids.append(devIds[i])
                self.gpus.append(gpu)
                # set starting power level
                self.gpus[i].SetPowerLimit(gpu.powerLimit)
                self.log.Info("found GPU%i - %s" % (i, self.gpus[i].name))
            else:
                fanSpeeds.remove(fanSpeeds[len(fanSpeeds) - 1])
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
        self.requiresRestart = False
        saveOldData = False
        self.ResetGPUs(False, False)
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

            # if all GPUs are finished with tuning, or software crashed, restart
            if (self.requiresRestart and self.GPUsFinishedTuning()) or crashed:
                self.ResetGPUs(saveOldData, crashed)
                self.RemoveOverheatingGPUs()
                self.ReStartMiningSoftware()

            elif self.requiresRestart:
                self.log.Debug("restart pending but not all GPUs are finished with their tuning")

            saveOldData = True
            minerData = self.req.getData()
            if minerData == None:
                self.log.Warning("Received Mining Data could not be read, wait and skip")
                time.sleep(1)
                continue
    
            # tune GPUs
            tuningDone = self.OC(minerData)

            # wait some time between runs
            time.sleep(sleepBetweenTuningRuns)

        # as we are complete, print resultdata of each GPU
        self.log.Info("### TUNING COMPLETED FOR %i GPUS with Mode: \"%s\" ###" % (len(self.gpus), self.modeText))
        for gpu in self.gpus:
            plPerc = math.ceil(100.0 / gpu.defaultPowerLimit * gpu.powerLimit)
            self.log.Info("GPU%i: Max Memory Overclock: %i\tMax Core UnderClock: %i\tMin Power Limit: %iW (%i%%)\tFan: %i%%" % (gpu.id, gpu.memOC, gpu.coreUC, gpu.powerLimit, plPerc, gpu.fanSpeed))
        
        for gpu in self.overheatedGPUs:
            plPerc = math.ceil(100.0 / gpu.defaultPowerLimit * gpu.powerLimit)
            self.log.Info("!OVERHEATED! GPU%i: Memory Overclock: %i\tCore UnderClock: %i\tPower Limit: %iW (%i%%)\tFan: %i%%" % (gpu.id, gpu.memOC, gpu.coreUC, gpu.powerLimit, plPerc, gpu.fanSpeed))

        # stop mining if no GPU is left
        if len(self.gpus) == 0:
            self.ms.Stop()

    def ApplyPreset(self, gpu, algo):
        settings = gpuSettingsLoader.GetSettings(gpu.name)
        if settings is not None and algo in settings:
            self.log.Info("GPU%i: Presets loaded" % (gpu.id))
            gpu.memOC = settings[algo]["memOC"]
            gpu.coreUC = settings[algo]["coreUC"]
            gpu.fanSpeed = settings[algo]["fan"]
            gpu.powerLimit = settings[algo]["powerLimit"]
        else:
            self.log.Warning("GPU%i: could not load Presets for algorithm \"%s\", will apply defaults" % (gpu.id, algo))

    def RemoveOverheatingGPUs(self):
        for gpu in self.gpus:
            if gpu.Overheating():
                self.log.Warning("GPU%i is overheating - removing it from mining process for safety reasons" % gpu.id)
                self.gpus.remove(gpu)
                self.overheatedGPUs.append(gpu)

    def GPUsFinishedTuning(self):
        finishedTuning = True
        for gpu in self.gpus:
            if not gpu.tuningDone:
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
        self.ms.Start(self.algo, memOCs, coreUCs)

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
        