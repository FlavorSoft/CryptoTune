
from subprocess import Popen, PIPE
from nvidiaUtil import NVTool
import xmljson, json, platform
from calc import Calculator

# TO DO - find better way to identify if change in wattage had an effect
wattSteps = 2

class GPU:
    def __init__(self, log, id, mode, memOC, coreUC, fanSpeed, steps, powerLimit, nbrOfShares, nbrOfDatapoints, marginInMH, powerCost, dollarPerMHash):
        # basics
        self.id = id
        self.log = log
        self.existing = False
        self.calc = Calculator(marginInMH, powerCost, dollarPerMHash)
        self.nvTool = NVTool(self.log, self.id)

        # overall Tuning Variables
        self.maxMemClockFound = False
        self.minCoreClockFound = False
        self.minPowerLimitFound = False

        # HW settings
        self.fanSpeed = fanSpeed
        self.memOC = memOC
        self.coreUC = coreUC
        self.powerLimit = powerLimit

        # tuning variables
        self.mode = mode
        self.steps = steps
        self.nbrOfShares = nbrOfShares
        self.margin = marginInMH
        self.nbrOfDatapoints = nbrOfDatapoints
        
        ## DATA TO CALCULATE ON ##
        # speed data via mining software
        self.currentMinerData = []
        self.lastMinerData = []
        self.overheatingThreshold = 5
        self.thermalLimitReached = 0

        # hw data of GPU via nvidia-smi
        self.currentHWData = []
        self.lastHWData = []

        ## HELPER VARIABLES ##
        self.dataSummary = []
        self.maxSpeed = 0.0
        self.defaultPowerLimit = 0.0
        self.tuningTries = 0

        ## TUNING PROCESS VARIABLES
        self.requiresRestart = False
        self.tuningDone = False

        self.found = self.Initialize()

    def Initialize(self):
        # initialy get HW data of device
        self.GetData()
        if len(self.currentHWData) > 0:
            self.defaultPowerLimit = int(self.currentHWData[len(self.currentHWData) -1]["power_readings"]["default_power_limit"]["$"].split(".")[0])
            # if no powerLimit was provided, get the default limit
            if self.powerLimit == None:
                self.powerLimit = self.defaultPowerLimit
            self.SetPowerLimit(self.powerLimit)

            # if this is a unix environment, we need to setup fans and clocks now
            if not self.IsWindowsOS():
                self.unixInit()
            return True
        return False

    def unixInit(self):
        self.nvTool.NVidiaSettings("fan", self.fanSpeed)
        self.nvTool.NVidiaSettings("memOC", self.memOC)
        self.nvTool.NVidiaSettings("coreUC", self.coreUC)

    # if the mining software crashed, the memory OC was too high
    def MiningSoftwareCrashed(self):
        self.maxMemClockFound = True
        self.changeMemOC(-1 * self.steps)

    # check if running under windows
    def IsWindowsOS(self):
        return platform.system() == "Windows"

    # change memory overclock
    def changeMemOC(self, val):
        self.memOC += val
        if self.IsWindowsOS():
            self.requiresRestart = True
        else:
            self.nvTool.NVidiaSettings("memOC", self.memOC)

    # change core underclock
    def changeCoreUC(self, val):
        self.coreUC += val
        if self.IsWindowsOS():
            self.requiresRestart = True
        else:
            self.nvTool.NVidiaSettings("coreUC", self.coreUC)

    # change power limit
    def changePowerLimit(self, val):
        self.powerLimitChanged = True
        self.powerLimit += val
        self.SetPowerLimit(self.powerLimit)

        # reset data as power limit does not need reboot
        self.ResetData(True, False)

    # change settings - returning False means, tuning is not yet completed
    def Tune(self, minerData):
        # save how often we have tried tuning
        self.tuningTries += 1
        # first refresh Data
        self.GetData()
        # check if we are currently thermal-throttled - can always happen, therefore we do it at the start
        if self.ThermalThrottled() and not self.tuningDone and self.tuningTries >= self.nbrOfDatapoints:
            self.ThermalThrottlingDetected()
            return False

        # if we are waiting for a restart, do not change anything
        if self.requiresRestart:
            return False
        
        # check if data is OK - and we are not thermal-throttling will require a restart in the next run
        if not self.IsValidData(minerData):
            self.InvalidDataCreated()
            return False 

        # save data as it is valid
        self.AddData(minerData)

        # check if enough data has been created
        if not self.IsSufficientData(minerData):
            return False

        # MEMORY OVERCLOCK NEEDS A RESTART IN MINING SOFTWARE
        # only change memory oc if no prior change is waiting to be applied
        # if no invalid shares were created and enough valid shares have been created, it is time to increase the overclock!
        if not self.maxMemClockFound and not self.tuningDone:
            self.log.Debug("GPU%i: Tuning Memory OC" % (self.id))
            self.DoMemOC()
            return

        # CORE UNDERCLOCK NEEDS A RESTART IN MINING SOFTWARE
        # only change core undervolt if max memory oc was found and no prior change is waiting to be applied
        if self.maxMemClockFound and not self.minCoreClockFound and not self.tuningDone:
            self.log.Debug("GPU%i: Tuning Core UC" % (self.id))
            self.DoCoreUC()
            return
        
        # POWER LIMIT CHANGE CAN BE APPLIED WITHOUT MINING SOFTWARE RESTART
        if self.maxMemClockFound and self.minCoreClockFound and not self.requiresRestart and not self.tuningDone:
            self.log.Debug("GPU%i: Tuning Power Limit" % (self.id))
            self.ReducePowerLimit()
            return

        return self.maxMemClockFound and self.minCoreClockFound and self.minPowerLimitFound

    ### INVALID SHARE HANDLING ###
    def InvalidDataCreated(self):
        self.log.Info("GPU%i: detected invalid shares, will reduce Memory OC" % self.id)
        self.MaxMemLimitFound()

    def ThermalThrottlingDetected(self):
        self.log.Info("GPU%i: Thermal Throttling detected - Memory OC was too high" % self.id)
        self.thermalLimitReached += 1
        self.MaxMemLimitFound()
        self.tuningDone = True
    
    def Overheating(self):
        return self.thermalLimitReached >= self.overheatingThreshold

    def MaxMemLimitFound(self):
        self.maxMemClockFound = True
        self.changeMemOC(-1 * self.steps)
        self.log.Info("GPU%i: new max memory OC found at %i" % (self.id, self.memOC))

    # check if GPU created invalid shares
    def IsValidData(self, minerData):
        if minerData.invalid > 0:
            self.log.Debug("GPU%i: created invalid shares" % self.id)
            return False
        return True

    ### CHECK IF GPU IS READY FOR NEXT SETTINGS ###
    def IsSufficientData(self, minerData):
        if minerData.accepted == 0:
            self.lastShareCount = 0
        if minerData.accepted - self.lastShareCount < self.nbrOfShares or len(self.currentHWData) < self.nbrOfDatapoints:
            self.log.Debug("GPU%i: not created enough valid shares or datapoints yet shares (%i/%i) - datapoints (%i/%i)" % (self.id, minerData.accepted - self.lastShareCount, self.nbrOfShares, len(self.currentHWData), self.nbrOfDatapoints))
            return False
        return True

    # MEMORY OC LOGIC#
    def DoMemOC(self):
        self.tuningDone = True
        self.changeMemOC(self.steps)
        self.log.Info("GPU%i: increased mem OC to %i" % (self.id, self.memOC))
        return

    # CORE UC LOGIC #
    def DoCoreUC(self):
        self.tuningDone = True
        if self.IsSlower():
            self.changeCoreUC(self.steps)
            self.minCoreClockFound = True
            self.log.Info("GPU%i: previous core clock was more efficient, found maximum core underclock: %i" % (self.id, self.coreUC))
        else:
            # otherwise, we are now faster -> better -> reduce core speed further
            self.changeCoreUC(-1*self.steps)
            self.log.Info("GPU%i: increased core UC to %i" % (self.id, self.coreUC))

    # POWER LIMIT REDUCTION LOGIC #
    def ReducePowerLimit(self):
        self.tuningDone = True
        # EFFICIENCY
        if self.mode == 0:
            if self.IsMoreEfficientNow():
                self.changePowerLimit(wattSteps)
                self.minPowerLimitFound = True
                self.log.Info("GPU%i: previous power limit was more efficient, found minimum power limit: %i W" % (self.id, self.powerLimit))            
            else:
                # otherwise, we are now more efficient -> better -> reduce core speed
                self.changePowerLimit(-1 * wattSteps)
                self.log.Info("GPU%i: reduced power limit to %i" % (self.id, self.powerLimit))
        
        # SPEED
        if self.mode == 1:
            if self.IsSlower():
                self.changePowerLimit(wattSteps)
                self.minPowerLimitFound = True
                self.log.Info("GPU%i: previous power limit was faster, found minimum power level: %i" % (self.id, self.powerLimit))
            else:
                # otherwise, we are still fast enough
                self.changePowerLimit(-1 * wattSteps)
                self.log.Info("GPU%i: reduced power limit to %i" % (self.id, self.powerLimit))

        # PROFITABILITY
        if self.mode == 2:
            if not self.IsMoreProfitable():
                self.changePowerLimit(wattSteps)
                self.minPowerLimitFound = True
                self.log.Info("GPU%i: previous power limit was more profitable, found minimum power level: %i" % (self.id, self.powerLimit))
            else:
                # otherwise, we are now more profitable -> better -> reduce power limit
                self.changePowerLimit(-1 * wattSteps)
                self.log.Info("GPU%i: reduced power limit to %i" % (self.id, self.powerLimit))

    def IsMoreProfitable(self):
        old = self.calc.Profitability(self.lastMinerData, self.lastHWData)
        new = self.calc.Profitability(self.currentMinerData, self.currentHWData)
        self.log.Debug("old vs. new: %.2f vs. %.2f" % (old, new))
        if new > old:
            return True
        return False

    def AddData(self, minerData):
        if minerData.speed > 0:
            self.currentMinerData.append(minerData)

    # should happen once per clock-tuning run
    def ResetData(self, saveOldData, crashed):
        self.log.Debug("GPU%i: data reset" % self.id)
        if saveOldData and not crashed:
            self.lastHWData = self.currentHWData
            self.lastMinerData = self.currentMinerData
            self.SaveMaxAvgSpeed()
        self.currentHWData = []
        self.currentMinerData = []
        self.requiresRestart = False
        self.powerLimitChanged = False
        self.tuningDone = False
        self.tuningTries = 0

    def SaveMaxAvgSpeed(self):
        speed = self.calc.Speed(self.lastMinerData)
        if speed > self.maxSpeed:
            self.maxSpeed = speed

   
    def IsMoreEfficientNow(self):
        old = self.calc.Efficiency(self.lastMinerData, self.lastHWData)
        new = self.calc.Efficiency(self.currentMinerData, self.lastHWData)
        self.log.Info("GPU%i: can now calculate Efficiency: %f vs. %f (old vs. new)" % (self.id, old, new))
        return new > old

    def IsSlower(self):
        new = self.calc.Speed(self.currentMinerData)
        self.log.Info("GPU%i: can now compare speeds: oldMax: %f vs. new (+margin): %f" % (self.id, self.maxSpeed, new + self.margin))
        return new + self.margin < self.maxSpeed

    def GetData(self):
        try: 
            command = "nvidia-smi -i %i -x -q" % self.id
            data = self.nvTool.NSMI(command)
            if data == None:
                raise Exception("cannot get GPU#%i data" % self.id)

            gpu = data["nvidia_smi_log"]["gpu"]

            # save whole dataset
            self.currentHWData.append(gpu)

            # general data
            self.nbrOfCPUs = int(data["nvidia_smi_log"]["attached_gpus"]["$"])
            self.name = gpu["product_name"]["$"]

            self.found = True
        except Exception as e:
            self.log.Warning("GPU could not be found or data is missing via nvidia-smi")
            self.log.Warning(str(e))

    # change power limit of GPU
    def SetPowerLimit(self, wattage):
        if self.nvTool.NSMISet("pl", wattage):
            self.GetData()
            istWattage = int(self.currentHWData[len(self.currentHWData) - 1]["power_readings"]["power_limit"]["$"].split(".")[0])
            if istWattage == wattage:
                self.log.Info("GPU%i: power level set to %s W" % (self.id, wattage))
                return True
            else:
                self.log.Warning("GPU%i: could not set wattage. Command executed but: SOLL: \"%i\" vs. IST: \"%i\"" % (self.id, wattage, istWattage))
                return False
        self.log.Error("GPU%i: could not set wattage. Command execution failed" % self.id)
        return False

    # check if GPU is thermaly limited
    def ThermalThrottled(self):
        # check if the keyword "not" was found in the thermal throttle result
        return self.currentHWData[len(self.currentHWData) - 1]["clocks_throttle_reasons"]["clocks_throttle_reason_sw_thermal_slowdown"]["$"].find("Not") < 0 or \
        self.currentHWData[len(self.currentHWData) - 1]["clocks_throttle_reasons"]["clocks_throttle_reason_hw_thermal_slowdown"]["$"].find("Not") < 0