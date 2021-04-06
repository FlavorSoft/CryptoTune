from expections import *

from gMinerParser import GMinerParser

validMiners = []
validMiners.append({"name":"gminer", "parser": GMinerParser()})

class ResponseParser:
    def __init__(self, miner):
        for val in validMiners:
            if val["name"] == miner:
                self.parser = val["parser"]
                return
        
        raise InvalidMinerException("no valid miner found for \"%s\"" % miner)
        
    def Parse(self, json):
        if self.parser is None:
            raise NoParseAvailableException("no valid parser was set")
        return self.parser.Parse(json)