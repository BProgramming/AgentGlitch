"""Tests for ``Controller`` -- input dispatch, settings and the game-state flags.

These run against a real ``Controller``, menus, selectors and all.  The methods that
spin their own event loop (``pause``, ``main``, ``settings``, ``pick_from_selector``)
are driven only where they can be entered and left deterministically; everything else
is exercised directly.
"""

from __future__ import annotations

import pygame
import pytest

import Controller as ControllerModule
from Controller import Controller
from Helpers import DifficultyScale
from Player import Player
from support.doubles import StubGamepad, StubLevel


@pytest.fixture
def real_controller(window: pygame.Surface) -> Controller:
    return Controller(None, window)


@pytest.fixture
def wired_level(real_controller: Controller, sprite_master, player_audios) -> StubLevel:
    """A level whose player belongs to the real controller under test."""
    level = StubLevel(real_controller)
    player = Player(level, real_controller, level.block_size, level.block_size,
                    sprite_master, player_audios, 1.0, level.block_size,
                    sprite = "Player1", retro_sprite = "RetroPlayer1")
    level.set_player(player)
    real_controller.level = level
    return level


class _KeyState:
    """Stands in for the sequence ``pygame.key.get_pressed`` returns."""

    def __init__(self, *pressed: int) -> None:
        self.pressed = set(pressed)

    def __getitem__(self, key: int) -> bool:
        return key in self.pressed

    def __iter__(self):
        return iter([])


@pytest.fixture
def press(monkeypatch: pytest.MonkeyPatch):
    def _press(*keys: int) -> None:
        monkeypatch.setattr(pygame.key, "get_pressed", lambda: _KeyState(*keys))
    return _press


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
class TestConstruction:
    def test_every_menu_is_built(self, real_controller: Controller) -> None:
        for name in ("main_menu", "pause_menu", "settings_menu", "volume_menu",
                     "controls_menu"):
            assert getattr(real_controller, name) is not None

    def test_every_selector_is_built(self, real_controller: Controller) -> None:
        for name in ("difficulty_picker", "sprite_picker", "level_picker",
                     "keyboard_layout_picker", "gamepad_layout_picker"):
            assert getattr(real_controller, name) is not None

    def test_the_retro_menu_entry_is_hidden_without_the_dlc(self,
                                                            real_controller: Controller) -> None:
        assert real_controller.has_dlc == {}
        assert len(real_controller.main_menu.buttons) == 5

    def test_volume_starts_at_full_on_every_channel(self,
                                                    real_controller: Controller) -> None:
        assert set(real_controller.master_volume) == {
            "master", "background", "player", "non-player", "cinematics"}
        assert all(v == 1.0 for v in real_controller.master_volume.values())

    def test_the_default_difficulty_is_medium(self, real_controller: Controller) -> None:
        assert real_controller.difficulty is DifficultyScale.MEDIUM

    def test_the_keyboard_layout_defaults_to_arrows(self,
                                                    real_controller: Controller) -> None:
        assert real_controller.active_keyboard_layout == "ARROW_MOVE"

    def test_an_explicit_layout_is_honoured(self, window: pygame.Surface) -> None:
        assert Controller(None, window, layout = "WASD_MOVE").active_keyboard_layout \
            == "WASD_MOVE"

    def test_no_gamepad_is_connected_at_startup(self,
                                                real_controller: Controller) -> None:
        assert real_controller.gamepad is None
        assert real_controller.active_gamepad_layout is None

    def test_the_game_state_flags_start_clear(self, real_controller: Controller) -> None:
        assert real_controller.next_level is None
        assert real_controller.should_scroll_to_point is None
        assert real_controller.should_hot_swap_level is False
        assert real_controller.goto_load is False


# --------------------------------------------------------------------------- #
# layouts
# --------------------------------------------------------------------------- #
class TestLayouts:
    def test_every_keyboard_layout_binds_the_same_actions(self) -> None:
        reference = set(Controller.KEYBOARD_LAYOUTS["ARROW_MOVE"])
        for name, layout in Controller.KEYBOARD_LAYOUTS.items():
            assert set(layout) == reference, f"{name} is missing bindings"

    def test_every_gamepad_layout_binds_the_pause_button(self) -> None:
        for name, layout in Controller.GAMEPAD_LAYOUTS.items():
            assert "button_pause_unpause" in layout, name

    def test_the_none_layout_binds_nothing(self) -> None:
        assert all(v is None for v in Controller.GAMEPAD_LAYOUTS["NONE"].values())

    def test_setting_a_gamepad_layout_of_none_clears_it(self,
                                                        real_controller: Controller) -> None:
        real_controller.set_gamepad_layout("XBOX")
        assert real_controller.active_gamepad_layout == "XBOX"
        real_controller.set_gamepad_layout("NONE")
        assert real_controller.active_gamepad_layout is None

    def test_cycling_walks_every_layout_and_returns_to_the_start(
            self, real_controller: Controller, display_texts) -> None:
        seen = [real_controller.active_keyboard_layout]
        for _ in range(len(Controller.KEYBOARD_LAYOUTS)):
            real_controller.cycle_keyboard_layout()
            seen.append(real_controller.active_keyboard_layout)
        assert seen[0] == seen[-1]
        assert set(seen) == set(Controller.KEYBOARD_LAYOUTS)

    def test_cycling_tells_the_player_what_changed(self, real_controller: Controller,
                                                   display_texts) -> None:
        real_controller.cycle_keyboard_layout()
        assert "Control layout changed" in display_texts[-1].text

    def test_cycling_from_an_unknown_layout_says_nothing(self,
                                                         real_controller: Controller,
                                                         display_texts) -> None:
        real_controller.set_keyboard_layout("SOMETHING_ELSE")
        real_controller.cycle_keyboard_layout()
        assert display_texts == []


# --------------------------------------------------------------------------- #
# objectives, difficulty, persistence
# --------------------------------------------------------------------------- #
class TestObjectives:
    def test_activating_by_name_marks_matching_objectives(
            self, real_controller: Controller, wired_level: StubLevel, sprite_master,
            block_audios) -> None:
        from Objective import Objective
        objective = Objective(wired_level, real_controller, 0, 0, 96, 96,
                              sprite_master, block_audios, sprite = "TestAnim",
                              text = "Grab it", name = "Packet")
        wired_level.objectives.append(objective)

        real_controller.activate_objective("Packet", True, popup = False)
        assert objective.is_active is True
        assert real_controller.active_objective == "Packet"

    def test_clearing_the_objective_falls_back_to_the_level_default(
            self, real_controller: Controller, wired_level: StubLevel) -> None:
        wired_level.default_objective = "Find the exit"
        real_controller.activate_objective(None, True, popup = False)
        assert real_controller.active_objective is None

    def test_a_popup_announces_the_new_objective(self, real_controller: Controller,
                                                 wired_level: StubLevel, sprite_master,
                                                 block_audios, display_texts) -> None:
        from HUD import HUD
        from Objective import Objective
        real_controller.hud = HUD(wired_level.player, real_controller.win)
        objective = Objective(wired_level, real_controller, 0, 0, 96, 96,
                              sprite_master, block_audios, sprite = "TestAnim",
                              text = "Grab it", name = "Packet")
        wired_level.objectives.append(objective)

        real_controller.activate_objective("Packet", True, popup = True)
        assert "New objective: Grab it" in display_texts[-1].text

    def test_without_a_level_nothing_happens(self, real_controller: Controller) -> None:
        real_controller.activate_objective("Packet", True)
        assert real_controller.active_objective is None


class TestDifficulty:
    def test_applying_a_difficulty_touches_every_entity(self,
                                                        real_controller: Controller,
                                                        wired_level: StubLevel) -> None:
        player = wired_level.player
        before = player.max_hp
        real_controller.difficulty = float(DifficultyScale.HARD)
        real_controller.set_difficulty()
        assert player.max_hp != before

    def test_without_a_level_it_is_a_no_op(self, real_controller: Controller) -> None:
        real_controller.set_difficulty()


class TestPersistence:
    def test_save_writes_a_save_file(self, real_controller: Controller,
                                     wired_level: StubLevel, game_data_dir) -> None:
        real_controller.save()
        assert (game_data_dir / "save.p").is_file()

    def test_save_player_profile_writes_a_profile(self, real_controller: Controller,
                                                  game_data_dir) -> None:
        real_controller.save_player_profile()
        assert (game_data_dir / "profile.p").is_file()

    def test_quit_saves_the_profile_before_exiting(self, real_controller: Controller,
                                                   monkeypatch: pytest.MonkeyPatch,
                                                   game_data_dir) -> None:
        monkeypatch.setattr(pygame, "get_init", lambda: False)
        monkeypatch.setattr(ControllerModule.pygame._sdl2.controller, "get_init",
                            lambda: False)
        monkeypatch.setattr(ControllerModule.sys, "exit",
                            lambda *a: (_ for _ in ()).throw(SystemExit()))
        with pytest.raises(SystemExit):
            real_controller.quit()
        assert (game_data_dir / "profile.p").is_file()


# --------------------------------------------------------------------------- #
# music
# --------------------------------------------------------------------------- #
class TestMusic:
    def test_queueing_uses_the_levels_playlist_by_default(
            self, real_controller: Controller, wired_level: StubLevel,
            monkeypatch: pytest.MonkeyPatch) -> None:
        loaded: list = []
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: False)
        monkeypatch.setattr(pygame.mixer.music, "load", lambda path: loaded.append(path))
        wired_level.music = ["one.mp3", "two.mp3"]

        real_controller.queue_track_list()
        assert real_controller.music == wired_level.music
        assert loaded == ["one.mp3"]

    def test_an_explicit_playlist_overrides_the_level(self, real_controller: Controller,
                                                      wired_level: StubLevel,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: False)
        monkeypatch.setattr(pygame.mixer.music, "load", lambda path: None)
        real_controller.queue_track_list(["boss.mp3"])
        assert real_controller.music == ["boss.mp3"]

    def test_cycling_advances_the_index(self, real_controller: Controller,
                                        wired_level: StubLevel,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: False)
        monkeypatch.setattr(pygame.mixer.music, "load", lambda path: None)
        real_controller.queue_track_list(["one.mp3", "two.mp3"])
        real_controller.cycle_music()
        assert real_controller.music_index == 1

    def test_cycling_past_the_end_restarts_the_playlist(self,
                                                        real_controller: Controller,
                                                        wired_level: StubLevel,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: False)
        monkeypatch.setattr(pygame.mixer.music, "load", lambda path: None)
        wired_level.music = ["one.mp3"]
        real_controller.queue_track_list(["one.mp3"])
        real_controller.cycle_music()
        assert real_controller.music_index == 0

    def test_cycling_without_a_playlist_is_a_no_op(self,
                                                   real_controller: Controller) -> None:
        real_controller.cycle_music()
        assert real_controller.music_index == 0


# --------------------------------------------------------------------------- #
# gamepad lifecycle
# --------------------------------------------------------------------------- #
class TestGamepad:
    def test_disabling_releases_the_handle_and_clears_the_layout(
            self, real_controller: Controller, display_texts) -> None:
        pad = StubGamepad()
        real_controller.gamepad = pad
        real_controller.set_gamepad_layout("XBOX")

        real_controller.disable_gamepad()
        assert real_controller.gamepad is None
        assert real_controller.active_gamepad_layout is None
        assert pad.quit_calls == 1
        assert "Controller disconnected." in display_texts[-1].text

    def test_disabling_quietly_skips_the_notice(self, real_controller: Controller,
                                                display_texts) -> None:
        real_controller.gamepad = StubGamepad()
        real_controller.disable_gamepad(notify = False)
        assert display_texts == []

    def test_disabling_with_no_gamepad_is_a_no_op(self,
                                                  real_controller: Controller) -> None:
        assert real_controller.disable_gamepad() >= 0.0

    def test_a_removal_event_for_another_device_is_ignored(
            self, real_controller: Controller) -> None:
        real_controller.gamepad = StubGamepad(instance_id = 1)
        event = pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id = 99)
        real_controller.on_device_removed(event, notify = False)
        assert real_controller.gamepad is not None

    def test_a_removal_event_for_this_device_drops_it(self,
                                                      real_controller: Controller) -> None:
        real_controller.gamepad = StubGamepad(instance_id = 7)
        event = pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id = 7)
        real_controller.on_device_removed(event, notify = False)
        assert real_controller.gamepad is None

    def test_removal_preserves_the_layout_for_a_clean_reconnect(
            self, real_controller: Controller) -> None:
        real_controller.gamepad = StubGamepad(instance_id = 7)
        real_controller.set_gamepad_layout("PS5")
        real_controller.on_device_removed(
            pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id = 7), notify = False)
        assert real_controller.active_gamepad_layout == "PS5"
        assert real_controller._gamepad_was_disconnected is True

    def test_removal_with_no_gamepad_is_a_no_op(self,
                                                real_controller: Controller) -> None:
        event = pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id = 1)
        assert real_controller.on_device_removed(event) >= 0.0

    def test_enabling_with_no_device_present_does_nothing(
            self, real_controller: Controller) -> None:
        # The headless test runner has no controllers attached.
        real_controller.enable_gamepad(notify = False)
        assert real_controller.gamepad is None


# --------------------------------------------------------------------------- #
# input dispatch
# --------------------------------------------------------------------------- #
class TestSingleInput:
    @pytest.fixture(autouse = True)
    def _no_pause_loop(self, real_controller: Controller,
                       monkeypatch: pytest.MonkeyPatch) -> list:
        calls: list = []
        monkeypatch.setattr(real_controller, "pause",
                            lambda: (calls.append(1), 0.0)[1])
        return calls

    def _key(self, controller: Controller, action: str) -> int:
        return Controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout][action][0]

    def test_the_pause_key_pauses(self, real_controller: Controller,
                                  _no_pause_loop: list) -> None:
        real_controller.handle_single_input(self._key(real_controller,
                                                      "keys_pause_unpause"))
        assert _no_pause_loop == [1]

    def test_the_quicksave_key_saves(self, real_controller: Controller,
                                     wired_level: StubLevel, game_data_dir) -> None:
        real_controller.handle_single_input(self._key(real_controller, "keys_quicksave"))
        assert (game_data_dir / "save.p").is_file()

    def test_the_layout_key_cycles_the_layout(self, real_controller: Controller) -> None:
        real_controller.handle_single_input(self._key(real_controller,
                                                      "keys_cycle_layout"))
        assert real_controller.active_keyboard_layout == "WASD_MOVE"

    def test_the_fullscreen_key_toggles_fullscreen(self, real_controller: Controller,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(pygame.display, "toggle_fullscreen",
                            lambda: calls.append(1))
        real_controller.handle_single_input(self._key(real_controller,
                                                      "keys_fullscreen_toggle"))
        assert calls == [1]

    def test_the_crouch_key_crouches(self, real_controller: Controller,
                                     wired_level: StubLevel) -> None:
        real_controller.handle_single_input(self._key(real_controller,
                                                      "keys_crouch_uncrouch"))
        assert wired_level.player.is_crouching is True

    def test_the_jump_key_jumps(self, real_controller: Controller,
                                wired_level: StubLevel) -> None:
        real_controller.handle_single_input(self._key(real_controller, "keys_jump"))
        assert wired_level.player.jump_count == 1

    def test_gameplay_keys_are_ignored_while_the_camera_is_panning(
            self, real_controller: Controller, wired_level: StubLevel) -> None:
        real_controller.should_scroll_to_point = {"coords": (0, 0), "time": 0.0}
        real_controller.handle_single_input(self._key(real_controller, "keys_jump"))
        assert wired_level.player.jump_count == 0

    def test_an_unbound_key_does_nothing(self, real_controller: Controller,
                                         wired_level: StubLevel) -> None:
        assert real_controller.handle_single_input(pygame.K_z) == 0.0
        assert wired_level.player.jump_count == 0


class TestContinuousInput:
    def _key(self, controller: Controller, action: str) -> int:
        return Controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout][action][0]

    def test_the_right_key_moves_the_player_right(self, real_controller: Controller,
                                                  wired_level: StubLevel, press) -> None:
        press(self._key(real_controller, "keys_right"))
        real_controller.handle_continuous_input()
        assert wired_level.player.should_move_horiz is True

    def test_releasing_everything_stops_the_player(self, real_controller: Controller,
                                                   wired_level: StubLevel,
                                                   press) -> None:
        wired_level.player.move_right()
        press()
        real_controller.handle_continuous_input()
        assert wired_level.player.should_move_horiz is False

    def test_the_attack_key_attacks(self, real_controller: Controller,
                                    wired_level: StubLevel, press) -> None:
        press(self._key(real_controller, "keys_attack"))
        real_controller.handle_continuous_input()
        assert wired_level.player.is_attacking is True

    def test_not_attacking_clears_the_flag(self, real_controller: Controller,
                                           wired_level: StubLevel, press) -> None:
        wired_level.player.is_attacking = True
        press()
        real_controller.handle_continuous_input()
        assert wired_level.player.is_attacking is False

    def test_the_block_key_raises_a_shield(self, real_controller: Controller,
                                           wired_level: StubLevel, press) -> None:
        wired_level.player.abilities["can_block"] = True
        press(self._key(real_controller, "keys_block"))
        real_controller.handle_continuous_input()
        assert wired_level.player.cooldowns["block"] > 0

    def test_input_is_suspended_while_the_camera_is_panning(
            self, real_controller: Controller, wired_level: StubLevel, press) -> None:
        real_controller.should_scroll_to_point = {"coords": (0, 0), "time": 0.0}
        press(self._key(real_controller, "keys_right"))
        assert real_controller.handle_continuous_input() == 0.0
        assert wired_level.player.should_move_horiz is False

    def test_without_a_level_it_is_a_no_op(self, real_controller: Controller,
                                           press) -> None:
        press()
        assert real_controller.handle_continuous_input() == 0.0


class TestKeyHelpers:
    def test_pause_is_only_triggered_by_the_pause_binding(
            self, real_controller: Controller, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(real_controller, "pause", lambda: (calls.append(1), 0.0)[1])

        assert real_controller.handle_pause_unpause(pygame.K_z) == 0.0
        assert calls == []

        real_controller.handle_pause_unpause(pygame.K_ESCAPE)
        assert calls == [1]

    def test_any_key_reports_nothing_pressed(self, real_controller: Controller,
                                             press) -> None:
        press()
        assert real_controller.handle_any_key() is False

    def test_any_key_reports_a_pressed_key(self, real_controller: Controller,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
        # handle_any_key uses any(pygame.key.get_pressed()), so the stand-in has to
        # iterate as a bitmap rather than answer __getitem__ lookups.
        monkeypatch.setattr(pygame.key, "get_pressed", lambda: [False, True, False])
        assert real_controller.handle_any_key() is True


def test_refreshing_selector_images_leaves_every_picker_valid(
        real_controller: Controller) -> None:
    real_controller.force_retro = True
    real_controller.refresh_selector_images()
    for name in ("difficulty_picker", "sprite_picker", "level_picker",
                 "keyboard_layout_picker", "gamepad_layout_picker"):
        assert getattr(real_controller, name).image_selected is not None


# --------------------------------------------------------------------------- #
# menu flows
# --------------------------------------------------------------------------- #
class _ScriptedLoop:
    """Replaces ``Menu.loop`` with a fixed sequence of returns.

    The menu screens are ``while True`` loops fed by ``menu.loop()``; scripting that
    one method is what makes them testable without simulating a whole input stack.
    Once the script runs out the loop raises, so a flow that never terminates fails
    the test instead of hanging it.  ``Controller.main`` in particular has no "back"
    case -- there is nowhere to go from the main menu -- so a script for it must end
    on a value that genuinely leaves the menu.
    """

    def __init__(self, *values: int | None) -> None:
        self.values = list(values)
        self.calls  = 0

    def __call__(self) -> int | None:
        self.calls += 1
        if not self.values:
            raise AssertionError(
                "the menu flow did not terminate: the scripted loop ran out of "
                f"values after {self.calls} calls")
        return self.values.pop(0)


@pytest.fixture
def quiet_menus(real_controller: Controller, monkeypatch: pytest.MonkeyPatch):
    """Silence every menu fade so the flows run in a single frame."""
    for name in ("main_menu", "pause_menu", "settings_menu", "volume_menu",
                 "controls_menu", "difficulty_picker", "sprite_picker",
                 "level_picker", "keyboard_layout_picker", "gamepad_layout_picker"):
        menu = getattr(real_controller, name)
        monkeypatch.setattr(menu, "fade_in", lambda: None)
        monkeypatch.setattr(menu, "fade_out", lambda: None)
        if hasattr(menu, "fade_music"):
            monkeypatch.setattr(menu, "fade_music", lambda: None)

    def _script(menu_name: str, *values: int | None) -> _ScriptedLoop:
        loop = _ScriptedLoop(*values)
        monkeypatch.setattr(getattr(real_controller, menu_name), "loop", loop)
        return loop

    return _script


class TestPauseMenu:
    def test_resume_leaves_the_pause_menu(self, real_controller: Controller,
                                          quiet_menus) -> None:
        quiet_menus("pause_menu", 0)
        assert real_controller.pause() >= 0.0
        assert real_controller.goto_load is False

    def test_load_last_save_sets_the_flag_and_returns(self, real_controller: Controller,
                                                      quiet_menus) -> None:
        quiet_menus("pause_menu", 1)
        assert real_controller.pause() == 0.0
        assert real_controller.goto_load is True

    def test_restart_level_sets_the_flag(self, real_controller: Controller,
                                         quiet_menus) -> None:
        quiet_menus("pause_menu", 2)
        real_controller.pause()
        assert real_controller.goto_restart is True

    def test_quit_to_menu_saves_and_sets_the_flag(self, real_controller: Controller,
                                                  wired_level: StubLevel, quiet_menus,
                                                  game_data_dir) -> None:
        quiet_menus("pause_menu", 4)
        real_controller.pause()
        assert real_controller.goto_main is True
        assert (game_data_dir / "save.p").is_file()
        assert (game_data_dir / "profile.p").is_file()

    def test_backing_out_resumes(self, real_controller: Controller,
                                 quiet_menus) -> None:
        quiet_menus("pause_menu", -1)
        real_controller.pause()
        assert real_controller.goto_main is False

    def test_settings_can_be_opened_from_the_pause_menu(self,
                                                        real_controller: Controller,
                                                        quiet_menus) -> None:
        quiet_menus("pause_menu", 3, 0)
        quiet_menus("settings_menu", -1)
        real_controller.pause()


class TestSettingsMenu:
    def test_backing_out_applies_the_difficulty_slider(self,
                                                       real_controller: Controller,
                                                       quiet_menus) -> None:
        # settings() re-seeds the slider from controller.difficulty on entry, so the
        # drag has to happen inside the loop -- as it would with a real mouse.
        script = quiet_menus("settings_menu", 0, 4)
        bar    = real_controller.settings_menu.buttons[0]
        inner  = real_controller.settings_menu.loop

        def _drag_then_loop() -> int | None:
            if script.calls == 0:
                bar.value = float(DifficultyScale.HARD)
            return inner()

        real_controller.settings_menu.loop = _drag_then_loop   # type: ignore[method-assign]
        real_controller.settings()
        assert real_controller.difficulty is DifficultyScale.HARD

    def test_the_fullscreen_entry_toggles_fullscreen(self, real_controller: Controller,
                                                     quiet_menus,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(pygame.display, "toggle_fullscreen",
                            lambda: calls.append(1))
        quiet_menus("settings_menu", 3, 4)
        real_controller.settings()
        assert calls == [1]

    def test_the_volume_entry_opens_the_volume_menu(self, real_controller: Controller,
                                                    quiet_menus) -> None:
        quiet_menus("settings_menu", 2, 4)
        volume = quiet_menus("volume_menu", 5)
        real_controller.settings()
        assert volume.calls >= 1

    def test_the_controls_entry_opens_the_controls_menu(self,
                                                        real_controller: Controller,
                                                        quiet_menus) -> None:
        quiet_menus("settings_menu", 1, 4)
        controls = quiet_menus("controls_menu", 2)
        real_controller.settings()
        assert controls.calls >= 1


class TestVolumeMenu:
    def test_the_sliders_are_seeded_from_the_current_volumes(self,
                                                             real_controller: Controller,
                                                             quiet_menus) -> None:
        real_controller.master_volume["player"] = 0.4
        quiet_menus("volume_menu", 5)
        real_controller.volume()
        assert real_controller.master_volume["player"] == pytest.approx(0.4)

    def test_moving_the_master_slider_moves_every_channel(self,
                                                          real_controller: Controller,
                                                          quiet_menus) -> None:
        loop = _ScriptedLoop(0, 5)

        def _drag_then_loop() -> int | None:
            if loop.calls == 0:
                real_controller.volume_menu.buttons[0].value = 50
            return loop()

        real_controller.volume_menu.loop = _drag_then_loop      # type: ignore[method-assign]
        for name in ("volume_menu",):
            menu = getattr(real_controller, name)
            menu.fade_in = lambda: None                         # type: ignore[method-assign]
            menu.fade_out = lambda: None                        # type: ignore[method-assign]

        real_controller.volume()
        assert all(v == pytest.approx(0.5) for v in real_controller.master_volume.values())

    def test_backing_out_stores_the_channel_sliders(self, real_controller: Controller,
                                                    quiet_menus) -> None:
        # volume() re-seeds every slider from master_volume on entry, so the drags
        # have to happen inside the loop.
        script = quiet_menus("volume_menu", 2, 5)
        inner  = real_controller.volume_menu.loop
        buttons = real_controller.volume_menu.buttons

        def _drag_then_loop() -> int | None:
            if script.calls == 0:
                buttons[2].value = 30
                buttons[3].value = 20
                buttons[4].value = 10
            return inner()

        real_controller.volume_menu.loop = _drag_then_loop     # type: ignore[method-assign]
        real_controller.volume()
        assert real_controller.master_volume["player"] == pytest.approx(0.3)
        assert real_controller.master_volume["non-player"] == pytest.approx(0.2)
        assert real_controller.master_volume["cinematics"] == pytest.approx(0.1)


class TestControlsMenu:
    def test_the_controller_entry_is_disabled_without_a_gamepad(
            self, real_controller: Controller, quiet_menus) -> None:
        quiet_menus("controls_menu", 2)
        real_controller.controls()
        assert real_controller.controls_menu.buttons[1].is_enabled is False

    def test_the_controller_entry_is_enabled_with_a_gamepad(
            self, real_controller: Controller, quiet_menus) -> None:
        real_controller.gamepad = StubGamepad()
        quiet_menus("controls_menu", 2)
        real_controller.controls()
        assert real_controller.controls_menu.buttons[1].is_enabled is True

    def test_accepting_a_keyboard_layout_applies_it(self, real_controller: Controller,
                                                    quiet_menus,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("controls_menu", 0, 2)

        # controls() re-seeds the picker from the active layout before opening it, so
        # the choice has to be made inside the picker.
        def _pick(selector, **kwargs) -> bool:
            selector.image_index = 1
            return True

        monkeypatch.setattr(real_controller, "pick_from_selector", _pick)
        real_controller.controls()
        assert real_controller.active_keyboard_layout == \
            real_controller.keyboard_layout_picker.values[1]

    def test_declining_leaves_the_layout_alone(self, real_controller: Controller,
                                               quiet_menus,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("controls_menu", 0, 2)
        monkeypatch.setattr(real_controller, "pick_from_selector",
                            lambda selector, **kwargs: False)
        real_controller.controls()
        assert real_controller.active_keyboard_layout == "ARROW_MOVE"


class TestMainMenu:
    def test_continue_sets_the_load_flag_and_reports_no_new_game(
            self, real_controller: Controller, quiet_menus) -> None:
        quiet_menus("main_menu", 1)
        assert real_controller.main() is False
        assert real_controller.goto_load is True

    def test_a_new_game_records_the_chosen_sprite_and_difficulty(
            self, real_controller: Controller, quiet_menus,
            monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("main_menu", 0)
        monkeypatch.setattr(real_controller, "pick_from_selector",
                            lambda selector, **kwargs: True)
        real_controller.sprite_picker.image_index     = 0
        real_controller.difficulty_picker.image_index = 4

        assert real_controller.main() is True
        assert real_controller.player_sprite_selected == \
            real_controller.sprite_picker.values[0]
        assert real_controller.difficulty is DifficultyScale.HARDEST

    def test_backing_out_of_the_sprite_picker_returns_to_the_menu(
            self, real_controller: Controller, quiet_menus,
            monkeypatch: pytest.MonkeyPatch) -> None:
        # Backing out of the sprite picker drops back to the menu rather than
        # starting a game; "Continue" then leaves main().
        quiet_menus("main_menu", 0, 1)
        monkeypatch.setattr(real_controller, "pick_from_selector",
                            lambda selector, **kwargs: False)
        assert real_controller.main() is False

    def test_selecting_a_level_records_it(self, real_controller: Controller,
                                          quiet_menus,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("main_menu", 2)
        monkeypatch.setattr(real_controller, "pick_from_selector",
                            lambda selector, **kwargs: True)
        real_controller.level_picker.image_index = 1
        assert real_controller.main() is False
        assert real_controller.level_selected == \
            real_controller.level_picker.values[1]

    def test_the_first_level_counts_as_a_new_game(self, real_controller: Controller,
                                                  quiet_menus,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("main_menu", 2)
        monkeypatch.setattr(real_controller, "pick_from_selector",
                            lambda selector, **kwargs: True)
        real_controller.level_picker.image_index = 0
        assert real_controller.main() is True

    def test_settings_can_be_opened_from_the_main_menu(self,
                                                       real_controller: Controller,
                                                       quiet_menus) -> None:
        quiet_menus("main_menu", 3, 1)
        settings = quiet_menus("settings_menu", 4)
        real_controller.main()
        assert settings.calls >= 1

    def test_without_the_dlc_the_last_entry_quits(self, real_controller: Controller,
                                                  quiet_menus,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        quiet_menus("main_menu", 4)
        calls: list = []
        monkeypatch.setattr(real_controller, "quit",
                            lambda: (calls.append(1), (_ for _ in ()).throw(SystemExit()))[0])
        with pytest.raises(SystemExit):
            real_controller.main()
        assert calls == [1]

    def test_with_the_dlc_the_retro_entry_toggles_the_palette(
            self, real_controller: Controller, quiet_menus) -> None:
        real_controller.has_dlc = {"gumshoe": True}
        quiet_menus("main_menu", 4, 1)
        real_controller.main()
        assert real_controller.force_retro is True


class TestSelectorFlow:
    def test_accepting_reports_true(self, real_controller: Controller,
                                    quiet_menus) -> None:
        quiet_menus("sprite_picker", 3)
        assert real_controller.pick_from_selector(real_controller.sprite_picker) is True

    def test_backing_out_reports_false(self, real_controller: Controller,
                                       quiet_menus) -> None:
        quiet_menus("sprite_picker", 2)
        assert real_controller.pick_from_selector(real_controller.sprite_picker) is False

    def test_the_arrow_buttons_cycle_the_image(self, real_controller: Controller,
                                               quiet_menus) -> None:
        picker = real_controller.sprite_picker
        quiet_menus("sprite_picker", 1, 2)
        start = picker.image_index
        real_controller.pick_from_selector(picker)
        assert picker.image_index != start

    def test_an_accept_only_selector_treats_its_single_button_as_accept(
            self, real_controller: Controller, quiet_menus) -> None:
        quiet_menus("gamepad_layout_picker", 0)
        assert real_controller.pick_from_selector(
            real_controller.gamepad_layout_picker) is False
