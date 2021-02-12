import logging
import os
import queue
import sys
import threading

import cycler
import webserver

from modules import log

if __name__ == "__main__":
    logger = logging.getLogger('waitress')
    logger.setLevel(logging.DEBUG)

    logger.info("Main Start")

    # thread comms event
    comsevent = threading.Event()

    # message Queues
    webqueue = {}  # queue.Queue()
    cyclerqueue = queue.Queue()
    webserver.cyclerqueue = cyclerqueue
    webserver.webqueue = webqueue
    webserver.comsevent = comsevent

    logger.debug("Coms Init")

    try:
        cycler = cycler.Cycler(name='Cycler', comsevent=comsevent, cyclerqueue=cyclerqueue, webqueue=webqueue)

        # Start thread
        cycler.daemon = True
        cycler.start()

        # Start webserver
        webserver.run_server()
        # serve(webserver.app, host='0.0.0.0', port=8080, threads=6)
        print("Web server shutdown")

    except KeyboardInterrupt:
        logger.debug("Shutdown requested")
        comsevent.set()
        comsevent.wait()
        comsevent.set()
        comsevent.wait()
        logger.debug("Shutdown completed")
    except Exception as e:
        comsevent.set()
        comsevent.wait()
        comsevent.set()
        comsevent.wait()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.critical("Exception: '{}' {} {}:{}".format(e, exc_type, fname, exc_tb.tb_lineno))
