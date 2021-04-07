import json, requests
from responseParser import ResponseParser 


class MinerDataRequester:
    def __init__(self, log, miner, minerSw):
        self.log = log
        self.path = minerSw.GetRequesterPath()
        self.responseParser = ResponseParser(miner)
        self.path = "http://%s" % self.path
        self.log.Debug("will use path %s" % self.path)

    def getData(self):
        try:
            r = requests.get(self.path)
            if r.status_code == 200 and r is not None and r.json() is not None:
                #print("response code: %i" % r.status_code)
                #print(r.content)
                return self.responseParser.Parse(r.json())
        except:
            return None
        return None