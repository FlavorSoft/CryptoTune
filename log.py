import logging
from pathlib import Path

from time import strftime
class Log:
    def __init__(self, level):
        subPath = "./logs"
        Path("./logs").mkdir(parents=True, exist_ok=True)
        filename="%s/autotune_%s.log" % (subPath, strftime("%Y-%m-%d_%H_%M_%S"))
        if level == "INFO":
            logging.basicConfig(filename=filename, level=logging.INFO)
        elif level == "WARNING":
            logging.basicConfig(filename=filename, level=logging.WARNING)
        elif level == "ERROR":
            logging.basicConfig(filename=filename, level=logging.ERROR)
        else:
            logging.basicConfig(filename=filename, level=logging.DEBUG)

    def GetMessage(self, msg):
        return strftime("%Y-%m-%d %H:%M:%S") + " - " +  msg

    def Error(self, msg):
        logging.error(self.GetMessage(msg))
        print("ERR:\t%s" % self.GetMessage(msg))
    
    def Warning(self, msg):
        logging.warning(self.GetMessage(msg))
        print("WARN:\t%s" % self.GetMessage(msg))

    def Info(self, msg):
        logging.info(self.GetMessage(msg))
        print("INFO:\t%s" % self.GetMessage(msg))

    def Debug(self, msg):
        logging.debug(self.GetMessage(msg))
        print("DEBUG:\t%s" % self.GetMessage(msg))