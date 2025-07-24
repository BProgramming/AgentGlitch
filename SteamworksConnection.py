import os
from Helpers import handle_exception
os.add_dll_directory(os.getcwd())
from steamworks import STEAMWORKS
from steamworks.exceptions import *


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
