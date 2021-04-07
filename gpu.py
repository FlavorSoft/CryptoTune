
from subprocess import Popen, PIPE
import xmljson, json, platform
from lxml.etree import fromstring, tostring

wattSteps = 2

class GPU:
    def __init__(self, log, id, mode, memOC, coreUC, fanSpeed, steps, powerLimit, nbrOfShares, nbrOfDatapoints, marginInMH):
        self.log = log
        self.id = id
        self.found = False
        self.mode = mode
        self.fanSpeed = fanSpeed
        self.isWindows = self.IsWindowsOS()
        self.lastShareCount = 0

        # speed data via mining software
        self.currentSpeedData = []
        self.lastSpeedData = []
        # hw data of GPU via nvidia-smi
        self.currentData = []
        self.lastData = []
        
        self.margin = marginInMH
        
        # initialize runtime values
        self.maxAvg = 0
        self.maxMemClockFound = False
        self.minCoreClockFound = False
        self.minPowerLimitFound = False
        self.efficiency = 0

        self.memOC = memOC
        self.coreUC = coreUC
        self.steps = steps
        self.powerLimit = powerLimit
        self.nbrOfShares = nbrOfShares
        self.maxAvgSpeed = 0

        # if this is a unix environment, we need to setup fans and clocks now
        if not self.isWindows:
            self.unixInit()

        if nbrOfDatapoints is None:
            nbrOfDatapoints = 10
        self.nbrOfDatapoints = nbrOfDatapoints

        # tuning variables
        self.requiresRestart = False
        self.powerLimitChanged = False
        self.tuningRanThrough = False

        # initialy get HW data of device
        self.GetData()
        if self.powerLimit == None and self.found:
            self.SetPowerLevel(int(self.powerReadings["default_power_limit"]["$"].split(".")[0]))

    def unixInit(self):
        self.NVidiaSettings("fan", self.fanSpeed)
        self.NVidiaSettings("memOC", self.memOC)
        self.NVidiaSettings("coreUC", self.coreUC)

    def MiningSoftwareCrashed(self):
        # if the mining software crashed, the memory OC was too high
        self.maxMemClockFound = True
        self.changeMemOC(-1 * self.steps)

    def IsWindowsOS(self):
        if platform.system() == "Windows":
            return True
        else:
            return False

    # change memory overclock
    def changeMemOC(self, val):
        if self.isWindows:
            self.requiresRestart = True
        else:
            self.ResetData(True, False)
        self.memOC += val
        if not self.isWindows:
            self.NVidiaSettings("memOC", self.memOC)

    # change core underclock
    def changeCoreUC(self, val):
        if self.isWindows:
            self.requiresRestart = True
        else:
            self.ResetData(True, False)
        
        self.coreUC += val
        if not self.isWindows:
            self.NVidiaSettings("coreUC", self.coreUC)

    # change power limit
    def changePowerLimit(self, val):
        self.powerLimitChanged = True
        self.powerLimit += val
        self.SetPowerLevel(self.powerLimit)

    # get data of last run (before mining software restart)
    def getLastData(self):
        if len(self.currentData) > 0:
            return self.currentData[len(self.currentData) - 1]
        return None

    # change settings - returning False means, tuning is not yet completed
    def Tune(self, minerData):
        # if we are waiting for a restart, do not change anything
        if self.requiresRestart:
            return False
        
        # check if data is OK - will require a restart in the next run
        if not self.IsValidData(minerData):
            self.InvalidDataCreated()
            return False
        
        # save data as it is valid
        self.AddSpeedData(minerData.speed)

        # check if enough data has been created
        if not self.IsSufficientData(minerData):
            return False

        # from now on, we can assume that the tuning has taken effect
        self.tuningRanThrough = True

        # MEMORY OVERCLOCK NEEDS A RESTART IN MINING SOFTWARE
        # only change memory oc if no prior change is waiting to be applied
        # if no invalid shares were created and enough valid shares have been created, it is time to increase the overclock!
        if not self.maxMemClockFound and not self.powerLimitChanged:
            self.log.Debug("GPU%i: Tuning Memory OC" % (self.id))
            self.DoMemOC(minerData)
            return

        # CORE UNDERCLOCK NEEDS A RESTART IN MINING SOFTWARE
        # only change core undervolt if max memory oc was found and no prior change is waiting to be applied
        if self.maxMemClockFound and not self.minCoreClockFound and not self.powerLimitChanged:
            self.log.Debug("GPU%i: Tuning Core UC" % (self.id))
            self.DoCoreUC(minerData)
            return
        
        # POWER LIMIT CHANGE CAN BE APPLIED WITHOUT MINING SOFTWARE RESTART
        if self.maxMemClockFound and self.minCoreClockFound and not self.requiresRestart:
            if self.powerLimitChanged:
                self.ResetData(True, False)
            # if both clocks have not been changed and power level was not adjusted
            else:
                self.log.Debug("GPU%i: Tuning Power Limit" % (self.id))
                self.ReducePowerLimit(minerData)

        return self.maxMemClockFound and self.minCoreClockFound and self.minPowerLimitFound

    def InvalidDataCreated(self):
        self.log.Info("GPU%i created %i invalid shares, will reduce Memory OC")
        # check if gpu created invalid shares
        self.maxMemClockFound = True
        self.changeMemOC(-1 * self.steps)
        self.log.Info("new max memory OC found at %i" % self.memOC)
        return

    def IsValidData(self, minerData):
        if minerData.invalid > 0:
            self.log.Debug("GPU%i: created invalid shares" % self.id)
            return False
        return True

    # check if gpu created enough valid share
    def IsSufficientData(self, minerData):
        if minerData.accepted - self.lastShareCount < self.nbrOfShares or len(self.currentData) < self.nbrOfDatapoints:
            self.log.Debug("GPU%i: not created enough valid shares or datapoints yet shares (%i/%i) - datapoints (%i/%i)" % (self.id, minerData.accepted - self.lastShareCount, self.nbrOfShares, len(self.currentData), self.nbrOfDatapoints))
            return False
        return True

    def DoMemOC(self, minerData):
        self.changeMemOC(self.steps)
        self.log.Info("GPU%i: increased mem OC to %i" % (self.id, self.memOC))
        return

    def DoCoreUC(self, minerData):
        # compare speed with previous one - more = better!
        isSlower = self.IsSlower()
        if isSlower > 0:
            self.changeCoreUC(self.steps)
            self.minCoreClockFound = True
            self.log.Info("GPU%i: previous core clock was more efficient, found maximum core underclock: %i" % (self.id, self.coreUC))
            return
        
        if isSlower < 0:
            # otherwise, we are now faster -> better -> reduce core speed further
            self.changeCoreUC(-1*self.steps)
            self.log.Info("GPU%i: increased core UC to %i" % (self.id, self.coreUC))
            return

    def ReducePowerLimit(self, minerData):
        # do this depending on mode
        if self.mode == 0:
            # compare efficiency with previous one - more = better!
            isMoreEfficientNow = self.IsMoreEfficientNow()
            if isMoreEfficientNow < 0:
                self.changePowerLimit(wattSteps)
                self.minPowerLimitFound = True
                self.log.Info("GPU%i: previous power limit was more efficient, found minimum power limit: %i W" % (self.id, self.powerLimit))
                return
            
            if isMoreEfficientNow > 0:
                # otherwise, we are now more efficient -> better -> reduce core speed
                self.changePowerLimit(-1 * wattSteps)
                self.log.Info("GPU%i: reduced power limit to %i" % (self.id, self.powerLimit))
                return
        if self.mode == 1:
            isSlower = self.IsSlower()
            if isSlower > 0:
                self.changePowerLimit(wattSteps)
                self.minPowerLimitFound = True
                self.log.Info("GPU%i: previous power limit was faster, found minimum power level: %i" % (self.id, self.powerLimit))
                return
        
            if isSlower < 0:
                # otherwise, we are now faster -> better -> reduce power limit
                self.changePowerLimit(-1 * wattSteps)
                self.log.Info("GPU%i: reduced power limit to %i" % (self.id, self.powerLimit))
                return

    def AddSpeedData(self, speed):
        if speed > 0:
            self.currentSpeedData.append(speed)
            self.GetData()

    # should happen once per clock-tuning run
    def ResetData(self, saveOldData, crashed):
        self.log.Debug("GPU%i: data resettet" % self.id)
        if saveOldData and not crashed:
            self.lastData = self.currentData
            self.lastSpeedData = self.currentSpeedData
            self.SaveMaxAvgSpeed()
            self.lastShareCount = self.currentData[len(self.currentData)-1].accepted
        self.currentData = []
        self.currentSpeedData = []
        self.requiresRestart = False
        self.powerLimitChanged = False

    def SaveMaxAvgSpeed(self):
        currentAvgSpeed = self.GetAvgSpeed(self.currentSpeedData)
        if len(self.currentSpeedData) >= self.nbrOfDatapoints and currentAvgSpeed > self.maxAvgSpeed:
            self.maxAvgSpeed = currentAvgSpeed

    def GetCurrentEfficiency(self):
        return self.GetAvgSpeed(self.currentSpeedData) / self.GetAveragePowerDraw(self.currentData)

    def GetAvgEfficiency(self, listSpeed, listPower):
        if len(listSpeed) < self.nbrOfDatapoints: 
            return None

        return self.GetAvgSpeed(listSpeed) / self.GetAveragePowerDraw(listPower)

    def IsMoreEfficientNow(self):
        # if we did not have any data previously, but have now enough data, we assume we are faster now
        if len(self.lastData) < self.nbrOfDatapoints and len(self.currentData) > self.nbrOfDatapoints:
            return 1

        if len(self.currentData) < self.nbrOfDatapoints or len(self.lastData) < self.nbrOfDatapoints:
            self.log.Debug("GPU%i: not enough data to compare - current/needed (%i/%i)" % (self.id, len(self.currentData), self.nbrOfDatapoints))
            return 0
        
        old = self.GetAvgEfficiency(self.lastSpeedData, self.lastData)
        new = self.GetAvgEfficiency(self.currentSpeedData, self.currentData)
        
        self.log.Info("GPU%i: can now calculate Efficiency: %f vs. %f (old vs. new)" % (self.id, old, new))
        if new > old:
            return 1
        return -1

    def IsSlower(self):
        # if we did not have any data previously, but have now enough data, we assume we are faster now
        if self.maxAvgSpeed == 0 and len(self.currentSpeedData) > self.nbrOfDatapoints:
            return -1

        if len(self.currentSpeedData) < self.nbrOfDatapoints:
            self.log.Debug("GPU%i: not enough data to compare - current/needed (%i/%i)" % (self.id, len(self.currentSpeedData), self.nbrOfDatapoints))
            return 0

        currentAvg = self.GetAvgSpeed(self.currentSpeedData)
        self.log.Info("GPU%i: can now compare speeds: oldMax: %f vs. new (+margin): %f" % (self.id, self.maxAvgSpeed, currentAvg + self.margin))
        if currentAvg + self.margin < self.maxAvgSpeed:
            return 1
        return -1

    def GetAvgSpeed(self, lst):
        sum = 0.0
        for item in lst:
            sum += item / 1000000
        #print("avg speed: %f" % (sum / len(lst)))
        return sum / len(lst)

    def GetAveragePowerDraw(self, lst):
        sum = 0.0
        for data in lst:
            sum += float(data["power_readings"]["power_draw"]["$"].split(" ")[0])
        #print("AvgPowerDraw: %f" % (sum / len(lst)))
        return sum / len(lst)

    def GetData(self):
        try: 
            command = "nvidia-smi -i %i -x -q" % self.id
            # print(command)
            data = self.NSMI(command)
            if data == None:
                raise Exception("cannot get GPU#%i data" % self.id)

            gpu = data["nvidia_smi_log"]["gpu"]

            # save whole dataset
            self.currentData.append(gpu)

            # general data
            self.nbrOfCPUs = data["nvidia_smi_log"]["attached_gpus"]["$"]
            self.name = gpu["product_name"]["$"]
            self.utilization = gpu["utilization"]["gpu_util"]["$"]
            self.fanSpeed = gpu["fan_speed"]["$"]
            self.pState = gpu["performance_state"]["$"]

            # memory
            self.memoryTotal = gpu["fb_memory_usage"]["total"]["$"]
            self.memoryUsed = gpu["fb_memory_usage"]["used"]["$"]
            self.memoryFree = gpu["fb_memory_usage"]["free"]["$"]

            # ecc errors
            self.eccErrors = gpu["ecc_errors"]

            # temperatures
            self.temperatures = gpu["temperature"]
            #self.supportedTemperatures = gpu["supported_gpu_target_temp"]

            # power
            self.powerReadings = gpu["power_readings"]

            # clocks
            self.clocks = gpu["clocks"]
            self.maxClocks = gpu["max_clocks"]
            #self.supportedClocks = gpu["supported_clocks"]

            self.found = True
        except Exception as e:
            self.log.Warning("GPU could not be found or data is missing via nvidia-smi")
            self.log.Warning(str(e))

    def NVidiaSettings(self,name, value):
        command = None
        if name == "fan":
            command = "nvidia-settings -a [gpu:%i]/GPUFanControlState=1 -a [fan:0]/GPUTargetFanSpeed=%i" % (self.id, value)
        if name == "memOC":
            command = "nvidia-settings -a [gpu:%i]/GPUMemoryTransferRateOffset[3]=%i" % (self.id, value)
        if name == "coreUC":
            command = "nvidia-settings -a [gpu:%i]/GPUGraphicsClockOffset[2]=%i" % (self.id, value)
        
        if name == None:
            self.log.Error("invalid value for change in nvidia-settings")
            return False

        process = Popen(command.split(" "), stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            return True
        else:
            self.log.Warning("could not change nvidia-settings")
            self.log.Warning("Code: %i:\n%s" %(exit_code, output))
            return False

    def NSMI(self, command):
        process = Popen(command.split(" "), stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            xml = fromstring(output)
            jsonObj = xmljson.badgerfish.data(xml)
            return jsonObj
        else:
            print("Code: %i:\n%s" %(exit_code, err))
            return None

    def NSMISet(self, name, value):
        command = "nvidia-smi -i %i -%s %s" % (self.id, name, value)
        self.log.Debug("GPU%i: SMI Command: %s" % (self.id, command))
        process = Popen(command.split(" "), stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            return True
        else:
            self.log.Warning("GPU%i: could not execute nvidia-smi command: \"%s\"" % (self.id, command))
            #print("Code: %i:\n%s" %(exit_code, err))
            return False

    def SetPowerLevel(self, wattage):
        if wattage is None:
            wattage = int(self.powerReadings["default_power_limit"]["$"].split(".")[0])
        if self.NSMISet("pl", wattage):
            self.GetData()
            istWattage = int(self.powerReadings["power_limit"]["$"].split(".")[0])
            if istWattage == wattage:
                self.log.Info("GPU%i: power level set to %s W" % (self.id, wattage))
                return True
            else:
                self.log.Warning("GPU%i: could not set wattage. Command executed but: SOLL: \"%i\" vs. IST: \"%i\"" % (self.id, wattage, istWattage))
                return False
        self.log.Error("GPU%i: could not set wattage. Command execution failed" % self.id)
        return False

    def SetMinPowerLevel(self):
        return self.SetPowerLevel(self.powerReadings["min_power_limit"]["$"].split(".")[0])