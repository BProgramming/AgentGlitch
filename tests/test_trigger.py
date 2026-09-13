"""Tests for the ``Trigger`` family.

Every subclass follows the same shape -- refuse to run twice when ``fire_once`` is
set, stamp ``has_fired``, do one thing, and return the wall-clock cost of doing it so
the engine can subtract it from the frame's delta time.  The shared contract is
covered once by parametrised tests; each subclass then gets tests for its own effect.
"""

from __future__ import annotations

import pygame
import pytest

from Block import Block, Hazard
from NonPlayer import NonPlayer
from Trigger import (
    AchievementTrigger,
    CameraToPlayerTrigger,
    CameraToPointTrigger,
    ChangeLevelTrigger,
    CinematicTrigger,
    DiscordStatusTrigger,
    ObjectiveTrigger,
    PropertyTrigger,
    RevertTrigger,
    SaveTrigger,
    SoundTrigger,
    SpawnTrigger,
    SwapLevelTrigger,
    TextTrigger,
    Trigger,
)
from support import stubs
from support.assets import OBJECT_DICT
from support.patches import HandledError


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
class _DiscordRecorder:
    def __init__(self) -> None:
        self.statuses: list[tuple[str, str]] = []

    def set_status(self, details: str = "", state: str = "") -> None:
        self.statuses.append((details, state))


def _make(cls, level, controller, value, **kwargs):
    return cls(level, controller, 0, 0, 96, 96, value, **kwargs)


# --------------------------------------------------------------------------- #
# base class
# --------------------------------------------------------------------------- #
class TestBaseTrigger:
    def test_defaults_to_firing_once(self, level, controller) -> None:
        trigger = _make(Trigger, level, controller, None)
        assert trigger.fire_once is True
        assert trigger.has_fired is False

    def test_the_raw_value_is_kept_untouched_by_default(self, level, controller) -> None:
        assert _make(Trigger, level, controller, {"a": 1}).value == {"a": 1}

    def test_collide_does_nothing_on_the_base_class(self, level, controller,
                                                    player) -> None:
        trigger = _make(Trigger, level, controller, None)
        assert trigger.collide(player) == 0.0
        assert trigger.has_fired is False

    def test_draw_is_a_no_op(self, level, controller, surface) -> None:
        _make(Trigger, level, controller, None).draw(surface, 0, 0, {})
        assert surface.get_at((0, 0)) == pygame.Color(0, 0, 0, 0)

    def test_unpack_input_splits_a_packed_dict(self) -> None:
        assert Trigger.__unpack_input__({"ref": "R", "input": "I"}) == ("R", "I")

    def test_save_is_omitted_until_the_trigger_fires(self, level, controller) -> None:
        trigger = _make(SaveTrigger, level, controller, None)
        assert trigger.save() is None
        trigger.has_fired = True
        assert trigger.save() == {trigger.name: {"has_fired": True}}

    def test_load_restores_the_fired_flag(self, level, controller) -> None:
        trigger = _make(Trigger, level, controller, None)
        trigger.load({"has_fired": True})
        assert trigger.has_fired is True


# --------------------------------------------------------------------------- #
# shared fire-once contract
# --------------------------------------------------------------------------- #
#: (class, value) pairs whose ``collide`` needs nothing beyond a level + controller
SIMPLE_TRIGGERS = [
    (AchievementTrigger,   "ACH_TEST"),
    (CameraToPlayerTrigger, None),
    (ChangeLevelTrigger,   "next"),
    (PropertyTrigger,      None),
    (SaveTrigger,          None),
    (SwapLevelTrigger,     None),
]


@pytest.mark.parametrize("cls, value", SIMPLE_TRIGGERS,
                         ids = [c.__name__ for c, _ in SIMPLE_TRIGGERS])
class TestFireOnceContract:
    def test_firing_stamps_has_fired(self, cls, value, level, controller, player) -> None:
        trigger = _make(cls, level, controller, value)
        trigger.collide(player)
        assert trigger.has_fired is True

    def test_a_fire_once_trigger_refuses_to_run_twice(self, cls, value, level,
                                                      controller, player) -> None:
        trigger = _make(cls, level, controller, value)
        trigger.collide(player)
        assert trigger.collide(player) == 0.0

    def test_a_repeatable_trigger_runs_every_time(self, cls, value, level, controller,
                                                  player) -> None:
        trigger = _make(cls, level, controller, value, fire_once = False)
        trigger.collide(player)
        second = trigger.collide(player)
        assert second >= 0.0

    def test_collide_returns_a_non_negative_time_offset(self, cls, value, level,
                                                        controller, player) -> None:
        assert _make(cls, level, controller, value).collide(player) >= 0.0


# --------------------------------------------------------------------------- #
# AchievementTrigger
# --------------------------------------------------------------------------- #
class TestAchievementTrigger:
    def test_unlocks_the_achievement_and_asks_for_a_stat_flush(self, level,
                                                               controller, player) -> None:
        controller.steamworks = stubs.STEAMWORKS()
        _make(AchievementTrigger, level, controller, "ACH_SNEAK").collide(player)
        assert controller.steamworks.UserStats.GetAchievement("ACH_SNEAK")
        assert controller.should_store_steam_stats is True

    def test_an_already_unlocked_achievement_is_left_alone(self, level, controller,
                                                           player) -> None:
        controller.steamworks = stubs.STEAMWORKS()
        controller.steamworks.UserStats.achievements["ACH_SNEAK"] = True
        _make(AchievementTrigger, level, controller, "ACH_SNEAK").collide(player)
        assert controller.should_store_steam_stats is False

    def test_without_steam_it_still_fires_but_does_nothing(self, level, controller,
                                                           player) -> None:
        controller.steamworks = None
        trigger = _make(AchievementTrigger, level, controller, "ACH_SNEAK")
        trigger.collide(player)
        assert trigger.has_fired is True
        assert controller.should_store_steam_stats is False


# --------------------------------------------------------------------------- #
# camera triggers
# --------------------------------------------------------------------------- #
class TestCameraTriggers:
    def test_to_player_clears_any_fixed_camera_target(self, level, controller,
                                                      player) -> None:
        controller.should_scroll_to_point = {"coords": (0, 0), "time": 1.0}
        _make(CameraToPlayerTrigger, level, controller, None).collide(player)
        assert controller.should_scroll_to_point is None

    def test_to_point_converts_tile_coordinates_to_pixels(self, level, controller) -> None:
        trigger = _make(CameraToPointTrigger, level, controller,
                        {"ref": 96, "input": {"coords": "3 4", "time": 2.5}})
        assert trigger.value == {"coords": (3 * 96, 4 * 96), "time": 2.5}

    def test_to_point_defaults_the_dwell_time_to_zero(self, level, controller) -> None:
        trigger = _make(CameraToPointTrigger, level, controller,
                        {"ref": 96, "input": {"coords": "1 1"}})
        assert trigger.value["time"] == 0.0

    def test_to_point_hands_the_target_to_the_controller(self, level, controller,
                                                         player) -> None:
        trigger = _make(CameraToPointTrigger, level, controller,
                        {"ref": 96, "input": {"coords": "2 2"}})
        trigger.collide(player)
        assert controller.should_scroll_to_point == trigger.value


# --------------------------------------------------------------------------- #
# ChangeLevelTrigger
# --------------------------------------------------------------------------- #
class TestChangeLevelTrigger:
    def test_queues_the_named_level_uppercased(self, level, controller, player) -> None:
        _make(ChangeLevelTrigger, level, controller, "rooftop").collide(player)
        assert controller.next_level == "ROOFTOP"

    def test_a_non_string_value_queues_nothing(self, level, controller, player) -> None:
        _make(ChangeLevelTrigger, level, controller, 7).collide(player)
        assert controller.next_level is None


# --------------------------------------------------------------------------- #
# CinematicTrigger
# --------------------------------------------------------------------------- #
class TestCinematicTrigger:
    def test_a_level_with_no_cinematics_is_a_safe_no_op(self, level, controller,
                                                        player) -> None:
        level.cinematics = None
        trigger = _make(CinematicTrigger, level, controller, "intro")
        assert trigger.collide(player) >= 0.0

    def test_queues_the_named_cinematic(self, level, controller, player) -> None:
        from Cinematic import CinematicsManager

        level.cinematics = CinematicsManager(
            {"name": "intro", "type": "slide", "file": "slide.png"}, controller)
        _make(CinematicTrigger, level, controller, "intro").collide(player)
        assert level.cinematics.queued == ["intro"]

    def test_an_unknown_cinematic_name_queues_nothing(self, level, controller,
                                                      player) -> None:
        from Cinematic import CinematicsManager

        level.cinematics = CinematicsManager(
            {"name": "intro", "type": "slide", "file": "slide.png"}, controller)
        _make(CinematicTrigger, level, controller, "missing").collide(player)
        assert level.cinematics.queued == []


# --------------------------------------------------------------------------- #
# DiscordStatusTrigger
# --------------------------------------------------------------------------- #
class TestDiscordStatusTrigger:
    def test_load_input_keeps_state_and_details(self, level, controller) -> None:
        trigger = _make(DiscordStatusTrigger, level, controller,
                        {"state": "Sneaking", "details": "On a mission:"})
        assert trigger.value == {"state": "Sneaking", "details": "On a mission:"}

    def test_load_input_defaults_missing_fields_to_empty_strings(self, level,
                                                                 controller) -> None:
        assert _make(DiscordStatusTrigger, level, controller, {}).value == {
            "state": "", "details": ""}

    def test_pushes_the_status_when_discord_is_connected(self, level, controller,
                                                         player) -> None:
        controller.discord = _DiscordRecorder()
        _make(DiscordStatusTrigger, level, controller,
              {"state": "Sneaking", "details": "Mission:"}).collide(player)
        assert controller.discord.statuses == [("Mission:", "Sneaking")]

    def test_without_discord_it_is_a_no_op(self, level, controller, player) -> None:
        controller.discord = None
        trigger = _make(DiscordStatusTrigger, level, controller, {"state": "x"})
        assert trigger.collide(player) >= 0.0


# --------------------------------------------------------------------------- #
# ObjectiveTrigger
# --------------------------------------------------------------------------- #
class TestObjectiveTrigger:
    def test_load_input_narrows_to_target_and_value(self, level, controller) -> None:
        trigger = _make(ObjectiveTrigger, level, controller,
                        {"target": "Packet", "value": True, "extra": "ignored"})
        assert trigger.value == {"target": "Packet", "value": True}

    def test_activates_the_named_objective(self, level, controller, player) -> None:
        _make(ObjectiveTrigger, level, controller,
              {"target": "Packet", "value": True}).collide(player)
        assert controller.activate_objective_calls == [("Packet", True, True)]

    def test_a_non_boolean_value_is_rejected(self, level, controller, player) -> None:
        _make(ObjectiveTrigger, level, controller,
              {"target": "Packet", "value": "yes"}).collide(player)
        assert controller.activate_objective_calls == []

    def test_a_non_string_target_is_rejected(self, level, controller, player) -> None:
        _make(ObjectiveTrigger, level, controller,
              {"target": 3, "value": True}).collide(player)
        assert controller.activate_objective_calls == []


# --------------------------------------------------------------------------- #
# PropertyTrigger
# --------------------------------------------------------------------------- #
class TestPropertyTrigger:
    def test_applies_the_property_change_to_matching_entities(self, level, controller,
                                                              player, make_enemy) -> None:
        enemy = make_enemy()
        _make(PropertyTrigger, level, controller,
              {"target": enemy.name.split(" ")[0], "property": "hp", "value": 5}
              ).collide(player)
        assert enemy.hp == 5

    def test_can_grant_an_ability_to_the_player(self, level, controller, player) -> None:
        _make(PropertyTrigger, level, controller,
              {"target": "Player", "property": "can_double_jump", "value": True}
              ).collide(player)
        assert player.abilities["can_double_jump"] is True

    def test_a_null_specification_is_a_safe_no_op(self, level, controller, player) -> None:
        assert _make(PropertyTrigger, level, controller, None).collide(player) >= 0.0


# --------------------------------------------------------------------------- #
# RevertTrigger
# --------------------------------------------------------------------------- #
class TestRevertTrigger:
    def test_reverts_the_player(self, level, controller, player) -> None:
        player.cached_x, player.cached_y = 500, 600
        player.rect.topleft = (0, 0)
        _make(RevertTrigger, level, controller, None).collide(player)
        assert player.rect.topleft == (500, 600)


# --------------------------------------------------------------------------- #
# SaveTrigger
# --------------------------------------------------------------------------- #
class TestSaveTrigger:
    def test_saves_the_game_and_the_profile(self, level, controller, player) -> None:
        _make(SaveTrigger, level, controller, None).collide(player)
        assert controller.save_calls == 1
        assert controller.save_profile_calls == 1


# --------------------------------------------------------------------------- #
# SoundTrigger
# --------------------------------------------------------------------------- #
class TestSoundTrigger:
    def test_loads_a_wav_from_the_triggers_folder(self, level, controller) -> None:
        trigger = _make(SoundTrigger, level, controller, "beep.wav")
        assert isinstance(trigger.value, pygame.mixer.Sound)

    @pytest.mark.parametrize("value", ["missing.wav", "notes.txt", "ab", ""])
    def test_anything_that_is_not_a_playable_file_loads_as_none(self, level, controller,
                                                                value) -> None:
        assert _make(SoundTrigger, level, controller, value).value is None

    def test_plays_the_sound_when_it_fires(self, level, controller, player,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
        played: list = []

        class _Channel:
            def play(self, sound):
                played.append(sound)

        monkeypatch.setattr(pygame.mixer, "find_channel", lambda force = False: _Channel())
        trigger = _make(SoundTrigger, level, controller, "beep.wav")
        trigger.collide(player)
        assert played == [trigger.value]

    def test_a_missing_sound_fires_without_playing(self, level, controller, player) -> None:
        trigger = _make(SoundTrigger, level, controller, "missing.wav")
        assert trigger.collide(player) >= 0.0
        assert trigger.has_fired is True


# --------------------------------------------------------------------------- #
# SpawnTrigger
# --------------------------------------------------------------------------- #
class TestSpawnTrigger:
    @pytest.fixture
    def refs(self, sprite_master, image_master, enemy_audios, block_audios,
             message_audios) -> dict:
        return {
            "objects_dict":   OBJECT_DICT,
            "sprite_master":  sprite_master,
            "image_master":   image_master,
            "enemy_audios":   enemy_audios,
            "block_audios":   block_audios,
            "message_audios": message_audios,
            "block_size":     96,
        }

    def _spawner(self, level, controller, refs, token: str, coords: str = "2 3",
                 **kwargs) -> SpawnTrigger:
        return _make(SpawnTrigger, level, controller,
                     {"ref": refs, "input": {"name": token, "coords": coords}}, **kwargs)

    def test_the_recipe_is_recorded_and_nothing_is_built_until_it_fires(
            self, level, controller, refs, player) -> None:
        trigger = self._spawner(level, controller, refs, "E")
        assert trigger.value["element"] == "E"
        assert level.enemies == []

    def test_an_unknown_token_records_no_recipe(self, level, controller,
                                                refs) -> None:
        assert self._spawner(level, controller, refs, "NOPE").value is None

    def test_an_unknown_entity_type_spawns_nothing(self, level, controller, refs,
                                                   player) -> None:
        trigger = self._spawner(level, controller, refs, "?")
        before  = len(level.entities)
        trigger.collide(player)
        assert len(level.entities) == before

    def test_firing_files_an_enemy_and_bumps_the_census(self, level, controller,
                                                        refs, player) -> None:
        trigger = self._spawner(level, controller, refs, "E")
        before  = level.enemies_available
        trigger.collide(player)
        assert len(level.enemies) == 1
        assert isinstance(level.enemies[0], NonPlayer)
        assert level.enemies_available == before + 1

    def test_firing_files_an_objective_and_bumps_the_census(self, level, controller,
                                                            refs, player) -> None:
        trigger = self._spawner(level, controller, refs, "O")
        before  = level.objectives_available
        trigger.collide(player)
        assert len(level.objectives) == 1
        assert level.objectives_available == before + 1

    def test_firing_files_a_hazard(self, level, controller, refs, player) -> None:
        self._spawner(level, controller, refs, "H").collide(player)
        assert len(level.hazards) == 1
        assert isinstance(level.hazards[0], Hazard)

    def test_firing_files_a_block(self, level, controller, refs, player) -> None:
        self._spawner(level, controller, refs, "B").collide(player)
        assert len(level.blocks) == 1
        assert isinstance(level.blocks[0], Block)

    def test_firing_files_a_trigger(self, level, controller, refs, player) -> None:
        self._spawner(level, controller, refs, "S").collide(player)
        assert any(isinstance(t, Trigger) for t in level.triggers)

    def test_coordinates_are_read_as_column_then_row(self, level, controller, refs,
                                                     player) -> None:
        self._spawner(level, controller, refs, "B", coords = "5 2").collide(player)
        assert level.blocks[0].rect.topleft == (5 * 96, 2 * 96)

    def test_a_repeatable_spawner_builds_a_new_entity_each_time(
            self, level, controller, refs, player) -> None:
        """The entity used to be built once, so repeat fires re-added the same object
        and the census counter climbed without any new enemy appearing."""
        trigger = self._spawner(level, controller, refs, "E", fire_once = False)
        trigger.collide(player)
        trigger.collide(player)

        assert len(level.enemies) == 2
        assert level.enemies[0] is not level.enemies[1]
        assert level.enemies_available == 2

    def test_spawned_entities_get_their_triggers_linked(self, level, controller,
                                                        refs, player) -> None:
        """build_level links everything it builds; the spawn path used to skip it,
        leaving a spawned entity's trigger reference an unresolved string."""
        alarm = _make(SaveTrigger, level, controller, None, name = "Packetalarm")
        level.triggers.append(alarm)

        spawner = self._spawner(level, controller, refs, "OT")
        spawner.collide(player)

        spawned = level.objectives[0]
        assert spawned.trigger == [alarm]

    def test_a_spawner_reports_the_wall_clock_cost_of_building(self, level,
                                                               controller, refs,
                                                               player) -> None:
        # Construction now happens at fire time, so the engine needs the offset to
        # subtract the hitch from the frame's delta time.
        assert self._spawner(level, controller, refs, "E").collide(player) > 0.0


# --------------------------------------------------------------------------- #
# SwapLevelTrigger
# --------------------------------------------------------------------------- #
class TestSwapLevelTrigger:
    def test_requests_a_hot_swap(self, level, controller, player) -> None:
        _make(SwapLevelTrigger, level, controller, None).collide(player)
        assert controller.should_hot_swap_level is True


# --------------------------------------------------------------------------- #
# TextTrigger
# --------------------------------------------------------------------------- #
class TestTextTrigger:
    def _text(self, level, controller, message_audios, payload, **kwargs) -> TextTrigger:
        return _make(TextTrigger, level, controller,
                     {"ref": message_audios, "input": payload}, **kwargs)

    def test_loads_the_lines_from_the_text_folder(self, level, controller,
                                                  message_audios) -> None:
        trigger = self._text(level, controller, message_audios, {"file": "message.txt"})
        assert trigger.value["text"] == ["First line.", "Second line."]

    def test_type_out_defaults_to_on(self, level, controller, message_audios) -> None:
        trigger = self._text(level, controller, message_audios, {"file": "message.txt"})
        assert trigger.value["should_type"] is True

    def test_type_out_can_be_turned_off(self, level, controller, message_audios) -> None:
        trigger = self._text(level, controller, message_audios,
                             {"file": "message.txt", "type": False})
        assert trigger.value["should_type"] is False

    def test_audio_is_resolved_from_the_message_bank(self, level, controller,
                                                     message_audios) -> None:
        trigger = self._text(level, controller, message_audios,
                             {"file": "message.txt", "audio": "INTRO"})
        assert trigger.value["audio"] is message_audios["INTRO"]

    def test_missing_audio_is_fatal(self, level, controller, message_audios) -> None:
        with pytest.raises(HandledError):
            self._text(level, controller, message_audios,
                       {"file": "message.txt", "audio": "NOPE"})

    def test_firing_displays_the_text(self, level, controller, message_audios, player,
                                      display_texts) -> None:
        trigger = self._text(level, controller, message_audios, {"file": "message.txt"})
        trigger.collide(player)
        assert display_texts[-1].lines == ["First line.", "Second line."]
        assert display_texts[-1].kwargs["should_type_text"] is True

    def test_the_retro_flag_follows_the_level(self, retro_level, controller,
                                              message_audios, display_texts) -> None:
        trigger = self._text(retro_level, controller, message_audios,
                             {"file": "message.txt"})
        trigger.collide(None)
        assert display_texts[-1].kwargs["retro"] is True
