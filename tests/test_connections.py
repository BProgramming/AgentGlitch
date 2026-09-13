"""Tests for the two external-service seams: Steamworks and Discord Rich Presence.

Both packages are replaced by recorders in ``tests/support/stubs.py``, so these tests
are about Agent Glitch's own error handling and payload shaping, not about the SDKs.
"""

from __future__ import annotations

import os
import pathlib

import pytest

import Helpers
import SteamworksConnection as SteamworksModule
from DiscordConnection import DiscordConnection
from SteamworksConnection import SteamworksConnection
from support import stubs
from support.patches import HandledError


# --------------------------------------------------------------------------- #
# Steamworks
# --------------------------------------------------------------------------- #
class TestSteamworksConnection:
    def test_connecting_initialises_the_sdk_and_requests_stats(self) -> None:
        connection = SteamworksConnection()
        assert connection.connection.initialized is True

    def test_a_failed_stats_request_is_fatal(self,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(stubs._UserStats, "RequestCurrentStats", lambda self: False)
        with pytest.raises(HandledError):
            SteamworksConnection()

    @pytest.mark.parametrize("error", [
        stubs.SteamException("no steam"),
        OSError("library missing"),
        RuntimeError("something else entirely"),
    ])
    def test_every_initialisation_failure_is_reported_not_swallowed(self, error) -> None:
        stubs.STEAMWORKS.raise_on_initialize = error
        with pytest.raises(HandledError):
            SteamworksConnection.initialize()

    def test_dlc_ownership_is_reported_as_a_named_mapping(self) -> None:
        # Currently hard-coded to True pending a real DLC app id; the shape is what
        # Controller depends on.
        assert SteamworksConnection().has_dlc() == {"gumshoe": True}

    def test_the_dlc_app_id_is_still_a_placeholder(self) -> None:
        assert Helpers.DLC_APP_ID == 0

    def test_the_windows_dll_directory_hook_is_platform_guarded(self) -> None:
        # os.add_dll_directory exists only on Windows; the module guards on sys.platform
        # so importing on Linux/macOS must not have tried to call it.
        assert SteamworksModule.sys.platform != "win32" or hasattr(os, "add_dll_directory")


# --------------------------------------------------------------------------- #
# Discord
# --------------------------------------------------------------------------- #
class TestDiscordConnection:
    def test_connecting_opens_a_presence_and_stamps_a_start_time(self) -> None:
        connection = DiscordConnection()
        assert connection.presence is not None
        assert connection.activity["timestamps"]["start"] == connection.start_time

    def test_the_activity_starts_blank(self) -> None:
        connection = DiscordConnection()
        assert connection.activity["state"] == ""
        assert connection.activity["details"] == ""

    def test_a_refused_connection_degrades_to_no_presence(self) -> None:
        stubs.Presence.raise_on_connect = stubs.PresenceError("no discord")
        assert DiscordConnection().presence is None

    def test_a_missing_socket_degrades_to_no_presence(self) -> None:
        stubs.Presence.raise_on_connect = FileNotFoundError("no socket")
        assert DiscordConnection().presence is None

    def test_setting_a_status_pushes_the_activity(self) -> None:
        connection = DiscordConnection()
        connection.set_status(details = "On a mission:", state = "Rooftops")
        assert connection.presence.activities[-1]["details"] == "On a mission:"
        assert connection.presence.activities[-1]["state"] == "Rooftops"

    def test_setting_a_status_reconnects_when_the_presence_was_dropped(self) -> None:
        connection = DiscordConnection()
        connection.presence = None
        connection.set_status(details = "Back", state = "Online")
        assert connection.presence is not None

    def test_a_failed_push_drops_the_presence_rather_than_raising(self) -> None:
        connection = DiscordConnection()
        stubs.Presence.raise_on_set = True
        connection.set_status(details = "x")
        assert connection.presence is None

    def test_the_activity_is_updated_even_when_the_push_fails(self) -> None:
        connection = DiscordConnection()
        stubs.Presence.raise_on_set = True
        connection.set_status(details = "Recorded anyway")
        assert connection.activity["details"] == "Recorded anyway"

    def test_closing_clears_and_closes_the_presence(self) -> None:
        connection = DiscordConnection()
        presence   = connection.presence
        connection.close()
        assert presence.cleared == 1
        assert presence.closed == 1
        assert connection.presence is None

    def test_closing_twice_is_harmless(self) -> None:
        connection = DiscordConnection()
        connection.close()
        connection.close()

    def test_closing_swallows_a_presence_error(self,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
        connection = DiscordConnection()

        def _boom() -> None:
            raise stubs.PresenceError("gone")

        monkeypatch.setattr(connection.presence, "clear", _boom)
        connection.close()
        assert connection.presence is None

    def test_the_client_id_is_a_fixed_application_id(self) -> None:
        assert DiscordConnection.CLIENT_ID.isdigit()


class TestIpcSocketShim:
    def test_no_runtime_dir_means_nothing_to_do(self,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising = False)
        assert DiscordConnection._ensure_ipc_socket() is None

    def test_a_runtime_dir_without_a_flatpak_socket_is_left_alone(
            self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        DiscordConnection._ensure_ipc_socket()
        assert not (tmp_path / "discord-ipc-0").exists()

    def test_a_flatpak_socket_is_symlinked_into_place(
            self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
        import socket

        flatpak_dir = tmp_path / "app" / "com.discordapp.Discord"
        flatpak_dir.mkdir(parents = True)
        sock_path = flatpak_dir / "discord-ipc-0"

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(sock_path))
            monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
            DiscordConnection._ensure_ipc_socket()
            assert (tmp_path / "discord-ipc-0").is_symlink()
        finally:
            server.close()
