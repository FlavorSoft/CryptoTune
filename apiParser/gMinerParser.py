import json
from apiParser.minerdata import MinerData

class GMinerParser:
    def Parse(self, json):
        res = []
        for device in json["devices"]:
            res.append(MinerData(device["name"], device["bus_id"], device["speed"], device["accepted_shares"], device["rejected_shares"], device["invalid_shares"]))
        return res