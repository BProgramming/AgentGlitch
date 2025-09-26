from discordrp import Presence
import time


class DiscordActivity:
    CLIENT_ID: str = "1413505164362649731"

    def __init__(self) -> None:
        self.presence: Presence = Presence(DiscordActivity.CLIENT_ID)
        self.start_time: int = int(time.time())
        self.activity: dict[str, str | dict[str, int]] = {"state": "", "details": "", "timestamps": {"start": self.start_time}}

    def set_status(self, details: str="", state: str="") -> None:
        self.activity["details"] = details
        self.activity["state"] = state
        self.presence.set(self.activity)

    def close(self) -> None:
        self.presence.clear()
        self.presence.close()
