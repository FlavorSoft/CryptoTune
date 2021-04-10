import json
from apiParser.minerdata import MinerData

class TRexParser:
    def Parse(self, data):
        res = []
        for device in data["gpus"]:
            accepted = 0
            invalid = 0
            rejected = 0
            if device["shares"] is not None:
                accepted = device["shares"]["accepted_count"]
                invalid = device["shares"]["invalid_count"]
                rejected = device["shares"]["rejected_count"]
            res.append(MinerData(device["name"], device["pci_bus"], device["hashrate"], accepted, rejected, invalid))
        return res