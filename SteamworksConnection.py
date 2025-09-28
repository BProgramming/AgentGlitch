import os
from Helpers import handle_exception
os.add_dll_directory(os.getcwd())
from steamworks import STEAMWORKS
from steamworks.exceptions import *


class SteamworksConnection:
    def __init__(self):
        self.connection = self.initialize()
        self.connection.UserStats.RequestCurrentStats()

    @staticmethod
    def initialize() -> STEAMWORKS:
        sw = STEAMWORKS()

        try:
            sw.initialize()
        except SteamException as e:
            handle_exception(str(e))
        except OSError as e:
            handle_exception(str(e))
        except Exception as e:
            handle_exception(str(e))
        return sw

    def has_dlc(self) -> dict[str, bool]:
        return {"gumshoe": True}
