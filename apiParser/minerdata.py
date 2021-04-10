class MinerData:
    def __init__(self, name, bus, speed, accepted, rejected, invalid):
        self.name = name
        self.bus = bus
        self.speed = speed
        self.accepted = accepted
        self.rejected = rejected
        self.invalid = invalid