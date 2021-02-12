class State:
    pass


class Discharging(State):
    def __eq__(self, value):
        return True if value == 1 else False

    @staticmethod
    def value():
        return 1


class BattDisconnected(State):
    def __eq__(self, value):
        return True if value == 2 else False

    @staticmethod
    def value():
        return 2


class Charging(State):
    def __eq__(self, value):
        return True if value == 3 else False

    @staticmethod
    def value():
        return 3


class BattDisconnect(State):
    def __eq__(self, value):
        return True if value == 4 else False

    @staticmethod
    def value():
        return 4


class Waiting(State):
    def __eq__(self, value):
        return True if value == 5 else False

    @staticmethod
    def value():
        return 5


class MeasuringIR(State):
    def __eq__(self, value):
        return True if value == 6 else False

    @staticmethod
    def value():
        return 6


class MeasuringIR10Sec(State):
    def __eq__(self, value):
        return True if value == 7 else False

    @staticmethod
    def value():
        return 7


class Idle(State):
    def __eq__(self, value):
        return True if value == 8 else False

    @staticmethod
    def value():
        return 8


class NotSet(State):
    def __eq__(self, value):
        return True if value == 0 else False

    @staticmethod
    def value():
        return -1


def get_state(state_id):
    if state_id == 0:
        return NotSet
    if state_id == 1:
        return Discharging
    if state_id == 2:
        return BattDisconnected
    if state_id == 3:
        return Charging
    if state_id == 4:
        return BattDisconnect
    if state_id == 5:
        return Waiting
    if state_id == 6:
        return MeasuringIR
    if state_id == 7:
        return MeasuringIR10Sec
    if state_id == 8:
        return Idle

if __name__ == "__main__":
    print(Idle)
    print(Idle.__name__)
