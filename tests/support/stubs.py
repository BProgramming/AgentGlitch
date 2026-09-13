"""Deterministic stand-ins for the third-party packages Agent Glitch imports at module level.

Agent Glitch imports four packages that are either unavailable on a clean checkout
(``SimpleVFX``), platform/SDK dependent (``steamworks``), or that reach out to the
world when touched (``discordrp``, ``cv2``).  Importing the game modules therefore
fails or misbehaves in a bare test environment.

These stubs are installed into ``sys.modules`` *before* any game module is imported,
so ``from SimpleVFX.SimpleVFX import VisualEffect`` and friends resolve to the fakes
below.  They are installed unconditionally -- even when the real package happens to
be present -- so that a test run is identical on a dev box, on CI and on a fresh
clone.  ``tests/test_thirdparty_seams.py`` separately checks the *real* packages'
signatures when they are importable, so unconditional stubbing does not hide drift.

Nothing here tries to emulate the real libraries faithfully; each fake records what
the game asked it to do so tests can assert on the call, and nothing more.
"""

from __future__ import annotations

import sys
import types
from enum import Enum
from typing import Any


# --------------------------------------------------------------------------- #
# SimpleVFX
# --------------------------------------------------------------------------- #
class ImageDirection(Enum):
    """Mirrors SimpleVFX.ImageDirection well enough for the call sites in the game."""

    TOP    = 0
    BOTTOM = 1
    LEFT   = 2
    RIGHT  = 3


class VisualEffect:
    """Records the arguments the game passes when it spawns an effect."""

    def __init__(
            self,
            source:       Any,
            image_master: Any,
            image_name:   str | None = None,
            direction:    Any        = None,
            rotation:     float      = 0.0,
            alpha:        int        = 255,
            offset:       Any        = None,
            scale:        Any        = None,
            linked_to_source: bool   = False,
            **extra:      Any,
    ) -> None:
        self.source           = source
        self.image_master     = image_master
        self.image_name       = image_name
        self.direction        = direction
        self.rotation         = rotation
        self.alpha            = alpha
        self.offset           = offset
        self.scale            = scale
        self.linked_to_source = linked_to_source
        self.extra            = extra

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<VisualEffect {self.image_name!r}>"


class VisualEffectsManager:
    """A no-op manager that records ``spawn`` calls.

    ``tests/support/doubles.py`` wraps this in :class:`RecordingVFXManager`, which is
    what tests actually assert against; this class exists so the stub package exports
    the same three names as the real one.
    """

    def __init__(self, image_master: Any = None) -> None:
        self.image_master = image_master if image_master is not None else {}
        self.spawned: list[tuple[VisualEffect, float]] = []

    def spawn(self, effect: VisualEffect, time: float = 0.0) -> None:
        self.spawned.append((effect, time))

    def loop(self, dtime: float) -> float:
        return 0.0

    def draw(self, win: Any, offset: Any = (0, 0)) -> None:
        return None


# --------------------------------------------------------------------------- #
# steamworks
# --------------------------------------------------------------------------- #
class SteamException(Exception):
    """Stand-in for ``steamworks.exceptions.SteamException``."""


class _UserStats:
    """Achievement/stat book-keeping, in memory."""

    def __init__(self) -> None:
        self.achievements: dict[str, bool] = {}
        self.stored:       int             = 0
        self.request_ok:   bool            = True

    def RequestCurrentStats(self) -> bool:  # noqa: N802 - mirrors the SDK's casing
        return self.request_ok

    def GetAchievement(self, name: str) -> bool:  # noqa: N802
        return self.achievements.get(name, False)

    def SetAchievement(self, name: str) -> bool:  # noqa: N802
        self.achievements[name] = True
        return True

    def StoreStats(self) -> bool:  # noqa: N802
        self.stored += 1
        return True


class _Apps:
    def __init__(self) -> None:
        self.installed_dlc: set[int] = set()

    def IsDLCInstalled(self, app_id: int) -> bool:  # noqa: N802
        return app_id in self.installed_dlc


class STEAMWORKS:  # noqa: N801 - mirrors the SDK's casing
    """In-memory stand-in for the SteamworksPy entry point."""

    #: set by a test to make :meth:`initialize` raise that exception instance
    raise_on_initialize: BaseException | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.UserStats   = _UserStats()
        self.Apps        = _Apps()
        self.initialized = False

    def initialize(self) -> bool:
        if STEAMWORKS.raise_on_initialize is not None:
            raise STEAMWORKS.raise_on_initialize
        self.initialized = True
        return True


# --------------------------------------------------------------------------- #
# discordrp
# --------------------------------------------------------------------------- #
class PresenceError(Exception):
    """Stand-in for ``discordrp.PresenceError``."""


class Presence:
    """Records activity payloads instead of talking to a Discord IPC socket."""

    #: set by a test to make the constructor raise that exception instance
    raise_on_connect: BaseException | None = None
    #: set by a test to make :meth:`set` raise ``PresenceError``
    raise_on_set: bool = False

    def __init__(self, client_id: str) -> None:
        if Presence.raise_on_connect is not None:
            raise Presence.raise_on_connect
        self.client_id = client_id
        self.activities: list[dict] = []
        self.cleared   = 0
        self.closed    = 0

    def set(self, activity: dict) -> None:
        if Presence.raise_on_set:
            raise PresenceError("set failed")
        self.activities.append(dict(activity))

    def clear(self) -> None:
        self.cleared += 1

    def close(self) -> None:
        self.closed += 1


# --------------------------------------------------------------------------- #
# cv2
# --------------------------------------------------------------------------- #
CAP_PROP_FRAME_COUNT = 7
CAP_PROP_FPS         = 5
CAP_PROP_POS_FRAMES  = 1
COLOR_BGR2RGB        = 4


#: frame geometry the fake capture reports
FRAME_SIZE: tuple[int, int] = (64, 48)   # (width, height)


def _make_frame():
    """A frame in the shape ``__play_video__`` expects, or None when numpy is absent.

    ``Cinematic.__play_video__`` feeds frames straight to
    ``pygame.surfarray.make_surface``, which needs a real ndarray -- so without numpy
    the video path simply cannot be driven, and the tests that cover it skip.
    """
    try:
        import numpy
    except ImportError:  # pragma: no cover - depends on the environment
        return None
    width, height = FRAME_SIZE
    return numpy.zeros((height, width, 3), dtype = numpy.uint8)


def frames_are_available() -> bool:
    """Whether the video-playback path can be exercised in this environment."""
    return _make_frame() is not None


class VideoCapture:
    """A video handle that yields a fixed number of blank frames."""

    #: number of frames a freshly opened capture will yield before ``read`` fails
    default_frames: int = 3

    def __init__(self, path: str = "") -> None:
        self.path       = path
        self.frames     = VideoCapture.default_frames
        self._position  = 0
        self._released  = 0
        self._opened    = True

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def get(self, prop: int) -> float:
        if prop == CAP_PROP_FRAME_COUNT:
            return float(self.frames)
        if prop == CAP_PROP_FPS:
            return 30.0
        if prop == CAP_PROP_POS_FRAMES:
            return float(self._position)
        return 0.0

    def set(self, prop: int, value: float) -> bool:
        if prop == CAP_PROP_POS_FRAMES:
            self._position = int(value)
        return True

    def read(self) -> tuple[bool, Any]:
        if self._position >= self.frames:
            return False, None
        self._position += 1
        return True, _make_frame()

    def release(self) -> None:
        self._released += 1
        self._opened = False


def cvtColor(frame: Any, code: int) -> Any:  # noqa: N802
    return frame


def resize(frame: Any, size: Any) -> Any:
    return frame


# --------------------------------------------------------------------------- #
# tkinter (only stubbed when genuinely missing -- some CI images ship without it)
# --------------------------------------------------------------------------- #
class _MessageBox:
    calls: list[dict] = []

    @staticmethod
    def showerror(title: str = "", message: str = "") -> None:
        _MessageBox.calls.append({"title": title, "message": message})


# --------------------------------------------------------------------------- #
# installation
# --------------------------------------------------------------------------- #
def _module(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def install() -> None:
    """Put the stub packages into ``sys.modules``.

    Safe to call more than once.  Must run before the first game module import.
    """
    # SimpleVFX is a package whose module of the same name holds the classes.
    simplevfx_inner = _module(
        "SimpleVFX.SimpleVFX",
        VisualEffect         = VisualEffect,
        ImageDirection       = ImageDirection,
        VisualEffectsManager = VisualEffectsManager,
    )
    simplevfx_pkg = _module("SimpleVFX", SimpleVFX = simplevfx_inner)
    simplevfx_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["SimpleVFX"]          = simplevfx_pkg
    sys.modules["SimpleVFX.SimpleVFX"] = simplevfx_inner

    steamworks_exceptions = _module(
        "steamworks.exceptions",
        SteamException = SteamException,
    )
    steamworks_pkg = _module(
        "steamworks",
        STEAMWORKS = STEAMWORKS,
        exceptions = steamworks_exceptions,
    )
    steamworks_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["steamworks"]            = steamworks_pkg
    sys.modules["steamworks.exceptions"] = steamworks_exceptions

    sys.modules["discordrp"] = _module(
        "discordrp",
        Presence      = Presence,
        PresenceError = PresenceError,
    )

    sys.modules["cv2"] = _module(
        "cv2",
        VideoCapture         = VideoCapture,
        cvtColor             = cvtColor,
        resize               = resize,
        CAP_PROP_FRAME_COUNT = CAP_PROP_FRAME_COUNT,
        CAP_PROP_FPS         = CAP_PROP_FPS,
        CAP_PROP_POS_FRAMES  = CAP_PROP_POS_FRAMES,
        COLOR_BGR2RGB        = COLOR_BGR2RGB,
    )

    try:  # pragma: no cover - depends on the interpreter build
        import tkinter  # noqa: F401
        from tkinter import messagebox  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means "no Tk here"
        tk_pkg = _module("tkinter", messagebox = _module("tkinter.messagebox",
                                                         showerror = _MessageBox.showerror))
        tk_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["tkinter"]            = tk_pkg
        sys.modules["tkinter.messagebox"] = tk_pkg.messagebox  # type: ignore[attr-defined]


def reset() -> None:
    """Return every stub's mutable class-level knob to its default.

    Called between tests by an autouse fixture so one test cannot leak a forced
    failure into the next.
    """
    STEAMWORKS.raise_on_initialize = None
    Presence.raise_on_connect      = None
    Presence.raise_on_set          = False
    VideoCapture.default_frames    = 3
    _MessageBox.calls.clear()
