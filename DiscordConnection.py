from __future__ import annotations
import os
import pathlib
import time
from discordrp import Presence, PresenceError


class DiscordConnection:
    CLIENT_ID: str = "1413505164362649731"

    def __init__(
            self: DiscordConnection,
    ) -> None:
        """Open a Discord Rich Presence connection and initialize the activity payload."""
        self._ensure_ipc_socket()
        self.presence:   Presence | None                 = self._connect()
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
        """Update the Discord presence with new details and state text."""
        self.activity["details"] = details
        self.activity["state"]   = state

        if self.presence is None:
            self._ensure_ipc_socket()
            self.presence = self._connect()

        if self.presence:
            try:
                self.presence.set(self.activity)
            except PresenceError:
                self.presence = None

        return None

    def close(
            self: DiscordConnection,
    ) -> None:
        """Clear and close the Discord presence connection."""
        if self.presence:
            try:
                self.presence.clear()
                self.presence.close()
            except PresenceError:
                pass
            self.presence = None

        return None

    @staticmethod
    def _connect() -> Presence | None:
        """Connect to the Discord client if able."""
        try:
            return Presence(DiscordConnection.CLIENT_ID)
        except (PresenceError, FileNotFoundError):
            return None

    @staticmethod
    def _ensure_ipc_socket() -> None:
        """On Linux, Discord might be running in an unexpected environment. This symlinks to the proper environment."""
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if not runtime_dir:
            return None

        expected = pathlib.Path(runtime_dir) / "discord-ipc-0"
        flatpak  = pathlib.Path(runtime_dir) / "app" / "com.discordapp.Discord" / "discord-ipc-0"

        if not expected.is_socket() and flatpak.is_socket():
            if expected.is_symlink():
                expected.unlink()
            expected.symlink_to(flatpak)

        return None
