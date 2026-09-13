"""Test doubles for the three objects every entity in the game reaches through.

Almost nothing in Agent Glitch can be constructed in isolation: an ``Entity`` wants a
``Level`` and a ``Controller``, a ``Level`` wants a fully built entity graph, and a
``Controller`` wants menus, selectors and the whole asset tree.  Rather than mock all
of that out, this module provides:

* :class:`StubController` -- a plain object carrying the attributes entities read,
  which records the calls they make back into it.  It borrows the real key/button
  layout tables from ``Controller`` so tests cannot drift from the shipped bindings.
* :class:`StubLevel` -- a real ``Level`` *subclass* whose ``__init__`` populates the
  fields directly instead of parsing a grid.  Every method under test
  (``get_entities_in_range``, ``purge``, ``entities``, ``formatted_time``,
  ``award_achievements``, ...) is therefore the real implementation, not a fake.
* :class:`RecordingVFXManager` -- stands in for ``SimpleVFX.VisualEffectsManager``
  and keeps every spawned effect so VFX side effects can be asserted on.

The integration tests in ``tests/test_integration_level.py`` build a genuine ``Level``
from generated ``.agl``/``.agd`` data instead; these doubles are for unit tests, where
constructing a whole level per case would be both slow and imprecise.
"""

from __future__ import annotations

from typing import Any

import pygame

from Controller import Controller as RealController
from Helpers import DifficultyScale
from Level import Level


# --------------------------------------------------------------------------- #
# visual effects
# --------------------------------------------------------------------------- #
class RecordingVFXManager:
    """Stands in for ``SimpleVFX.VisualEffectsManager`` and records every spawn."""

    def __init__(self) -> None:
        self.image_master: dict[str, Any] = {}
        self.spawned: list[tuple[Any, float]] = []
        self.draw_calls: int = 0

    def spawn(self, effect: Any, time: float = 0.0) -> None:
        self.spawned.append((effect, time))

    def loop(self, dtime: float) -> float:
        return 0.0

    def draw(self, win: pygame.Surface, offset: tuple[float, float] = (0, 0)) -> None:
        self.draw_calls += 1

    # -- assertions helpers ------------------------------------------------- #
    @property
    def image_names(self) -> list[str]:
        """The ``image_name`` of every spawned effect, in spawn order."""
        return [getattr(effect, "image_name", None) for effect, _ in self.spawned]

    def spawned_named(self, image_name: str) -> list[Any]:
        return [effect for effect, _ in self.spawned
                if getattr(effect, "image_name", None) == image_name]

    def clear(self) -> None:
        self.spawned.clear()
        self.draw_calls = 0


# --------------------------------------------------------------------------- #
# gamepad
# --------------------------------------------------------------------------- #
class StubGamepad:
    """A controller handle that records rumble and reports scripted axis/button state."""

    def __init__(self, instance_id: int = 1) -> None:
        self.instance_id = instance_id
        self.rumbles: list[tuple[float, float, int]] = []
        self.axes:    dict[int, float] = {}
        self.buttons: dict[int, bool]  = {}
        self.quit_calls: int  = 0
        self.init_calls: int  = 0
        self.name: str        = "Stub Gamepad"

    def init(self) -> None:
        self.init_calls += 1

    def quit(self) -> None:
        self.quit_calls += 1

    def get_id(self) -> int:
        return self.instance_id

    def rumble(self, low: float, high: float, duration: int) -> bool:
        self.rumbles.append((low, high, duration))
        return True

    def stop_rumble(self) -> None:
        return None

    def get_axis(self, axis: int) -> float:
        return self.axes.get(axis, 0.0)

    def get_button(self, button: int) -> bool:
        return self.buttons.get(button, False)


# --------------------------------------------------------------------------- #
# controller
# --------------------------------------------------------------------------- #
class StubController:
    """The attribute surface of ``Controller`` that entities actually touch.

    Layout tables are the real class attributes, so a binding change in
    ``Controller`` shows up here immediately.
    """

    KEYBOARD_LAYOUTS  = RealController.KEYBOARD_LAYOUTS
    GAMEPAD_LAYOUTS   = RealController.GAMEPAD_LAYOUTS
    JOYSTICK_TOLERANCE = RealController.JOYSTICK_TOLERANCE

    def __init__(
            self,
            win:        pygame.Surface | None = None,
            difficulty: float                 = float(DifficultyScale.MEDIUM),
            steamworks: Any                   = None,
            discord:    Any                   = None,
    ) -> None:
        self.win = win if win is not None else pygame.display.get_surface()

        self.master_volume: dict[str, float] = {
            "master": 1.0, "background": 1.0, "player": 1.0,
            "non-player": 1.0, "cinematics": 1.0,
        }
        self.difficulty              = difficulty
        self.steamworks              = steamworks
        self.discord                 = discord
        self.gamepad: Any            = None
        self.hud: Any                = None
        self.level: Any              = None

        self.force_retro             = False
        self.player_sprite_selected  = 1
        self.start_level: str | None = "TESTLEVEL"
        self.next_level: str | None  = None
        self.active_objective: str | None = None
        self.should_store_steam_stats = False
        self.should_scroll_to_point: Any = None
        self.should_hot_swap_level   = False
        self.goto_load = self.goto_main = self.goto_restart = False
        self.has_dlc: dict[str, bool] = {}

        self.active_keyboard_layout  = "ARROW_MOVE"
        self.active_gamepad_layout: str | None = None

        self.music: list | None      = None
        self.music_index             = 0

        # -- recorders ------------------------------------------------------ #
        self.activate_objective_calls: list[tuple[str | None, bool, bool]] = []
        self.queued_track_lists: list[list | None] = []
        self.save_calls               = 0
        self.save_profile_calls       = 0
        self.quit_calls               = 0

    # -- the bits of Controller's behaviour entities depend on --------------- #
    @property
    def retro(self) -> bool:
        return self.force_retro or (self.level is not None and self.level.retro)

    def activate_objective(self, name: str | None, value: bool, popup: bool = True) -> None:
        self.activate_objective_calls.append((name, value, popup))
        self.active_objective = name

    def save(self) -> None:
        self.save_calls += 1

    def save_player_profile(self) -> None:
        self.save_profile_calls += 1

    def quit(self) -> None:
        self.quit_calls += 1

    def queue_track_list(self, music: list | None = None) -> None:
        self.queued_track_lists.append(music)
        self.music = music if music else (self.level.music if self.level else None)

    def set_keyboard_layout(self, name: str) -> None:
        self.active_keyboard_layout = name

    def set_gamepad_layout(self, name: str) -> None:
        self.active_gamepad_layout = None if name == "NONE" else name

    def handle_pause_unpause(self, key: int) -> float:
        return 0.0

    def handle_any_key(self) -> bool:
        return False


# --------------------------------------------------------------------------- #
# level
# --------------------------------------------------------------------------- #
class StubLevel(Level):
    """A ``Level`` with its entity graph injected instead of parsed from a grid.

    Deliberately a subclass: every ``Level`` method a test calls is the shipped one.
    Only ``__init__`` is replaced, and ``Level.__init__`` is never invoked.
    """

    def __init__(  # noqa: PLR0913 - mirrors the fields Level.__init__ sets
            self,
            controller:      Any,
            name:            str   = "TESTLEVEL",
            block_size:      int   = Level.BLOCK_SIZE,
            width_blocks:    int   = 10,
            height_blocks:   int   = 8,
            retro:           bool  = False,
    ) -> None:
        self.name         = name.upper()
        self.display_name = self.name
        self.controller   = controller
        self.time         = 0.0
        self.block_size   = block_size
        self._retro       = retro
        self.can_glitch   = False

        self.achievements: dict[str, str] = {}
        self.purge_queue = {
            "triggers": set(), "hazards": set(), "blocks": set(),
            "doors": set(), "enemies": set(), "objectives": set(),
        }

        self.visual_effects_manager = RecordingVFXManager()
        self.background       = "Test.png"
        self.foreground       = None
        self.start_cinematic  = [None]
        self.end_cinematic    = [None]
        self.start_message    = None
        self.end_message      = None
        self.music            = None
        self.cinematics       = None
        self.particle_effects = []

        self.level_bounds = ((0, 0), (width_blocks * block_size, height_blocks * block_size))

        self._player: Any = None
        self.triggers:   list = []
        self.blocks:     list = []
        self.dynamic_blocks: list = []
        self.doors:      dict = {}
        self.hazards:    list = []
        self.falling_hazards: dict = {}
        self.enemies:    list = []
        self.objectives: list = []
        self.objectives_collected: list = []

        self.static_blocks: list[list] = [
            [None] * width_blocks for _ in range(height_blocks)
        ]

        self.target_time          = 0
        self.default_objective    = None
        self.objectives_available = 0
        self.enemies_available    = 0
        self.boss_hp_pct          = None
        self.hot_swap_level       = None

    # -- convenience used by the unit tests --------------------------------- #
    def set_player(self, player: Any) -> Any:
        """Attach a player and return it."""
        self._player = player
        return player

    def place_static(self, block: Any, col: int, row: int) -> Any:
        """File a block into ``static_blocks[row][col]`` and ``blocks``, like build_level."""
        self.static_blocks[row][col] = block
        self.blocks.append(block)
        return block

    def add_door(self, door: Any, col: int) -> Any:
        self.doors.setdefault(col, []).append(door)
        self.blocks.append(door)
        return door
