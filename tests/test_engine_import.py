"""Import smoke test for ``Engine`` -- the module that wires the whole game together.

``Engine`` does real work at import time: it starts pygame, opens a 1920x1080 window,
connects to Steam and Discord, and imports every gameplay module in a specific order
to dodge the circular-import problems the codebase has had before.  Importing it into
the test session would replace the shared display and disturb every other test, so it
is imported in a subprocess instead.

This is the only test that exercises ``Engine`` at all: ``main()`` is a single
blocking game loop with no seam to drive it from.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent


# The same bootstrap the pytest session runs -- stubs, sandboxed HOME, synthetic
# assets, patched Helpers -- but WITHOUT opening a display.  Engine opens its own
# 1920x1080 SCALED window, and SDL cannot build a renderer for a SCALED mode once a
# plain window already exists in the process.
def _bootstrap(open_display: bool) -> str:
    """The same bootstrap the pytest session runs: stubs, sandboxed HOME, synthetic
    assets, patched Helpers.

    ``open_display`` must be False for the Engine probe -- Engine opens its own
    1920x1080 ``SCALED`` window, and SDL cannot build a renderer for a SCALED mode
    once a plain window already exists in the process.  Every other probe needs a
    display, because ``Objective`` calls ``convert_alpha`` in its class body.
    """
    return (
        "import sys\n"
        f"sys.path.insert(0, {str(TESTS_DIR)!r})\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        "from support import bootstrap\n"
        f"bootstrap.boot(open_display={open_display!r})\n"
    )


def _run(body: str, open_display: bool = True) -> subprocess.CompletedProcess:
    source = _bootstrap(open_display) + textwrap.dedent(body) + '\nprint("OK")\n'
    return subprocess.run([sys.executable, "-c", source], capture_output = True,
                          text = True, timeout = 180, cwd = str(REPO_ROOT))


def _import_engine(extra: str = "") -> subprocess.CompletedProcess:
    """Import Engine in a clean interpreter, with the test harness bootstrapped first."""
    return _run("import Engine\n" + extra, open_display = False)


@pytest.fixture(scope = "module")
def engine_import() -> subprocess.CompletedProcess:
    return _import_engine(
        "assert callable(Engine.main)\n"
        "assert Engine.FPS_TARGET > 0\n"
        "assert (Engine.WIDTH, Engine.HEIGHT) == (1920, 1080)\n"
        "assert Engine.WINDOW is not None\n"
        "assert Engine.steamworks is not None\n"
        "assert Engine.discord is not None\n"
    )


@pytest.mark.slow
class TestEngineImport:
    def test_the_module_imports_cleanly(self, engine_import) -> None:
        assert engine_import.returncode == 0, engine_import.stderr

    def test_no_circular_import_is_reported(self, engine_import) -> None:
        assert "circular import" not in engine_import.stderr.lower()
        assert "partially initialized module" not in engine_import.stderr.lower()

    def test_the_window_and_services_are_wired_up(self, engine_import) -> None:
        assert "OK" in engine_import.stdout


@pytest.mark.slow
def test_the_gameplay_modules_can_be_imported_in_any_order() -> None:
    """Guards the deferred-import fixes that broke the EntityFactory/Trigger cycle.

    Importing ``Trigger`` first -- before ``EntityFactory``, ``NonPlayer`` or
    ``Objective`` -- is the order that used to fail.
    """
    result = _run("""
        import Trigger
        import EntityFactory
        import NonPlayer
        import Objective
        import Level
        import Camera
        import Boss
        """)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
