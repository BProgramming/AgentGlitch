"""Checks against the *real* third-party packages, when they happen to be installed.

The suite replaces ``SimpleVFX``, ``steamworks``, ``discordrp`` and ``cv2`` with
recorders so a run is identical everywhere.  That buys determinism at the cost of one
thing: a stub accepts any call, so it cannot notice when the game and the real library
drift apart.

These tests close that gap.  Each one runs in a subprocess -- where ``sys.modules`` is
clean and the genuine package is importable -- and skips when the package is not
installed.  They check *shape*, never behaviour: does the real class still accept the
arguments Agent Glitch passes it?
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest


def _probe(source: str) -> subprocess.CompletedProcess:
    """Run a snippet in a clean interpreter and return the completed process.

    Exit code 0 means the check passed, 77 means "package not installed" (skip),
    anything else is a failure whose stderr is the message.
    """
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        capture_output = True, text = True, timeout = 60,
    )


def _run_or_skip(source: str) -> None:
    result = _probe(source)
    if result.returncode == 77:
        pytest.skip(result.stdout.strip() or "package not installed")
    assert result.returncode == 0, result.stderr or result.stdout


def test_the_real_visual_effect_accepts_every_call_the_game_makes() -> None:
    """Every keyword set the game passes to ``SimpleVFX.VisualEffect``, by call site."""
    _run_or_skip("""
        import inspect, sys
        try:
            from SimpleVFX.SimpleVFX import VisualEffect
        except Exception:
            print("SimpleVFX is not installed")
            sys.exit(77)

        CALLS = [
            # Actor.jump -- double-jump trail
            dict(image_name="JUMPLINES", direction=[], rotation=0.0, alpha=64,
                 offset=(0, 0), scale=(0, 0)),
            # Actor.loop -- resize burst
            dict(image_name="RESIZEBURST", alpha=128, scale=(0, 0),
                 linked_to_source=True),
            # Player.block -- shield
            dict(image_name="BLOCKSHIELD", alpha=128, scale=(0, 0),
                 linked_to_source=True),
            # Player.loop -- dash cloud
            dict(image_name="DASHCLOUD", direction=None, alpha=64, offset=(0, 0),
                 scale=(0, 0)),
            # NonPlayer._enter_search -- spot/lose player marker
            dict(image_name="SPOTPLAYER", alpha=255, direction=None, offset=(0, 0),
                 scale=(0, 0), linked_to_source=True),
            # Block.BreakableBlock.get_hit -- break burst
            dict(image_name="BREAKBURST", alpha=128, scale=(0, 0)),
            # Block.FallingHazard.loop -- landing burst
            dict(image_name="LANDBURST", direction=None, alpha=128, scale=(0, 0)),
        ]

        signature = inspect.signature(VisualEffect.__init__)
        for call in CALLS:
            try:
                signature.bind_partial(None, None, None, **call)
            except TypeError as error:
                print("VisualEffect rejects " + str(call.get("image_name"))
                      + ": " + str(error), file=sys.stderr)
                sys.exit(1)
        """)


def test_the_real_effects_manager_still_exposes_spawn_and_image_master() -> None:
    _run_or_skip("""
        import inspect, sys
        try:
            from SimpleVFX.SimpleVFX import VisualEffectsManager
        except Exception:
            print("SimpleVFX is not installed")
            sys.exit(77)

        if not hasattr(VisualEffectsManager, "spawn"):
            print("VisualEffectsManager has no spawn()", file=sys.stderr)
            sys.exit(1)

        # Actor/Player/Block all call spawn(effect, time=...)
        signature = inspect.signature(VisualEffectsManager.spawn)
        try:
            signature.bind_partial(None, None, time=0.05)
        except TypeError as error:
            print(f"spawn() rejects the game's call: {error}", file=sys.stderr)
            sys.exit(1)
        """)


def test_the_real_image_direction_has_the_members_the_game_uses() -> None:
    _run_or_skip("""
        import sys
        try:
            from SimpleVFX.SimpleVFX import ImageDirection
        except Exception:
            print("SimpleVFX is not installed")
            sys.exit(77)

        missing = [name for name in ("TOP", "BOTTOM", "LEFT", "RIGHT")
                   if not hasattr(ImageDirection, name)]
        if missing:
            print(f"ImageDirection is missing {missing}", file=sys.stderr)
            sys.exit(1)
        """)


def test_the_real_cv2_exposes_the_video_api_the_cinematics_use() -> None:
    _run_or_skip("""
        import sys
        try:
            import cv2
        except Exception:
            print("cv2 is not installed")
            sys.exit(77)

        missing = [name for name in ("VideoCapture", "cvtColor", "COLOR_BGR2RGB",
                                     "CAP_PROP_FRAME_COUNT", "CAP_PROP_FPS")
                   if not hasattr(cv2, name)]
        if missing:
            print(f"cv2 is missing {missing}", file=sys.stderr)
            sys.exit(1)
        """)


def test_the_real_discordrp_exposes_presence_and_its_error() -> None:
    _run_or_skip("""
        import inspect, sys
        try:
            from discordrp import Presence, PresenceError
        except Exception:
            print("discordrp is not installed")
            sys.exit(77)

        for name in ("set", "clear", "close"):
            if not hasattr(Presence, name):
                print(f"Presence has no {name}()", file=sys.stderr)
                sys.exit(1)

        # DiscordConnection._connect calls Presence(CLIENT_ID)
        try:
            inspect.signature(Presence.__init__).bind_partial(None, "123")
        except TypeError as error:
            print(f"Presence() rejects a bare client id: {error}", file=sys.stderr)
            sys.exit(1)
        """)


def test_the_real_steamworks_exposes_the_user_stats_api() -> None:
    _run_or_skip("""
        import sys
        try:
            from steamworks import STEAMWORKS
            from steamworks.exceptions import SteamException
        except Exception:
            print("steamworks is not installed")
            sys.exit(77)

        if not hasattr(STEAMWORKS, "initialize"):
            print("STEAMWORKS has no initialize()", file=sys.stderr)
            sys.exit(1)
        """)


# --------------------------------------------------------------------------- #
# the stubs themselves
# --------------------------------------------------------------------------- #
def test_the_installed_stubs_are_the_ones_the_suite_provides() -> None:
    """Guards against a real package shadowing the deterministic stand-in."""
    from SimpleVFX.SimpleVFX import VisualEffect
    from support import stubs

    assert VisualEffect is stubs.VisualEffect


def test_stub_state_is_reset_between_tests() -> None:
    from support import stubs

    assert stubs.STEAMWORKS.raise_on_initialize is None
    assert stubs.Presence.raise_on_connect is None
    assert stubs.Presence.raise_on_set is False
