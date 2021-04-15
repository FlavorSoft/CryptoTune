from subprocess import Popen, PIPE
import xmljson
import lxml.etree

class NVTool:
    def __init__(self, log, gpuId):
        self.log = log
        self.gpuId = gpuId
    
    def NVidiaSettings(self, name, value):
        command = None
        if name == "fan":
            command = "nvidia-settings -a [gpu:%i]/GPUFanControlState=1 -a [fan:0]/GPUTargetFanSpeed=%i -a [fan:1]/GPUTargetFanSpeed=%i -a [fan:2]/GPUTargetFanSpeed=%i" % (self.gpuId, value, value ,value)
        if name == "memOC":
            command = "nvidia-settings -a [gpu:%i]/GPUMemoryTransferRateOffset[3]=%i" % (self.gpuId, value)
        if name == "coreUC":
            command = "nvidia-settings -a [gpu:%i]/GPUGraphicsClockOffset[3]=%i" % (self.gpuId, value)
        
        if command == None:
            self.log.Error("invalid value for change in nvidia-settings")
            return False

        self.log.Debug(command)
        process = Popen(command.split(" "), stdout=PIPE)
        output = process.communicate()
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
        if exit_code == 0 or exit_code == 6:
            xml = lxml.etree.fromstring(output)
            jsonObj = xmljson.badgerfish.data(xml)
            return jsonObj
        else:
            self.log.Debug("Error on executing command \"%s\"" % command)
            self.log.Debug("Code: %i:\n%s" %(exit_code, err))
            return None

    def NSMISet(self, name, value):
        command = "nvidia-smi -i %i -%s %s" % (self.gpuId, name, value)
        self.log.Debug("GPU%i: SMI Command: %s" % (self.gpuId, command))
        process = Popen(command.split(" "), stdout=PIPE)
        (output, err) = process.communicate()
        exit_code = process.wait()
        if exit_code == 0:
            return True
        else:
            self.log.Warning("GPU%i: could not execute nvidia-smi command: \"%s\"" % (self.gpuId, command))
            self.log.Warning("GPU%i: Code %i - %s" %(self.gpuId, exit_code, err))
            return False