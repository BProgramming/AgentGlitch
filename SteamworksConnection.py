import sys
import os
from pathlib import Path
from Helpers import handle_exception, DLC_APP_ID

# os.add_dll_directory is Windows-only (Python 3.8+).
# On Linux/macOS the shared library (libsteam_api.so / SteamworksPy.so) is
# found via LD_LIBRARY_PATH or because it sits next to the executable, so no
# explicit directory registration is needed.
if sys.platform == "win32":
    os.add_dll_directory(str(Path.cwd()))

from steamworks import STEAMWORKS
from steamworks.exceptions import SteamException


class SteamworksConnection:
    def __init__(self):
        self.connection = self.initialize()
        if not self.connection.UserStats.RequestCurrentStats():
            handle_exception(f'{ConnectionError("Couldn\'t retrieve Steam user info.")}')

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
        return {"gumshoe": True}  ## self.connection.Apps.IsDLCInstalled(DLC_APP_ID)}
