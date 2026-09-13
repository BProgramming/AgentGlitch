"""Tests for ``SaveLoad`` -- the pickle-backed profile and save-game layer.

Every test here runs against a per-test stand-in for ``~/.agentglitch`` (installed by
the autouse fixture in ``conftest.py``), so nothing can read or clobber a real save.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pygame
import pytest

import SaveLoad
from Helpers import DifficultyScale
from Trigger import Trigger


class _StubHUD:
    def __init__(self) -> None:
        self.save_icon_timer = 0.0


@pytest.fixture
def populated_level(level, player, controller, make_objective):
    """A level with a player, a fired trigger and an objective, ready to serialise."""
    trigger = Trigger(level, controller, 0, 0, 96, 96, None, name = "Autosave")
    level.triggers.append(trigger)
    make_objective(col = 5, row = 5)
    level.time = 12.5
    return level


# --------------------------------------------------------------------------- #
# player profile
# --------------------------------------------------------------------------- #
class TestSavePlayerProfile:
    def test_writes_every_setting_the_game_restores(self, controller, level,
                                                    game_data_dir: Path) -> None:
        controller.master_volume["master"] = 0.42
        controller.difficulty              = float(DifficultyScale.HARD)
        controller.player_sprite_selected  = 2
        controller.force_retro             = True

        SaveLoad.save_player_profile(controller, level)

        data = pickle.loads((game_data_dir / "profile.p").read_bytes())
        assert data["level"] == level.name
        assert data["master volume"]["master"] == 0.42
        assert data["difficulty"] == float(DifficultyScale.HARD)
        assert data["selected sprite"] == 2
        assert data["force retro"] is True
        assert data["keyboard layout"] == controller.active_keyboard_layout
        assert data["is fullscreen"] is pygame.display.is_fullscreen()

    def test_without_a_level_it_falls_back_to_the_start_level(self, controller,
                                                              game_data_dir: Path) -> None:
        controller.start_level = "OPENING"
        SaveLoad.save_player_profile(controller, None)
        data = pickle.loads((game_data_dir / "profile.p").read_bytes())
        assert data["level"] == "OPENING"

    def test_without_a_level_an_existing_profile_keeps_its_level(self, controller, level,
                                                                 game_data_dir: Path) -> None:
        """Quitting from the menu must not reset the player's progress marker."""
        SaveLoad.save_player_profile(controller, level)          # level recorded
        controller.start_level = "OPENING"
        SaveLoad.save_player_profile(controller, None)           # quit from the menu
        data = pickle.loads((game_data_dir / "profile.p").read_bytes())
        assert data["level"] == level.name

    def test_overwrites_rather_than_appends(self, controller, level,
                                            game_data_dir: Path) -> None:
        SaveLoad.save_player_profile(controller, level)
        first = (game_data_dir / "profile.p").stat().st_size
        SaveLoad.save_player_profile(controller, level)
        assert (game_data_dir / "profile.p").stat().st_size == first


class TestLoadPlayerProfile:
    def test_no_profile_yields_an_empty_level_name(self, controller) -> None:
        assert SaveLoad.load_player_profile(controller) == ""

    def test_round_trips_the_settings(self, controller, level) -> None:
        controller.master_volume["background"] = 0.3
        controller.difficulty                  = float(DifficultyScale.EASIEST)
        controller.player_sprite_selected      = 2
        controller.set_keyboard_layout("WASD_MOVE")
        SaveLoad.save_player_profile(controller, level)

        fresh = type(controller)(win = controller.win)
        assert SaveLoad.load_player_profile(fresh) == level.name
        assert fresh.master_volume["background"] == 0.3
        assert fresh.difficulty == float(DifficultyScale.EASIEST)
        assert fresh.player_sprite_selected == 2
        assert fresh.active_keyboard_layout == "WASD_MOVE"

    def test_force_retro_is_gated_on_owning_the_dlc(self, controller, level) -> None:
        controller.force_retro = True
        SaveLoad.save_player_profile(controller, level)

        without = type(controller)(win = controller.win)
        without.has_dlc = {}
        SaveLoad.load_player_profile(without)
        assert without.force_retro is False

        owner = type(controller)(win = controller.win)
        owner.has_dlc = {"gumshoe": True}
        SaveLoad.load_player_profile(owner)
        assert owner.force_retro is True

    def test_the_saved_gamepad_layout_is_never_restored(self, controller, level) -> None:
        """Characterisation: ``save_player_profile`` writes it, ``load`` ignores it.

        ``active_gamepad_layout`` is re-detected on connect, so the write is dead
        weight rather than a defect -- but the asymmetry is easy to misread.
        """
        controller.set_gamepad_layout("PS5")
        SaveLoad.save_player_profile(controller, level)
        fresh = type(controller)(win = controller.win)
        SaveLoad.load_player_profile(fresh)
        assert fresh.active_gamepad_layout is None

    def test_the_saved_fullscreen_preference_is_applied(
            self, controller, level, monkeypatch: pytest.MonkeyPatch,
            game_data_dir: Path) -> None:
        """The old condition was ``X and not X``, which is False for every value."""
        toggles: list[int] = []
        monkeypatch.setattr(pygame.display, "toggle_fullscreen",
                            lambda: toggles.append(1))
        monkeypatch.setattr(pygame.display, "is_fullscreen", lambda: False)

        SaveLoad.save_player_profile(controller, level)
        path = game_data_dir / "profile.p"
        data = pickle.loads(path.read_bytes())
        data["is fullscreen"] = True
        path.write_bytes(pickle.dumps(data))

        SaveLoad.load_player_profile(type(controller)(win = controller.win))
        assert toggles == [1]

    def test_a_matching_fullscreen_preference_changes_nothing(
            self, controller, level, monkeypatch: pytest.MonkeyPatch,
            game_data_dir: Path) -> None:
        toggles: list[int] = []
        monkeypatch.setattr(pygame.display, "toggle_fullscreen",
                            lambda: toggles.append(1))
        monkeypatch.setattr(pygame.display, "is_fullscreen", lambda: False)

        SaveLoad.save_player_profile(controller, level)
        SaveLoad.load_player_profile(type(controller)(win = controller.win))
        assert toggles == []

    def test_a_profile_predating_the_fullscreen_key_is_left_alone(
            self, controller, level, monkeypatch: pytest.MonkeyPatch,
            game_data_dir: Path) -> None:
        """``None != False`` would have forced an old profile into fullscreen."""
        toggles: list[int] = []
        monkeypatch.setattr(pygame.display, "toggle_fullscreen",
                            lambda: toggles.append(1))
        monkeypatch.setattr(pygame.display, "is_fullscreen", lambda: False)

        SaveLoad.save_player_profile(controller, level)
        path = game_data_dir / "profile.p"
        data = pickle.loads(path.read_bytes())
        del data["is fullscreen"]
        path.write_bytes(pickle.dumps(data))

        SaveLoad.load_player_profile(type(controller)(win = controller.win))
        assert toggles == []

    def test_a_profile_with_no_level_returns_an_empty_string(self, controller, level,
                                                             game_data_dir: Path) -> None:
        SaveLoad.save_player_profile(controller, level)
        path = game_data_dir / "profile.p"
        data = pickle.loads(path.read_bytes())
        data["level"] = None
        path.write_bytes(pickle.dumps(data))
        assert SaveLoad.load_player_profile(controller) == ""


# --------------------------------------------------------------------------- #
# save game
# --------------------------------------------------------------------------- #
class TestSave:
    def test_no_level_writes_nothing(self, controller, game_data_dir: Path) -> None:
        SaveLoad.save(None, None, controller)
        assert not (game_data_dir / "save.p").exists()

    def test_writes_level_metadata_and_every_entity(self, populated_level, controller,
                                                    game_data_dir: Path) -> None:
        controller.active_objective = "Packet"
        SaveLoad.save(populated_level, None, controller)

        data = pickle.loads((game_data_dir / "save.p").read_bytes())
        assert data["level"] == populated_level.name
        assert data["time"] == 12.5
        assert data["objective"] == "Packet"
        assert populated_level.player.name in data
        assert populated_level.objectives[0].name in data

    def test_triggers_that_never_fired_are_omitted(self, populated_level, controller,
                                                   game_data_dir: Path) -> None:
        # Trigger.save returns None until has_fired, which keeps save files small.
        SaveLoad.save(populated_level, None, controller)
        data = pickle.loads((game_data_dir / "save.p").read_bytes())
        assert "Autosave (0, 0)" not in data

        populated_level.triggers[0].has_fired = True
        SaveLoad.save(populated_level, None, controller)
        data = pickle.loads((game_data_dir / "save.p").read_bytes())
        assert data["Autosave (0, 0)"] == {"has_fired": True}

    def test_collected_objectives_are_saved_even_though_they_left_the_level(
            self, populated_level, controller, game_data_dir: Path) -> None:
        objective = populated_level.objectives.pop()
        populated_level.objectives_collected.append(objective)
        SaveLoad.save(populated_level, None, controller)
        data = pickle.loads((game_data_dir / "save.p").read_bytes())
        assert objective.name in data

    def test_the_hud_save_indicator_is_lit(self, populated_level, controller) -> None:
        hud = _StubHUD()
        SaveLoad.save(populated_level, hud, controller)
        assert hud.save_icon_timer == 1.0


class TestLoadPart1:
    def test_no_save_file_yields_none(self) -> None:
        assert SaveLoad.load_part1() is None

    def test_returns_the_pickled_dict(self, populated_level, controller) -> None:
        SaveLoad.save(populated_level, None, controller)
        data = SaveLoad.load_part1()
        assert data["level"] == populated_level.name

    def test_a_pickled_none_yields_none(self, game_data_dir: Path) -> None:
        (game_data_dir / "save.p").write_bytes(pickle.dumps(None))
        assert SaveLoad.load_part1() is None


class TestLoadPart2:
    def test_missing_data_or_level_reports_failure(self, populated_level,
                                                   controller) -> None:
        assert SaveLoad.load_part2(None, populated_level, controller) is False
        assert SaveLoad.load_part2({}, None, controller) is False

    def test_restores_time_and_active_objective(self, populated_level, controller) -> None:
        assert SaveLoad.load_part2(
            {"time": 7.5, "objective": "Intel"}, populated_level, controller) is True
        assert populated_level.time == 7.5
        assert controller.active_objective == "Intel"

    def test_absent_time_and_objective_reset_to_defaults(self, populated_level,
                                                         controller) -> None:
        populated_level.time        = 99
        controller.active_objective = "Stale"
        SaveLoad.load_part2({}, populated_level, controller)
        assert populated_level.time == 0
        assert controller.active_objective is None

    def test_entities_present_in_the_save_are_restored(self, populated_level,
                                                       controller) -> None:
        objective = populated_level.objectives[0]
        SaveLoad.load_part2({objective.name: {"hp": 40}}, populated_level, controller)
        assert objective.hp == 40

    def test_purgeable_entities_missing_from_the_save_are_removed(
            self, populated_level, controller, make_enemy) -> None:
        """An enemy the player killed before saving must not come back."""
        enemy = make_enemy(col = 3, row = 3)
        assert enemy.purgeable_on_load is True
        SaveLoad.load_part2({}, populated_level, controller)
        assert enemy not in populated_level.enemies

    def test_non_purgeable_entities_missing_from_the_save_survive(
            self, populated_level, controller, make_block) -> None:
        block = make_block(col = 2, row = 7)
        assert block.purgeable_on_load is False
        SaveLoad.load_part2({}, populated_level, controller)
        assert block in populated_level.blocks

    def test_an_already_fired_trigger_is_purged_rather_than_reloaded(
            self, populated_level, controller) -> None:
        trigger = populated_level.triggers[0]
        trigger.has_fired = True
        SaveLoad.load_part2({trigger.name: {"has_fired": True}}, populated_level,
                            controller)
        assert trigger not in populated_level.triggers

    def test_the_purge_is_applied_before_returning(self, populated_level, controller,
                                                   make_enemy) -> None:
        make_enemy(col = 3, row = 3)
        SaveLoad.load_part2({}, populated_level, controller)
        assert all(not bucket for bucket in populated_level.purge_queue.values())


# --------------------------------------------------------------------------- #
# round trip
# --------------------------------------------------------------------------- #
def test_save_then_load_round_trips_the_whole_level(populated_level, controller) -> None:
    objective = populated_level.objectives[0]
    objective.hp = 33
    populated_level.time = 4.25
    controller.active_objective = "Packet"

    SaveLoad.save(populated_level, None, controller)
    populated_level.time = 0
    objective.hp = 100
    controller.active_objective = None

    assert SaveLoad.load_part2(SaveLoad.load_part1(), populated_level, controller) is True
    assert populated_level.time == 4.25
    assert objective.hp == 33
    assert controller.active_objective == "Packet"
