from __future__ import annotations
import time
from discordrp import Presence, PresenceError


class DiscordConnection:
    CLIENT_ID: str = "1413505164362649731" # Managed externally on the Discord site

    def __init__(
            self: DiscordConnection,
    ) -> None:
        try:
            self.presence: Presence | None = Presence(DiscordConnection.CLIENT_ID)
        except PresenceError:
            self.presence = None
        self.start_time: int                             = int(time.time())
        self.activity:   dict[str, str | dict[str, int]] = {
            "state":      "",
            "details":    "",
            "timestamps": {"start": self.start_time},
        }

    def set_status(
            self:    DiscordConnection,
            details: str = "",
            state:   str = "",
    ) -> None:
        if self.presence:
            self.activity["details"] = details
            self.activity["state"]   = state

            try:
                self.presence.set(self.activity)
            except PresenceError:
                pass

        return None

    def close(
            self: DiscordConnection,
    ) -> None:
        if self.presence:
            try:
                self.presence.clear()
                self.presence.close()
            except PresenceError:
                pass

        return None
