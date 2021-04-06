import logging
from pathlib import Path

from time import strftime
class Log:
    def __init__(self, level):
        subPath = "./logs"
        Path("./logs").mkdir(parents=True, exist_ok=True)
        filename="%s/autotune_%s.log" % (subPath, strftime("%Y-%m-%d %H %M %S"))
        if level == "INFO":
            logging.basicConfig(filename=filename, level=logging.INFO)
        elif level == "WARNING":
            logging.basicConfig(filename=filename, level=logging.WARNING)
        elif level == "ERROR":
            logging.basicConfig(filename=filename, level=logging.ERROR)
        else:
            logging.basicConfig(filename=filename, level=logging.DEBUG)

    def Error(self, msg):
        msg = strftime("%Y-%m-%d %H %M %S") + " " +  msg
        logging.error(msg)
        print("ERR:\t%s" % msg)
    
    def Warning(self, msg):
        msg = strftime("%Y-%m-%d %H %M %S") + " " +  msg
        logging.warning(msg)
        print("WARN:\t%s" % msg)

    def Info(self, msg):
        msg = strftime("%Y-%m-%d %H %M %S") + " " + msg
        logging.info(msg)
        print("INFO:\t%s" % msg)

    def Debug(self, msg):
        msg = strftime("%Y-%m-%d %H %M %S") + " " + msg
        logging.debug(msg)
        print("DEBUG:\t%s" % msg)