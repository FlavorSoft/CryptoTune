from startMiner import StartMiner
from log import Log
log = Log("DEBUG")

ms = StartMiner(log, "UnixWorker", "gminer", [0], [70])
