"""Tests for ``Menu`` -- buttons, sliders and keyboard/gamepad focus navigation."""

from __future__ import annotations

import pygame
import pytest

from Helpers import DifficultyScale, load_images, load_picker_sprites
from Menu import Bar, Button, ButtonType, Menu, Selector


@pytest.fixture
def click_items() -> list[dict]:
    return [{"label": "New game", "type": ButtonType.CLICK},
            {"label": "Settings", "type": ButtonType.CLICK},
            {"label": "Quit",     "type": ButtonType.CLICK}]


@pytest.fixture
def menu(controller, click_items) -> Menu:
    return Menu(controller, "MAIN", click_items)


@pytest.fixture
def slider_menu(controller) -> Menu:
    return Menu(controller, "VOLUME", [
        {"label": "Master", "type": ButtonType.BAR, "snap": False,
         "value": 0.5, "range": (0, 100)},
        {"label": "Back", "type": ButtonType.CLICK},
    ])


@pytest.fixture
def selector(controller) -> Selector:
    images, values = load_picker_sprites("Sprites")
    return Selector(controller, "CHOOSE", ["A note."], images, values)


# --------------------------------------------------------------------------- #
# Button
# --------------------------------------------------------------------------- #
class TestButton:
    @pytest.fixture
    def button(self, controller) -> Button:
        return Button(controller, 10, 20, 100, 40, "value")

    def test_it_keeps_its_geometry_and_value(self, button: Button) -> None:
        assert button.rect.topleft == (10, 20)
        assert button.value == "value"

    def test_it_renders_both_states_for_both_colour_schemes(self,
                                                            button: Button) -> None:
        assert set(button._normal) == {"normal", "mouseover"}
        assert set(button._retro) == {"normal", "mouseover"}

    def test_the_active_scheme_follows_the_controller(self, button: Button,
                                                      controller) -> None:
        assert button.normal is button._normal["normal"]
        controller.force_retro = True
        assert button.normal is button._retro["normal"]

    def test_a_label_is_centred_on_the_button(self, controller) -> None:
        label = pygame.font.SysFont("courier", 16).render("Hi", True, (255, 255, 255))
        button = Button(controller, 0, 0, 100, 40, 0, label_normal = label)
        assert button.normal.get_size() == (100, 40)

    def test_an_image_is_copied_rather_than_shared(self, controller) -> None:
        image = pygame.Surface((100, 40), pygame.SRCALPHA)
        image.fill((10, 20, 30, 255))
        button = Button(controller, 0, 0, 100, 40, 0, img_normal = image)
        assert button._normal["normal"] is not image

    def test_alpha_is_applied_to_both_schemes(self, button: Button) -> None:
        button.set_alpha(200)
        assert button._normal["normal"].get_alpha() == 200
        assert button._retro["normal"].get_alpha() == 200

    def test_a_disabled_button_is_drawn_at_half_alpha(self, button: Button) -> None:
        button.is_enabled = False
        button.set_alpha(200)
        assert button._normal["normal"].get_alpha() == 100

    def test_drawing_uses_the_mouseover_art_when_focused(self, button: Button,
                                                         controller) -> None:
        button._normal["normal"].fill((10, 0, 0, 255))
        button._normal["mouseover"].fill((0, 200, 0, 255))
        button.is_focused = True
        button.draw()
        assert controller.win.get_at((15, 25))[:3] == (0, 200, 0)

    def test_a_disabled_button_never_highlights(self, button: Button,
                                               controller) -> None:
        button._normal["normal"].fill((10, 0, 0, 255))
        button._normal["mouseover"].fill((0, 200, 0, 255))
        button.is_focused = True
        button.is_enabled = False
        button.draw()
        assert controller.win.get_at((15, 25))[:3] == (10, 0, 0)


# --------------------------------------------------------------------------- #
# Bar
# --------------------------------------------------------------------------- #
class TestBar:
    def _bar(self, controller, value, rng = (0, 100)) -> Bar:
        return Bar(controller, 0, 0, 200, 60, value, rng)

    @pytest.mark.parametrize("value, expected", [(0, 0.0), (50, 0.5), (100, 1.0)])
    def test_pct_val_maps_the_value_onto_the_range(self, controller, value,
                                                   expected) -> None:
        assert self._bar(controller, value).pct_val == expected

    def test_pct_val_works_for_a_non_zero_based_range(self, controller) -> None:
        bar = self._bar(controller, 1.0, (float(DifficultyScale.EASIEST),
                                          float(DifficultyScale.HARDEST)))
        assert bar.pct_val == pytest.approx((1.0 - 0.25) / (2.0 - 0.25))

    def test_the_track_and_notch_are_drawn_onto_the_button_art(self,
                                                               controller) -> None:
        left  = self._bar(controller, 0)
        right = self._bar(controller, 100)
        assert pygame.image.tostring(left.normal, "RGBA") != \
               pygame.image.tostring(right.normal, "RGBA")

    def test_the_mouseover_art_also_gets_a_notch(self, controller) -> None:
        bar = self._bar(controller, 50)
        assert bar.mouseover.get_size() == bar.normal.get_size()

    def test_snapping_is_recorded(self, controller) -> None:
        assert Bar(controller, 0, 0, 200, 60, 0, (0, 100), snap = True).snap is True


# --------------------------------------------------------------------------- #
# Menu
# --------------------------------------------------------------------------- #
class TestMenu:
    def test_one_button_is_built_per_entry(self, menu: Menu, click_items) -> None:
        assert len(menu.buttons) == len(click_items)
        assert all(isinstance(b, Button) for b in menu.buttons)

    def test_bar_entries_become_sliders(self, slider_menu: Menu) -> None:
        assert isinstance(slider_menu.buttons[0], Bar)
        assert isinstance(slider_menu.buttons[1], Button)

    def test_the_panel_is_centred_on_the_window(self, menu: Menu, controller) -> None:
        assert menu.rect.centerx == pytest.approx(controller.win.get_width() // 2, abs = 1)

    def test_a_header_makes_the_panel_taller(self, controller, click_items) -> None:
        headed   = Menu(controller, "MAIN", click_items)
        headless = Menu(controller, None, click_items)
        assert headed.rect.height > headless.rect.height

    def test_focus_starts_on_the_first_button(self, menu: Menu) -> None:
        assert menu.focused_index == 0

    def test_focus_moves_down_and_up(self, menu: Menu) -> None:
        menu._apply_focus_move((0, 1))
        assert menu.focused_index == 1
        menu._apply_focus_move((0, -1))
        assert menu.focused_index == 0

    def test_focus_stops_at_the_ends(self, menu: Menu) -> None:
        menu._apply_focus_move((0, -1))
        assert menu.focused_index == 0
        for _ in range(10):
            menu._apply_focus_move((0, 1))
        assert menu.focused_index == len(menu.buttons) - 1

    def test_horizontal_input_does_not_move_a_vertical_menu(self, menu: Menu) -> None:
        menu._apply_focus_move((1, 0))
        assert menu.focused_index == 0

    def test_set_mouse_pos_clamps_into_range(self, menu: Menu) -> None:
        menu.set_mouse_pos(99)
        assert menu.focused_index == len(menu.buttons) - 1
        menu.set_mouse_pos(-5)
        assert menu.focused_index == 0

    def test_alpha_is_applied_to_the_panel_and_every_button(self, menu: Menu) -> None:
        menu.set_alpha(120)
        assert menu.screen_normal.get_alpha() == 120
        assert all(b._normal["normal"].get_alpha() == 120 for b in menu.buttons)

    def test_music_cycles_and_wraps(self, controller, click_items) -> None:
        menu = Menu(controller, None, click_items,
                    music = ["track_one.mp3", "track_two.mp3"])
        menu.cycle_music()
        assert menu.music_index == 1
        menu.cycle_music()
        assert menu.music_index == 0

    def test_cycling_with_no_music_is_a_no_op(self, menu: Menu) -> None:
        menu.cycle_music()
        assert menu.music_index == 0

    def test_a_bar_confirmation_reports_its_index(self, slider_menu: Menu) -> None:
        assert slider_menu._handle_bar_confirm(0, slider_menu.buttons[0]) == 0

    def test_drawing_the_menu_paints_the_window(self, menu: Menu, controller) -> None:
        controller.win.fill((0, 0, 0))
        menu.draw()
        assert controller.win.get_at((menu.rect.centerx, menu.rect.centery))[:3] != (0, 0, 0)


# --------------------------------------------------------------------------- #
# Selector
# --------------------------------------------------------------------------- #
class TestSelector:
    def test_a_full_selector_has_four_buttons(self, selector: Selector) -> None:
        assert len(selector.buttons) == 4

    def test_an_accept_only_selector_has_one(self, controller) -> None:
        images = list((load_images("Menu", "Keyboards") or {}).values())
        sel = Selector(controller, "LAYOUT", None, images, ["A", "B"],
                       accept_only = True)
        assert len(sel.buttons) == 1

    def test_both_colour_schemes_are_prepared_for_a_plain_image_list(self,
                                                                     controller) -> None:
        images = list((load_images("Menu", "Keyboards") or {}).values())
        sel = Selector(controller, None, None, images, ["A", "B", "C", "D"])
        assert len(sel.images["normal"]) == len(sel.images["retro"]) == len(images)

    def test_a_dict_of_images_keeps_its_two_banks(self, selector: Selector) -> None:
        assert set(selector.images) == {"normal", "retro"}

    def test_the_starting_index_is_honoured(self, controller) -> None:
        images, values = load_picker_sprites("Sprites")
        assert Selector(controller, None, None, images, values, index = 1).image_index == 1

    def test_cycling_forwards_wraps_round(self, selector: Selector) -> None:
        count = len(selector.values)
        selector.set_index(count - 1)
        selector.cycle_images(1)
        assert selector.image_index == 0

    def test_cycling_backwards_wraps_round(self, selector: Selector) -> None:
        selector.set_index(0)
        selector.cycle_images(-1)
        assert selector.image_index == len(selector.values) - 1

    def test_set_index_does_not_validate_its_argument(self,
                                                      selector: Selector) -> None:
        """Characterisation: ``set_index`` indexes the image bank directly.

        ``cycle_images`` wraps, but ``set_index`` neither wraps nor clamps: an index
        past the end raises IndexError, and a negative one silently selects from the
        far end via Python's negative indexing.  Callers currently only pass indices
        they computed from the bank itself, so nothing trips it today.
        See BUGS_FOUND.md #14.
        """
        with pytest.raises(IndexError):
            selector.set_index(999)

        selector.set_index(-1)
        assert selector.image_index == -1

    def test_navigation_walks_the_two_by_two_grid(self, selector: Selector) -> None:
        selector.focused_index = 0
        selector._apply_focus_move((1, 0))
        assert selector.focused_index == 1
        selector._apply_focus_move((-1, 0))
        assert selector.focused_index == 0

    def test_an_accept_only_selector_ignores_navigation(self, controller) -> None:
        images = list((load_images("Menu", "Keyboards") or {}).values())
        sel = Selector(controller, None, None, images, ["A", "B"], accept_only = True)
        sel._apply_focus_move((1, 0))
        assert sel.focused_index == 0

    def test_alpha_is_applied_to_the_images_as_well_as_the_buttons(self,
                                                                   selector: Selector) -> None:
        selector.set_alpha(100)
        assert selector.screen_normal.get_alpha() == 100

    def test_drawing_paints_the_window(self, selector: Selector, controller) -> None:
        controller.win.fill((0, 0, 0))
        selector.draw()
        assert controller.win.get_at((selector.rect.centerx,
                                      selector.rect.centery))[:3] != (0, 0, 0)


# --------------------------------------------------------------------------- #
# input loop -- Menu
# --------------------------------------------------------------------------- #
@pytest.fixture
def mouse_away(monkeypatch: pytest.MonkeyPatch):
    """Park the mouse off every button so hover cannot steal focus."""
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (-100, -100))
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))


def _keydown(key: int) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = key))


class TestMenuLoop:
    def test_a_quiet_frame_selects_nothing(self, menu: Menu, mouse_away) -> None:
        assert menu.loop() is None

    def test_the_down_binding_moves_focus_down(self, menu: Menu, mouse_away,
                                               controller) -> None:
        layout = controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout]
        _keydown(layout["keys_crouch_uncrouch"][0])
        menu.loop()
        assert menu.focused_index == 1

    def test_the_up_binding_moves_focus_up(self, menu: Menu, mouse_away,
                                           controller) -> None:
        layout = controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout]
        menu.focused_index = 2
        _keydown(layout["keys_jump"][0])
        menu.loop()
        assert menu.focused_index == 1

    @pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE])
    def test_confirming_returns_the_focused_index(self, menu: Menu, mouse_away,
                                                  key) -> None:
        menu.focused_index = 1
        _keydown(key)
        assert menu.loop() == 1

    def test_the_pause_binding_backs_out(self, menu: Menu, mouse_away,
                                         controller) -> None:
        layout = controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout]
        _keydown(layout["keys_pause_unpause"][0])
        assert menu.loop() == -1

    def test_hovering_a_button_moves_focus_to_it(self, menu: Menu,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
        target = menu.buttons[2]
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: target.rect.center)
        monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
        menu.loop()
        assert menu.focused_index == 2
        assert target.is_mouseover is True

    def test_clicking_a_hovered_button_selects_it(self, menu: Menu,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        target = menu.buttons[1]
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: target.rect.center)
        monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1))
        assert menu.loop() == 1

    def test_only_the_focused_button_is_highlighted(self, menu: Menu,
                                                    mouse_away) -> None:
        menu.focused_index = 1
        menu.loop()
        assert [b.is_focused for b in menu.buttons] == [False, True, False]

    def test_dragging_a_slider_sets_its_value(self, slider_menu: Menu,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
        bar = slider_menu.buttons[0]
        slider_menu.focused_index = 0
        monkeypatch.setattr(pygame.mouse, "get_pos",
                            lambda: (bar.bar_rect.x + bar.bar_rect.width // 2,
                                     bar.rect.centery))
        monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
        slider_menu.loop()
        assert bar.value == pytest.approx(bar.range[-1] / 2, rel = 0.1)

    def test_a_snapping_slider_lands_on_a_range_value(self, controller,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
        steps = (0.25, 0.5, 1.0, 1.5, 2.0)
        menu = Menu(controller, None, [{"label": "Difficulty", "type": ButtonType.BAR,
                                        "snap": True, "value": 1.0, "range": steps}])
        bar = menu.buttons[0]
        monkeypatch.setattr(pygame.mouse, "get_pos",
                            lambda: (bar.bar_rect.x + int(bar.bar_rect.width * 0.1),
                                     bar.rect.centery))
        monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
        menu.loop()
        assert bar.value in steps

    def test_a_gamepad_stick_moves_focus(self, menu: Menu, mouse_away, controller,
                                         gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        gamepad.axes[layout["axis_vert"]] = Menu.JOYSTICK_TOLERANCE * 2
        menu.loop()
        assert menu.focused_index == 1

    def test_holding_the_stick_does_not_repeat_immediately(self, menu: Menu,
                                                           mouse_away, controller,
                                                           gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        gamepad.axes[layout["axis_vert"]] = Menu.JOYSTICK_TOLERANCE * 2
        menu.loop()
        menu.loop()
        assert menu.focused_index == 1

    def test_releasing_the_stick_clears_the_hold(self, menu: Menu, mouse_away,
                                                 controller, gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        gamepad.axes[layout["axis_vert"]] = Menu.JOYSTICK_TOLERANCE * 2
        menu.loop()
        gamepad.axes[layout["axis_vert"]] = 0
        menu.loop()
        assert menu._joy_held == (0, 0)

    def test_a_dpad_press_moves_focus(self, menu: Menu, mouse_away, controller,
                                      gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        gamepad.buttons[layout["button_down"]] = True
        menu.loop()
        assert menu.focused_index == 1

    def test_the_gamepad_confirm_button_selects(self, menu: Menu, mouse_away,
                                                controller, gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        menu.focused_index = 2
        pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN,
                                             button = layout["button_jump"]))
        assert menu.loop() == 2

    def test_the_gamepad_back_button_backs_out(self, menu: Menu, mouse_away,
                                               controller, gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN,
                                             button = layout["button_crouch_uncrouch"]))
        assert menu.loop() == -1


# --------------------------------------------------------------------------- #
# input loop -- Selector
# --------------------------------------------------------------------------- #
class TestSelectorLoop:
    def test_a_quiet_frame_selects_nothing(self, selector: Selector,
                                           mouse_away) -> None:
        assert selector.loop() is None

    def test_the_right_binding_reports_the_arrow_button(self, selector: Selector,
                                                        mouse_away, controller) -> None:
        layout = controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout]
        selector.focused_index = 0
        _keydown(layout["keys_right"][0])
        assert selector.loop() == 1

    def test_confirming_returns_the_focused_button(self, selector: Selector,
                                                   mouse_away) -> None:
        selector.focused_index = 3
        _keydown(pygame.K_RETURN)
        assert selector.loop() == 3

    def test_the_pause_binding_backs_out(self, selector: Selector, mouse_away,
                                         controller) -> None:
        layout = controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout]
        _keydown(layout["keys_pause_unpause"][0])
        assert selector.loop() == -1

    def test_clicking_a_button_returns_its_index(self, selector: Selector,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
        target = selector.buttons[2]
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: target.rect.center)
        monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button = 1))
        assert selector.loop() == 2

    def test_a_gamepad_nudge_on_the_arrow_row_cycles_immediately(
            self, selector: Selector, mouse_away, controller, gamepad) -> None:
        controller.gamepad = gamepad
        controller.set_gamepad_layout("XBOX")
        layout = controller.GAMEPAD_LAYOUTS["XBOX"]
        selector.focused_index = 0
        gamepad.axes[layout["axis_horiz"]] = Menu.JOYSTICK_TOLERANCE * 2
        assert selector.loop() == 1


# --------------------------------------------------------------------------- #
# fades
# --------------------------------------------------------------------------- #
@pytest.mark.slow
class TestFades:
    @pytest.fixture(autouse = True)
    def _no_sleeping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import time as time_module
        monkeypatch.setattr(time_module, "sleep", lambda _: None)

    def test_fade_in_ends_fully_visible(self, menu: Menu, mouse_away) -> None:
        menu.fade_in()
        assert menu.clear_normal is not None

    def test_fade_in_snaps_on_a_key_press(self, menu: Menu, mouse_away) -> None:
        _keydown(pygame.K_SPACE)
        menu.fade_in()
        assert menu.screen_normal.get_alpha() == 248

    def test_fade_out_without_a_captured_backdrop_returns_early(self, menu: Menu,
                                                                mouse_away) -> None:
        menu.clear_normal = None
        menu.fade_out()

    def test_fade_out_runs_after_a_fade_in(self, menu: Menu, mouse_away) -> None:
        menu.fade_in()
        menu.fade_out()
        assert menu.screen_normal.get_alpha() <= 8

    def test_fading_music_loads_the_first_track_when_nothing_is_playing(
            self, controller, click_items, monkeypatch: pytest.MonkeyPatch) -> None:
        loaded: list = []
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: False)
        monkeypatch.setattr(pygame.mixer.music, "load", lambda p: loaded.append(p))
        monkeypatch.setattr(pygame.mixer.music, "set_endevent", lambda e: None)
        monkeypatch.setattr(pygame.mixer.music, "play", lambda **k: None)
        monkeypatch.setattr(pygame.mixer.music, "queue", lambda p: None)

        menu = Menu(controller, None, click_items,
                    music = ["track_one.mp3", "track_two.mp3"])
        menu.fade_music()
        assert loaded

    def test_fading_music_fades_out_whatever_is_playing(self, controller, click_items,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
        faded: list = []
        monkeypatch.setattr(pygame.mixer.music, "get_busy", lambda: True)
        monkeypatch.setattr(pygame.mixer.music, "fadeout", lambda ms: faded.append(ms))
        monkeypatch.setattr(pygame.mixer.music, "unload", lambda: None)

        menu = Menu(controller, None, click_items, music = ["track_one.mp3"])
        menu.fade_music()
        assert faded == [1000]

    def test_fading_music_with_no_playlist_is_a_no_op(self, menu: Menu) -> None:
        menu.fade_music()
