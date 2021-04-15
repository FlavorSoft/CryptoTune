from os import path
import json

def GetSettings(deviceName):
    arr = deviceName.split(" ")
    if len(arr) < 3:
        return None

    # cut "NVIDIA" as it's not necessary - on UNIX it would be "GeForce RTX 3060 Ti" only
    if len(arr) == 4 and arr[0] == "NVIDIA":
        arr = arr[1:]

    # build config name
    configName = ("%s %s %s.json" % (arr[0], arr[1], arr[2]))
    configFile = path.join("gpuDB", configName)
    if path.isfile(configFile):
        f = open(configFile, "r")
        return json.loads(f.read())

    return None