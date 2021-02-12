import logging
from typing import List

from modules.states import Discharging, Idle, NotSet, State, get_state

cRed = "\033[31m"
cGreen = "\033[32m"
cYellow = "\033[33m"
cBlue = "\033[34m"
cMag = "\033[35m"
cCyan = "\033[36m"
cNorm = "\033[0m"


class CellData:
    """
    Contains slot cell metrics data
    """
    valid_keys = ['slot_id', 'stage_id', 'stage', 'voltage', 'current', 'amphour', 'watthour', 'temp', 'timestamp']

    def __init__(self, values: dict):
        """

        :param values:
        """
        self.log = logging.getLogger(__name__)

        self.check_parameters(values)
        self._slot_id = values['slot_id']
        self._timestamp = values['timestamp']
        self._voltage = values['voltage']
        self._current = values['current']
        self._amphour = values['amphour']
        self._watthour = values['watthour']
        self._temp = values['temp']
        self._stage_id = NotSet.value
        self._stage = NotSet

        try:
            self._stage_id = Discharging().value()
            self._stage = get_state(int(values['stage_id']))
            return
        except:
            self.log.info("{}Failed to set state: {} {}".format(cRed, values['stage_id'], cNorm))

        if int(values['stage_id']) == Idle().value:
            self._stage_id = Idle().value
            self._stage = Idle
            self.log.info("{}Slot# {} is now IDLE{}".format(cGreen, self._slot_id, cNorm))
            return
        raise ValueError("Invalid stage_id value: {}".format(values['stage_id']))

    @property
    def slot_id(self):
        """

        :return:
        """
        return self._slot_id

    def check_parameters(self, values: dict) -> None:
        """

        :param values:
        :return:
        """
        missing = [k for k in self.valid_keys if k not in values ]
        if missing:
            raise ValueError('{}Missing parameter(s): {}{}'.format(cRed, missing, cNorm))

        if any(True for k in values if k not in self.valid_keys):
            raise ValueError('Unexpected parameter, expected only {}'.format(self.valid_keys))

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def to_json(self) -> dict:
        """

        :return:
        """
        return {
            i: getattr(self, "_" + i) if 'stage' != i else self._stage.__name__ for i in self.valid_keys
        }


class Cell:
    """
    Cell object containing information about the cell, metrics, etc
    """

    def __init__(self, _id: int):
        self.log = logging.getLogger(__name__)

        self._id = _id
        self._state = Idle
        self._model = None
        self._manufacturer = None
        self._cycle_count = 0

        self._history = []

    def set_cell(self, _id: str, model: str, manufacturer: str) -> None:
        """

        :param _id:
        :param model:
        :param manufacturer:
        """
        self._id = _id
        self._model = model
        self._manufacturer = manufacturer

    def add_history(self, cell_data: CellData) -> None:
        """

        :param cell_data:
        :return:
        """
        self._history.append(cell_data)

    def get_history(self) -> List[CellData]:
        """

        :return: list of cell history
        """
        return list(celldata for celldata in self._history)

    def get_last_history(self) -> CellData:
        """
        Returns the latest cell data or an empty dict()
        :return: dic
        """
        return self.get_history()[-1] if len(self.get_history()) else CellData(dict())

    def clear_history(self) -> None:
        """

        :return:
        """
        self._history = []

    @property
    def state(self):
        """

        :return:
        """
        return self._state

    @state.setter
    def state(self, set_state):
        """

        :param set_state:
        :return:
        """
        if not issubclass(set_state, State):
            raise Exception("Not of type 'State'")
        self._state = set_state

    def cell_status_since(self, timestamp):
        selected = filter(lambda x: x.timestamp > timestamp, self.get_history()[::-1])
        output = {
            "state": self.state,
            "history": selected[::-1]
        }
        return output


if __name__ == "__main__":
    c = Cell(0)
    print(c)
