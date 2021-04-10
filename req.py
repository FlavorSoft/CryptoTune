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
            r = requests.get(self.path, timeout=1)
            if r.status_code == 200 and r is not None and r.json() is not None:
                return self.responseParser.Parse(r.json())
            return self.log.Warning("Mining software did not correctly respond. Code %i: Content: %s" % (r.status_code, r.text))
        except Exception as e:
            return self.log.Warning("Could not get Mining Software Data: %s" % str(e))