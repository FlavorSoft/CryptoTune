from req import MinerDataRequester
from startMiner import StartMiner
from gpu import GPU
import json, time, sys, getopt
from controller import Controller 


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"a:h:t:d:f:s:x:y:o:c:m:p:e:i:w",["algo=", "mode=", "devices=", "fans=", "steps=", "shares=", "datapoints=", "offset=", "coreUC=", "memOC=", "powerLimit=", "powerCost=", "dollarPerMHash=", "loadPreset", "miner=", "skipMem", "skipCore", "skipPower", "watchdog"])
    except getopt.GetoptError as e:
        print(str(e))
        print('run.py --algo <ethash> --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits> --miner <mining software>')
        sys.exit(2)

    # by default, gminer is selected
    miner = "gminer"

    # defaults for GPUs
    algo = "ethash"
    mode = 0
    devIds = None
    fanSpeeds = []
    steps = 5
    nbrOfShares = 3
    nbrOfDatapoints = 30
    margin = 0.3
    coreUCs = []
    memOCs = []
    powerLimits = []
    dollarPerMHash = None
    powerCost = None
    loadPreset = False
    skipMem = False
    skipCore = False
    skipPower = False
    watchdog = False

    for opt, arg in opts:
        if opt == '-h':
            print ('run.py --algo ethash --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits> <--loadPreset>')
            sys.exit()
        elif opt in ("-a", "--algo"):
            algo = arg
        elif opt in ("-t", "--mode"):
            mode = int(arg)
        elif opt in ("-d", "--devices"):
            arr = arg.split(",")
            devIds = []
            for item in arr:
                devIds.append(int(item))
        elif opt in ("-f", "--fans"):
            arr = arg.split(",")
            fanSpeeds = []
            for item in arr:
                fanSpeeds.append(int(item))
        elif opt in ("-s", "--steps"):
            steps = int(arg)
        elif opt in ("-x", "--shares"):
            nbrOfShares = int(arg)
        elif opt in ("-y", "--datapoints"):
            nbrOfDatapoints = int(arg)
        elif opt in ("-o", "--offset"):
            margin = float(arg)
        elif opt in ("-c", "--coreUC"):
            arr = arg.split(",")
            coreUCs = []
            for item in arr:
                coreUCs.append(int(item))
        elif opt in ("-m", "--memOC"):
            arr = arg.split(",")
            memOCs = []
            for item in arr:
                memOCs.append(int(item))
        elif opt in ("-p", "--powerLimit"):
            arr = arg.split(",")
            powerLimits = []
            for item in arr:
                powerLimits.append(int(item))
        elif opt in ("-e", "--powerCost"):
            powerCost = float(arg)
        elif opt in ("-i", "--dollarPerMHash"):
            dollarPerMHash = float(arg)
        elif opt in ("-w", "--loadPreset"):
            loadPreset = True
        elif opt in ("--miner"):
            miner = arg
        elif opt in ("--skipMem"):
            skipMem = True
        elif opt in ("--skipCore"):
            skipCore = True
        elif opt in ("--skipPower"):
            skipPower = True
        elif opt in ("--watchdog"):
            watchdog = True

    if mode == 2 and (dollarPerMHash == None or powerCost == None):
        mode = 0
        print("mode 2 can only be applied if \"--powerCost\" and \"--dollarPerMHash\" args are given, falling back to mode 0")

    # Start Optimizing Process
    Controller(miner, algo, mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, margin, coreUCs, memOCs, powerLimits, powerCost, dollarPerMHash, loadPreset, skipMem, skipCore, skipPower, watchdog)

if __name__ == "__main__":
    main(sys.argv[1:])