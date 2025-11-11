from discordrp import Presence, PresenceError
import time


class DiscordConnection:
    CLIENT_ID: str = "1413505164362649731"

    def __init__(self) -> None:
        try:
            self.presence: Presence | None = Presence(DiscordConnection.CLIENT_ID)
        except Exception:
            self.presence = None
        self.start_time: int = int(time.time())
        self.activity: dict[str, str | dict[str, int]] = {"state": "", "details": "", "timestamps": {"start": self.start_time}}

    def set_status(self, details: str="", state: str="") -> None:
        if self.presence is not None:
            self.activity["details"] = details
            self.activity["state"] = state
            try:
                self.presence.set(self.activity)
            except Exception:
                pass

    def close(self) -> None:
        if self.presence is not None:
            try:
                self.presence.clear()
                self.presence.close()
            except Exception:
                pass
