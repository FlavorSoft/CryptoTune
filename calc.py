

class Calculator:
    def __init__(self, speedOffset, powerCost, dollarPerMHash):
        self.speedOffset = speedOffset
        self.powerCost = powerCost
        self.dollarPerMHash = dollarPerMHash

    def Speed(self, minerDataArr):
        if len(minerDataArr) == 0:
            return 0.0
        sum = 0.0
        for item in minerDataArr:
            sum += item.speed
        return sum / len(minerDataArr)

    def Power(self, minerDataArr, hwDataArr):
        if len(hwDataArr) == 0:
            return 999.9

        # data that was reported without any minerdata should be excluded, therefore we will skip those entries
        skip = len(minerDataArr) - len(hwDataArr)
        sum = 0.0
        for item in hwDataArr[skip:]:
            sum += float(item["power_readings"]["power_draw"]["$"].split(" ")[0])
        return sum / len(hwDataArr[skip:])

    def Efficiency(self, minerDataArr, hwDataArr):
        if len(minerDataArr) == 0 or len(hwDataArr) == 0:
            return 0.0

        return self.Speed(minerDataArr) / self.Power(minerDataArr, hwDataArr)

    def Profitability(self, minerDataArr, hwDataArr):
        if self.powerCost is None or self.dollarPerMHash is None or len(minerDataArr) == 0 or len(hwDataArr) == 0:
            return 0.0

        grossProfit = self.dollarPerMHash * self.Speed(minerDataArr) / 1000000.0
        powerCost = self.powerCost / 1000 * 24 * self.Power(minerDataArr, hwDataArr)
        return grossProfit - powerCost

    