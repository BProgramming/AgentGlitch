"""The ordered bootstrap that has to run before any Agent Glitch module is imported.

Agent Glitch does real work at import time -- ``Helpers`` creates ``~/.agentglitch``,
``Objective`` loads a PNG in its class body -- so the environment has to be stood up
before the first game import, not in a fixture.  ``conftest.py`` calls :func:`boot`
at module level; ``tests/test_engine_import.py`` calls it from a subprocess with
``open_display = False``, because ``Engine`` opens its own 1920x1080 ``SCALED``
window and SDL cannot build a renderer for that once a plain window already exists.

The sequence is:

1. headless SDL, and ``HOME`` redirected at a throwaway directory so nothing in the
   suite can read or overwrite a real save file, profile or crash log;
2. stand-ins for ``SimpleVFX``, ``steamworks``, ``discordrp`` and ``cv2``;
3. pygame, and (optionally) a display -- ``convert_alpha`` needs one;
4. a synthetic ``Assets/`` tree, with ``Helpers.ASSETS_FOLDER`` repointed at it;
5. replacements for ``Helpers.handle_exception`` and ``Helpers.display_text``, which
   otherwise exit the process and block on ``time.sleep`` respectively.
"""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

TESTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TESTS_DIR.parent


class Environment(NamedTuple):
    """What :func:`boot` set up, for fixtures to hand on to tests."""

    home:        Path
    assets_root: Path
    window:      Any | None


_ENVIRONMENT: Environment | None = None


def boot(open_display: bool = True,
         window_size: tuple[int, int] = (1280, 720)) -> Environment:
    """Run the bootstrap once and return the environment it produced."""
    global _ENVIRONMENT
    if _ENVIRONMENT is not None:
        return _ENVIRONMENT

    # 1. import paths
    for path in (str(TESTS_DIR), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    # 2. headless + isolated HOME
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    home = Path(tempfile.mkdtemp(prefix = "agentglitch-tests-home-"))
    os.environ["HOME"]        = str(home)
    os.environ["USERPROFILE"] = str(home)
    # DiscordConnection._ensure_ipc_socket symlinks inside XDG_RUNTIME_DIR when set.
    os.environ.pop("XDG_RUNTIME_DIR", None)

    # 3. third-party stand-ins
    from support import stubs

    stubs.install()

    # 4. pygame
    import pygame

    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:  # pragma: no cover - a build with no audio at all
        pass

    window = pygame.display.set_mode(window_size) if open_display else None

    # 5. synthetic assets
    from support import assets

    assets_parent = Path(tempfile.mkdtemp(prefix = "agentglitch-tests-assets-"))
    assets_root   = assets.build(assets_parent / "Assets")

    import Helpers

    Helpers.ASSETS_FOLDER = assets_root

    # 6. neutralise the two process-ending helpers
    from support import patches

    patches.install(Helpers)

    atexit.register(shutil.rmtree, home, True)
    atexit.register(shutil.rmtree, assets_parent, True)

    _ENVIRONMENT = Environment(home = home, assets_root = assets_root, window = window)
    return _ENVIRONMENT
