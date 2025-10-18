import os
from Helpers import handle_exception, DLC_APP_ID
os.add_dll_directory(os.getcwd())
from steamworks import STEAMWORKS
from steamworks.exceptions import *


class SteamworksConnection:
    DLC_APP_ID = 0

    def __init__(self):
        self.connection = self.initialize()
        if not self.connection.UserStats.RequestCurrentStats():
            handle_exception(f'{ConnectionError("Couldn't retrieve Steam user info.")}')

    @staticmethod
    def initialize() -> STEAMWORKS:
        sw = STEAMWORKS()

        try:
            sw.initialize()
        except SteamException as e:
            handle_exception(f'{e}')
        except OSError as e:
            handle_exception(f'{e}')
        except Exception as e:
            handle_exception(f'{e}')
        return sw

    def has_dlc(self) -> dict[str, bool]:
        return {"gumshoe": True}##self.connection.Apps.IsDLCInstalled(SteamworksConnection.DLC_APP_ID)}
