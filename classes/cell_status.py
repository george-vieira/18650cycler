#
# class cell_data:
#     def __init__(self, values: dict):
#         self.check_parameters(values)
#
#         self._timestamp = values['timestamp']
#         self._voltage = values['voltage']
#         self._current = values['current']
#         self._amphours = values['amphours']
#         self._watthours = values['watthours']
#         self._temp = values['temp']
#
#     @staticmethod
#     def check_parameters(values):
#         # Ensure expected settings
#         valid_keys = [ 'timestamp', 'voltage', 'current', 'amphour', 'watthour', 'temp' ]
#
#         if any(True for k in valid_keys if k not in values):
#             raise ValueError('Missing parameter, expected {}'.format(valid_keys))
#
#         if any(True for k in values if k not in valid_keys):
#             raise ValueError('Unexpected parameter, expected only {}'.format(valid_keys))
#
#     @property
#     def to_json(self):
#         return {
#             'voltage': self._voltage,
#             'current': self._current,
#             'timestamp': self._timestamp
#         }
