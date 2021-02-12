import json
import logging
import os
import re
import sys
import threading
import time

from classes.cell import Cell, CellData
from modules.states import *  # State, Idle, Charging, Discharging
from modules.usbserial import USBSerial

# from modules.http import Http

cRed = "\033[31m"
cGreen = "\033[32m"
cYellow = "\033[33m"
cBlue = "\033[34m"
cMag = "\033[35m"
cCyan = "\033[36m"
cNorm = "\033[0m"


class profile:
    time_start = None
    time_end = None


class profiles:
    profiles = []
    index = 0


class Slot:
    def __init__(self, slot_id):
        """

        :param slot_id:
        """
        self.log = logging.getLogger(__name__)
        self._slot_id = slot_id
        self._state = Idle
        self._profile = None
        self._cell = Cell()
        self._history = []

        self._cycle_count = 0
        self._stage = Idle

    @property
    def status(self) -> dict:
        """

        :return:
        """
        return {
            "state": str(self._state)
        }

    @property
    def cell(self) -> Cell:
        """

        :return:
        """
        return self._cell

    @property
    def has_cell(self) -> bool:
        """

        :return:
        """
        return type(self.cell) is Cell

    @property
    def cell_status(self) -> CellData:
        """

        :return:
        """
        if self.has_cell:
            raise Exception("No cell set")
        if self.cell.state == Idle:
            return CellData(dict())

        return self.cell.get_last_history()

    def clear_history(self) -> None:
        """

        :return:
        """
        if self.has_cell:
            self.log.debug("{}Cell in slot# {} reset, all history cleared{}".format(cCyan, self._slot_id, cNorm))
            self.cell.clear_history()

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value):
        self._start_time = time.time()

    @property
    def elapsed_time(self):
        return time.time() - self._start_time

    def set_state(self, state):
        if not issubclass(state, State):
            raise ValueError("Expected type of '{}' but received '{}'".format(type(State), type(state)))

        self._state = state

        if state == Discharging:
            self._cycle_count = 0
            self._cycle_total = 0
            self._stage = Idle
            self.state_now = -1
            self.full_list = []
            self.pending = 0
            self._voltage = None
            self._amphours = None
            self._watthours = None
            self._current = None
            self._temp = None

    # @state.setter
    def state(self, value):
        if issubclass(value, State):
            raise ValueError("'{}' not a value State".format(value))
        if self._state != Idle and value != Idle:
            raise ValueError("Cannot set new state of non idle cell")
        self._state = value

    def next_cycle(self):
        if self._cycle_total == 0:
            if self.state_now == 2:
                self.log.info("Cell1 charging cycle completed")
                self.set_state(Idle)
                return
            if self.state_now == 7:
                self.log.info("Cell2 charging cycle completed")
                self.set_state(Idle)
                return
            if self.state_now == 1:
                self.log.info("Cell1 discharging cycle completed")
                self.set_state(Idle)
                return
            if self.state_now == 6:
                self.log.info("Cell2 discharging cycle completed")
                self.set_state(Idle)
                return
        elif self._cycle_total > self._cycle_count:
            if self.state_now == 1:
                self.stage = Idle
                self.log.info("Full cycle completed")
                return
            elif self.state_now == 2:
                # increase cycle count
                self.log.info("Cycle {} of {} completed".format(self._cycle_count, self._cycle_total))
                self._cycle_count += 1
        else:
            if self.state_now == 2:
                self.log.info("Cell1 cycle test completed")
                self.set_state(Idle)
            if self.state_now == 1:
                self.stage = Idle
                self.log.info("Full cycle completed")

    @property
    def get_history(self):
        return self._history

    def add_history(self, cell_data: CellData):
        self._history.append(cell_data)


class Cycler(threading.Thread):
    def __init__(self, group=None, target=None, name=None, comsevent=None, cyclerqueue=None, webqueue=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)

        self.device = None
        self.total_slots = 2

        # Threading objects
        self.comsevent = comsevent
        self.webqueue = webqueue
        self.cyclerqueue = cyclerqueue

        self.log = logging.getLogger(__name__)

        # Initialize slots
        self.slots = []
        for id in range(1, self.total_slots + 1):
            self.slots.append(Cell(id))

        self.log.debug("{}Number of cyclers configured: {}{}".format(cCyan, self.total_slots, cNorm))

    def comm_init(self):
        if not self.device or not self.device.is_connected:
            # Connect
            # ________
            self.device = USBSerial('/dev/ttyACM0')
            try:
                self.device.connect()
            except Exception as e:
                if not self.device:
                    self.log.error("Closing serial")
                    self.device.close()
                self.log.error("Serial connect failed: {}".format(e))
                time.sleep(5)
            else:
                self.log.info("Connected to serial")

        if not self.device.is_sync:
            # Initialize
            # ___________
            try:
                while not self.sync():
                    time.sleep(0.1)
                self.log.info("Arduino sync completed")
            except Exception as e:
                time.sleep(5)
                self.log.error("Arduino sync failure: {}".format(e))
            else:
                self.log.info("Synced with arduino")

    def connect(self):
        self.stage = 'connecting'
        self.log.info('Connecting')

        while not self.device.connect():
            time.sleep(1)
        self.stage = 'connected'
        self.log.info('Connected')

        return True

    # Communicate to arduino, ensure response
    # ________________________________________
    def sync(self):
        """

        :return:
        """
        if not self.device:
            raise ("Device not connected, device is: {}".format(self.device))

        self.log.debug("Sending NL to get a prompt")
        self.device.sendline("\n")

        self.log.debug("Fetching received lines")
        data = self.device.readlines()
        for line in data:
            self.log.debug("Received: {}{}{}".format(cBlue, line, cNorm))
            # self.sync()
        self.log.debug("Sending ? to get menu")
        self.device.sendline("?\n")
        time.sleep(0.1)

        data = self.device.readlines()
        for line in data:
            self.log.debug("Received: {}{}{}".format(cBlue, line, cNorm))
        for line in data:
            self.log.debug("Checking: {}{}{}".format(cBlue, line, cNorm))
            if '>' in line:
                # NEW if '> Select Mode:'  in line:
                self.stage = 'initialized'
                self.log.info(cGreen + 'Initialized' + cNorm)
                # Define the device as in sync
                self.device.is_sync = True
                return True

        return False

    def get_slot_history(self, slot_id):
        return [c.to_json for c in self.slots[slot_id].get_history()]

    def get_slots_status(self, slot_id):
        return json.dumps({
            "status": self.slots[slot_id].state.__name__,
            "data": [
                self.slots[slot_id].get_history()[-1].to_json
                if len(self.slots[slot_id].get_history()) > 0 else []
            ]})

    def api_charge_slot(self, request_id: str, slot_id: int, data: dict):
        settings = ""
        settings += "" if 'current' not in data['payload'] or data['payload']['current'] == "" else "i{} ".format(
                data['payload']['current'])
        settings += "" if 'voltage' not in data['payload'] or data['payload']['voltage'] == "" else "v{} ".format(
                data['payload']['voltage'])
        settings += "" if 'cutoffma' not in data['payload'] or data['payload']['cutoffma'] == "" else "o{} ".format(
                data['payload']['cutoffma'])

        # Detect cells state
        if self.slots[slot_id].state != Idle:
            return self.respond(request_id, "Slot {} is not idle".format(slot_id), 400)
        else:
            self.slots[slot_id].state = Charging
            self.log.info(
                    "{}Started charge on Slot {} with settings: {}{}".format(cGreen, slot_id,
                                                                             settings if settings else "default",
                                                                             cNorm))

            self.device.sendline("n{}\n".format(slot_id + 1))
            time.sleep(0.1)
            self.device.sendline("c{} {}\n".format(slot_id + 1, settings))
            return self.respond(request_id,
                                "Started charge on Slot {} with settings: {}".format(slot_id,
                                                                                     settings if settings else "default"),
                                200)

    def respond(self, request_id, message, code=200, content_type='application/json'):
        """

        :param message:
        :param code:
        :return:
        """
        return self.webqueue[request_id].put(
                {
                    "message": message if message is str else json.dumps(message),
                    "code": code,
                    "mimetype": content_type
                })

    def format_data(self, slot_id, data):
        formatted = {
            "slot_id": int(slot_id),
            "stage_id": int(data[6][0]),
            "stage": get_state(int(data[6][0])),
            "voltage": float(data[1]),
            "current": float(data[2]),
            "amphour": float(data[3]),
            "watthour": float(data[4]),
            "temp": float(data[5]),
            "timestamp": time.time()
        }
        return formatted

    def process_cycle_data(self, line):
        """

        :param line:
        :return:
        """
        #
        # check for actions
        # _______________
        match = re.search(r'> Cell (\d+) OVT, stopping', line)
        if match:
            slot_id = int(match.group(1)) - 1  # TODO zero base slots
            self.slots[slot_id].state = Idle
            self.log.info("{}Slot{} is now IDLE{}".format(cGreen, slot_id, cNorm))
            return

        value_list = line.split(',')

        # Ignore remaining menu lines
        if line[0] == '>':
            return

        # Determine slot id
        try:
            self.log.debug("{}Received: {}{}".format(cCyan, value_list, cNorm))

            # State = completed charge, exit out
            msg_type = int(value_list[0])

            # Set the slot_id
            if msg_type in {0, 1, 2, 3}:
                slot_id = 0
            elif msg_type in {5, 6, 7, 8}:
                slot_id = 1
            else:
                # Skip non cell# info (4 is debug)
                return

            state_type = int(value_list[-1])

            # Check if end of a cycle

            self.slots[slot_id].state = get_state(state_type)
            if state_type == Idle:
                self.log.info("{}Slot# {} is now IDLE{}".format(cGreen, slot_id, cNorm))

            # Store data in slot data
            try:
                formatted = self.format_data(slot_id, value_list)
            except:
                self.log.critical("BAD format: {}::{}".format(slot_id, value_list))
                return

            # slot_id = cell_data.slot_id
            self.slots[slot_id].add_history(CellData(formatted))

            return

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.log.critical("{}Exception: '{}' {} {}:{}{}".format(cRed, e, exc_type, fname, exc_tb.tb_lineno, cNorm))

    def is_valid_slot(self, slot_id):
        if slot_id < 0 or slot_id > self.total_slots - 1:
            self.log.critical("{}Invalid Slot: {}{}".format(cRed, slot_id, cNorm))
            return False
        return True

    # Running thread
    # _______________
    def run(self):
        """

        :return:
        """
        # Initialize serial device
        self.comm_init()
        self.log.info('{}Cycler process running{}'.format(cGreen, cNorm))

        #
        # MAIN comms loop
        #
        try:
            # While comms is enabled
            while not self.comsevent.is_set():
                # self.log.error("{}comms interrup set: {}{}".format(cRed, self.comsevent.is_set(), cNorm))

                try:
                    if self.device is None or not self.device.is_connected or not self.device.is_sync:
                        self.log.error("{}Re-initializing lost comms{}".format(cRed, cNorm))
                        self.comm_init()
                except:
                    self.log.error("{}Re-initializing lost comms{}".format(cRed, cNorm))
                    self.comm_init()

                #
                # check for actions
                # _______________
                while not self.cyclerqueue.empty():
                    # self.log.info("{}Messages in queue: {}{}".format(cMag, len(self.cyclerqueue.queue), cNorm))
                    request = self.cyclerqueue.get()
                    action = request['action']
                    request_id = request['request_id']

                    # define slot_id or -1
                    slot_id = -1 if 'slot_id' not in request else int(request['slot_id'])

                    self.log.debug(
                            "{}Id: {} Request: {}{}".format(cMag, request_id, request, cNorm))

                    if self.device is None or not self.device.is_connected or not self.device.is_sync:
                        self.webqueue[request_id].put({
                            "message": "Comm port failure, attempting to reconnect and sync",
                            "code": 500,
                            "mimetype": "application/json"
                        })
                        continue

                    # /api/history/#
                    if action == 'history':
                        if not self.is_valid_slot(slot_id):
                            self.webqueue[request_id].put({
                                "message": "Invalid slot_id",
                                "code": 400,
                                "mimetype": "application/json"
                            })
                        else:
                            self.webqueue[request_id][request_id].put(
                                    {
                                        "message": json.dumps(self.get_slot_history(slot_id)),
                                        "code": 200,
                                        "mimetype": "application/json"
                                    })
                    # /api/status/#
                    elif action == "status":
                        self.webqueue[request_id].put({
                            "message": self.get_slots_status(slot_id),
                            "code": 200,
                            "mimetype": "application/json"
                        })
                    # /api/stop/#
                    elif action == "stop":
                        self.api_stop(request_id, slot_id)
                    # /api/charge/#
                    elif action == "charge":
                        if not self.is_valid_slot(slot_id):
                            self.webqueue[request_id].put({
                                "message": "Invalid slot_id",
                                "code": 400,
                                "mimetype": "application/json"
                            })
                        else:
                            # self.slots[slot_id].clear_history()
                            self.api_charge_slot(request_id, slot_id, request)
                            # /api/charge/#
                    elif action == "cycle":
                        if not self.is_valid_slot(slot_id):
                            self.webqueue[request_id].put({
                                "message": "Invalid slot_id",
                                "code": 400,
                                "mimetype": "application/json"
                            })
                        else:
                            # self.slots[slot_id].clear_history()
                            self.api_cycle_slot(request_id, slot_id, request)
                    # /api/charge/#
                    elif action == "discharge":
                        if not self.is_valid_slot(slot_id):
                            self.webqueue[request_id].put({
                                "message": "Invalid slot_id",
                                "code": 400,
                                "mimetype": "application/json"
                            })
                        else:
                            # self.slots[slot_id].clear_history()
                            self.api_discharge(request_id, slot_id, request)
                    else:
                        self.webqueue[request_id].put(
                                {
                                    "message": "Unknown API request [{}]".format(request),
                                    "code": 404,
                                    "mimetype": "application/json"
                                })

                #
                # check for serial data
                # _______________
                for line in self.device.readlines():
                    if line:
                        self.process_cycle_data(line)

                time.sleep(0.1)
            self.log.critical("Cycler breaking out")
            sys.exit()
        except KeyboardInterrupt:
            self.log.warning("{}Cycler thread cancelled{}".format(cYellow, cNorm))
            raise KeyboardInterrupt

    def api_discharge(self, request_id: str, slot_id: int, data: dict):
        """

        :param cellid:
        :param data:
        :return:
        """
        self.slots[slot_id].clear_history()
        settings = ""
        settings += "" if 'discma' not in data['payload'] or data['payload']['discma'] == "" else "i{} ".format(
                data['payload']['discma'])
        settings += "" if 'cutoffmv' not in data['payload'] or data['payload']['cutoffmv'] == "" else "v{} ".format(
                data['payload']['cutoffmv'])
        settings += "" if 'mode' not in data['payload'] or data['payload']['mode'] == "" else "m{} ".format(
                data['payload']['mode'])

        # Detect cells state
        if self.slots[slot_id].state != Idle:
            return self.respond(request_id, "Slot {} not idle".format(slot_id), 400)
        else:
            self.device.sendline("n{}\n".format(slot_id + 1))
            self.log.info("Started discharge on Cell {} settings:{}".format(slot_id + 1, settings))
            time.sleep(0.1)
            self.device.sendline("d{} {}\n".format(slot_id + 1, settings))
            self.slots[slot_id].state = Discharging

            return self.respond(request_id,
                                "Started discharge on Slot {} with settings: {}".format(slot_id, settings),
                                200)

    def api_cycle_slot(self, request_id, slot_id, data):
        """

        :param slot_id:
        :param data:
        :return:
        """
        self.slots[slot_id].clear_history()
        settings = ""
        settings += "" if 'discma' not in data['payload'] or data['payload']['discma'] == "" else "y{} ".format(data['payload']['discma'])
        settings += "" if 'cutoffmv' not in data['payload'] or data['payload']['cutoffmv'] == "" else "v{} ".format(data['payload']['cutoffmv'])
        settings += "" if 'mode' not in data['payload'] or data['payload']['mode'] == "" else "m{} ".format(data['payload']['mode'])
        settings += "" if 'chrma' not in data['payload'] or data['payload']['chrma'] == "" else "k{} ".format(data['payload']['chrma'])
        settings += "" if 'chrmv' not in data['payload'] or data['payload']['chrmv'] == "" else "u{} ".format(data['payload']['chrmv'])
        settings += "" if 'cutoffma' not in data['payload'] or data['payload']['cutoffma'] == "" else "o{} ".format(data['payload']['cutoffma'])
        settings += "" if 'cycles' not in data['payload'] or data['payload']['cycles'] == "" else "l{} ".format(data['payload']['cycles'])

        # Detect cells state
        if self.slots[slot_id].state != Idle:
            return self.respond(request_id, "Cell {} not idle".format(slot_id + 1), 400)
        else:
            # self.slots[slot_id].state = 'cycle'
            # self.slots[slot_id].cycle_total = int(data['cycles'] if data['cycles'] != "" else 1)
            self.log.info("Cycle start on Slot {} settings: {}".format(slot_id + 1, settings))
            self.device.sendline("n{}\n".format(slot_id + 1))
            time.sleep(0.1)
            self.device.sendline("y{} {}\n".format(slot_id + 1, settings))

            return self.respond(request_id, "Cycle start on Slot {} settings: {}".format(slot_id + 1, settings), 200)

    def api_stop(self, request_id, slot_id):
        """

        :param slot_id:
        :return:
        """
        if self.slots[slot_id].state == Idle:
            return self.respond(request_id, "Cell {} is already idle".format(slot_id), 400)
        else:
            self.device.sendline("n{}\n".format(slot_id + 1))
            self.log.info("Stopping Slot {} currently:{}".format(slot_id, self.slots[slot_id].state))
            self.slots[slot_id].state = Idle
            return self.respond(request_id, "Stopping Slot {}".format(slot_id), 200)

    def api_status(self, request_id, slot_id, params):
        """

        :param slot_id:
        :param params:
        :return:
        """
        return self.respond(request_id, [
            cid.state() for cid in self.slots
        ], 200)

    def api_history(self, request_id, slot_id: int):
        """

        :param slot_id:
        :param params:
        :return:
        """

        return self.respond(request_id, self.slots[slot_id].get_history, 200)
