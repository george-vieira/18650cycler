import logging

logging.getLogger('connectionpool').setLevel(logging.CRITICAL)

log = logging.getLogger()
log.setLevel(logging.DEBUG)
logFormatter = logging.Formatter('%(asctime)s [%(levelname)-8s] (%(module)s::%(funcName)s:%(lineno)s) %(message)s')

fileHandler = logging.FileHandler("application.log")
fileHandler.setFormatter(logFormatter)
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)
