from req import MinerDataRequester
from startMiner import StartMiner
from gpu import GPU
import json, time, sys, getopt
from controller import Controller 


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"h:t:d:f:s:x:y:o:c:m:p",["mode=", "devices=", "fans=", "steps=", "shares=", "datapoints=", "offset=", "coreUC=", "memOC=", "powerLimit="])
    except getopt.GetoptError:
        print('run.py --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits>')
        sys.exit(2)

    # defaults for 1 GPU
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

    for opt, arg in opts:
        print("opt: %s arg: %s" % (opt,arg))
        if opt == '-h':
            print ('run.py --mode <0 (efficiency) / 1 (speed)> --devices <0,1..nbr of GPUs> --fans <speed for each GPU> --steps <stepsize for OC> --shares <nbr of shares for validation> --datapoints <nbr of Datapoints for validation> --offset <for comparing speeds> --coreUC <core underclock values> --memOC <memory overclock values> --powerLimit <power limits>')
            sys.exit()
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

    #   miner "gminer", devIds [0] fan 70, steps 10, shareCount 10, nbrOfDatapoints 10, marginInMH 0.25, coreUC 50, memOC 1200, powerLimit 270
    Controller("gminer", mode, devIds, fanSpeeds, steps, nbrOfShares, nbrOfDatapoints, margin, coreUCs, memOCs, powerLimits)

if __name__ == "__main__":
    main(sys.argv[1:])