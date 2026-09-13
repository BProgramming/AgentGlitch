"""Session bootstrap for the Agent Glitch test suite.

Everything that has to happen before the first game module is imported lives in
``tests/support/bootstrap.py`` -- headless SDL, a sandboxed ``HOME``, the third-party
stand-ins, the display, the synthetic asset tree and the two ``Helpers`` replacements.
It runs here at module level, which is why the game imports below carry
``noqa: E402`` rather than sitting at the top of the file.

Read ``tests/README.md`` for how the pieces fit together.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import bootstrap  # noqa: E402

ENVIRONMENT  = bootstrap.boot(open_display = True)
SANDBOX_HOME = ENVIRONMENT.home
ASSETS_ROOT  = ENVIRONMENT.assets_root
WINDOW       = ENVIRONMENT.window
WINDOW_SIZE  = WINDOW.get_size()

TESTS_DIR = bootstrap.TESTS_DIR
REPO_ROOT = bootstrap.REPO_ROOT

import pygame    # noqa: E402
import Helpers   # noqa: E402
from support import patches, stubs  # noqa: E402


# --------------------------------------------------------------------------- #
# game imports -- safe from here on
# --------------------------------------------------------------------------- #
from Block import Block, Door, Hazard  # noqa: E402
from Helpers import load_audios  # noqa: E402
from NonPlayer import NonPlayer  # noqa: E402
from Objective import Objective  # noqa: E402
from Player import Player  # noqa: E402
from support.doubles import (  # noqa: E402
    RecordingVFXManager,
    StubController,
    StubGamepad,
    StubLevel,
)


# --------------------------------------------------------------------------- #
# session-wide state
# --------------------------------------------------------------------------- #
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: builds a real Level end to end")
    config.addinivalue_line("markers", "slow: takes noticeably longer than a unit test")


@pytest.fixture(autouse = True)
def _isolate_between_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset every recorder and stub knob, and give each test its own save directory."""
    patches.reset()
    stubs.reset()

    data_dir = SANDBOX_HOME / "game-data"
    shutil.rmtree(data_dir, ignore_errors = True)
    data_dir.mkdir(parents = True, exist_ok = True)

    # SaveLoad did `from Helpers import GAME_DATA_FOLDER`, so it holds its own binding.
    import SaveLoad

    monkeypatch.setattr(Helpers, "GAME_DATA_FOLDER", data_dir, raising = True)
    monkeypatch.setattr(SaveLoad, "GAME_DATA_FOLDER", data_dir, raising = True)

    pygame.event.clear()
    yield
    pygame.event.clear()


# --------------------------------------------------------------------------- #
# fixtures: environment
# --------------------------------------------------------------------------- #
@pytest.fixture(scope = "session")
def window() -> pygame.Surface:
    """The session's dummy display surface."""
    return WINDOW


@pytest.fixture
def surface() -> pygame.Surface:
    """A scratch surface the size of the window, for draw tests."""
    return pygame.Surface(WINDOW_SIZE, pygame.SRCALPHA)


@pytest.fixture
def assets_root() -> Path:
    """Root of the generated asset tree (``Helpers.ASSETS_FOLDER``)."""
    return ASSETS_ROOT


@pytest.fixture
def game_data_dir() -> Path:
    """The per-test stand-in for ``~/.agentglitch``."""
    return Helpers.GAME_DATA_FOLDER


@pytest.fixture
def display_texts() -> list:
    """Every ``display_text`` call made during this test."""
    return patches.display_text_calls


@pytest.fixture
def handled_errors() -> list[str]:
    """Every message passed to ``handle_exception`` during this test."""
    return patches.handled_errors


# --------------------------------------------------------------------------- #
# fixtures: shared asset caches
# --------------------------------------------------------------------------- #
@pytest.fixture
def sprite_master() -> dict:
    """A fresh sprite cache.  Per-test, so retro/normal variants cannot leak."""
    return {}


@pytest.fixture
def image_master() -> dict:
    """A fresh terrain-image cache."""
    return {}


@pytest.fixture(scope = "session")
def _audio_cache() -> dict[str, dict]:
    return {
        group: (load_audios(group) or {})
        for group in ("player", "enemies", "blocks", "messages")
    }


@pytest.fixture
def player_audios(_audio_cache: dict[str, dict]) -> dict:
    return _audio_cache["player"]


@pytest.fixture
def enemy_audios(_audio_cache: dict[str, dict]) -> dict:
    return _audio_cache["enemies"]


@pytest.fixture
def block_audios(_audio_cache: dict[str, dict]) -> dict:
    return _audio_cache["blocks"]


@pytest.fixture
def message_audios(_audio_cache: dict[str, dict]) -> dict:
    return _audio_cache["messages"]


# --------------------------------------------------------------------------- #
# fixtures: core objects
# --------------------------------------------------------------------------- #
@pytest.fixture
def controller(window: pygame.Surface) -> StubController:
    return StubController(win = window)


@pytest.fixture
def level(controller: StubController) -> StubLevel:
    """An empty 10x8 level (960 x 768 px at the default block size) with no player yet."""
    lvl = StubLevel(controller)
    controller.level = lvl
    return lvl


@pytest.fixture
def retro_level(controller: StubController) -> StubLevel:
    lvl = StubLevel(controller, retro = True)
    controller.level = lvl
    return lvl


@pytest.fixture
def vfx(level: StubLevel) -> RecordingVFXManager:
    """The level's visual-effects recorder."""
    return level.visual_effects_manager


@pytest.fixture
def make_player(level: StubLevel, controller: StubController,
                sprite_master: dict, player_audios: dict):
    """Factory: place a ``Player`` in the level at a tile coordinate."""

    def _make(col: int = 1, row: int = 1, difficulty: float = 1.0,
              sprite: str = "Player1", retro_sprite: str | None = "RetroPlayer1",
              **kwargs) -> Player:
        player = Player(
            level, controller,
            col * level.block_size, row * level.block_size,
            sprite_master, player_audios, difficulty, level.block_size,
            sprite = sprite, retro_sprite = retro_sprite, **kwargs,
        )
        level.set_player(player)
        return player

    return _make


@pytest.fixture
def player(make_player) -> Player:
    """A player at tile (1, 1) on medium difficulty."""
    return make_player()


@pytest.fixture
def make_enemy(level: StubLevel, controller: StubController,
               sprite_master: dict, enemy_audios: dict):
    """Factory: place a ``NonPlayer`` in the level at a tile coordinate."""

    def _make(col: int = 4, row: int = 1, difficulty: float = 1.0,
              sprite: str = "TestAgent", register: bool = True, **kwargs) -> NonPlayer:
        enemy = NonPlayer(
            level, controller,
            col * level.block_size, row * level.block_size,
            sprite_master, enemy_audios, difficulty, level.block_size,
            sprite = sprite, **kwargs,
        )
        if register:
            level.enemies.append(enemy)
            level.enemies_available = len(level.enemies)
        return enemy

    return _make


@pytest.fixture
def make_block(level: StubLevel, controller: StubController, image_master: dict,
               block_audios: dict):
    """Factory: place a plain ``Block`` and file it into ``static_blocks``."""

    def _make(col: int = 0, row: int = 7, is_stacked: bool = False,
              place: bool = True, **kwargs) -> Block:
        block = Block(
            level, controller,
            col * level.block_size, row * level.block_size,
            level.block_size, level.block_size,
            image_master, block_audios, is_stacked, **kwargs,
        )
        if place:
            level.place_static(block, col, row)
        return block

    return _make


@pytest.fixture
def floor(make_block, level: StubLevel):
    """A solid row of blocks along the bottom of the level."""
    row = len(level.static_blocks) - 1
    return [make_block(col = col, row = row) for col in range(len(level.static_blocks[0]))]


@pytest.fixture
def make_hazard(level: StubLevel, controller: StubController, image_master: dict,
                sprite_master: dict, block_audios: dict):
    """Factory: place a ``Hazard``."""

    def _make(col: int = 3, row: int = 6, difficulty: float = 1.0,
              hit_sides: str = "UDLR", sprite: str | None = "TestAnim",
              register: bool = True, **kwargs) -> Hazard:
        hazard = Hazard(
            level, controller,
            col * level.block_size, row * level.block_size,
            level.block_size, level.block_size,
            image_master, sprite_master, block_audios, difficulty,
            hit_sides = hit_sides, sprite = sprite, **kwargs,
        )
        if register:
            level.hazards.append(hazard)
        return hazard

    return _make


@pytest.fixture
def make_objective(level: StubLevel, controller: StubController,
                   sprite_master: dict, block_audios: dict):
    """Factory: place an ``Objective``."""

    def _make(col: int = 5, row: int = 6, is_active: bool = True,
              sprite: str | None = "TestAnim", register: bool = True,
              **kwargs) -> Objective:
        objective = Objective(
            level, controller,
            col * level.block_size, row * level.block_size,
            level.block_size, level.block_size,
            sprite_master, block_audios, is_active = is_active, sprite = sprite,
            **kwargs,
        )
        if register:
            level.objectives.append(objective)
            level.objectives_available = len(level.objectives)
        return objective

    return _make


@pytest.fixture
def make_door(level: StubLevel, controller: StubController, image_master: dict,
              block_audios: dict):
    """Factory: place a ``Door`` and file it into the level's door index."""

    def _make(col: int = 6, row: int = 6, is_locked: bool = False,
              place: bool = True, **kwargs) -> Door:
        door = Door(
            level, controller,
            col * level.block_size, row * level.block_size,
            level.block_size, level.block_size,
            image_master, block_audios, True, is_locked = is_locked, **kwargs,
        )
        if place:
            level.add_door(door, col)
        return door

    return _make


@pytest.fixture
def gamepad() -> StubGamepad:
    return StubGamepad()
