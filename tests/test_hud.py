"""Tests for ``HUD`` -- health bars, ability icons and the mission timer."""

from __future__ import annotations

import pygame
import pytest

from HUD import HUD


@pytest.fixture
def window(surface: pygame.Surface) -> pygame.Surface:
    """Draw onto a per-test alpha surface rather than the shared display.

    The display surface created by ``set_mode`` has no alpha channel, so every pixel
    reads back at alpha 255 and "nothing was drawn here" becomes unassertable.
    """
    return surface


@pytest.fixture
def hud(player, window: pygame.Surface) -> HUD:
    return HUD(player, window)


class TestConstruction:
    def test_every_ability_icon_is_loaded(self, hud: HUD) -> None:
        for attr in ("icon_jump", "icon_double_jump", "icon_block", "icon_teleport",
                     "icon_wall_jump", "icon_resize", "icon_bullet_time", "save_icon"):
            assert getattr(hud, attr) is not None

    def test_the_timer_glyphs_cover_digits_and_punctuation(self, hud: HUD) -> None:
        assert set("0123456789") <= set(hud.time_characters)
        assert "COLON" in hud.time_characters
        assert "DECIMAL" in hud.time_characters

    def test_the_layout_is_scaled_against_a_1920x1080_reference(
            self, hud: HUD, window: pygame.Surface) -> None:
        assert hud.scale_factor == (window.get_width() / 1920, window.get_height() / 1080)

    def test_the_timer_starts_at_zero(self, hud: HUD) -> None:
        assert hud.old_time == "00:00.000"
        assert len(hud.time_display) == 9

    def test_a_retro_hud_tints_its_glyphs(self, player, window) -> None:
        plain = HUD(player, window)
        retro = HUD(player, window, retro = True)
        assert plain.time_characters["0"].get_at((2, 2)) != \
               retro.time_characters["0"].get_at((2, 2))


class TestObjectiveBanner:
    def test_activating_renders_the_text_and_its_capsule(self, hud: HUD) -> None:
        hud.activate_objective("Find the exit")
        assert hud.objective is not None
        assert hud.objective_capsule is not None

    def test_the_capsule_widens_with_the_text(self, hud: HUD) -> None:
        hud.activate_objective("Go")
        narrow = hud.objective_capsule.get_width()
        hud.activate_objective("Go somewhere considerably further away than that")
        assert hud.objective_capsule.get_width() > narrow

    def test_the_banner_is_drawn_in_the_top_right(self, hud: HUD,
                                                  window: pygame.Surface) -> None:
        hud.activate_objective("Find the exit")
        hud.draw("00:00.0")
        assert window.get_at((window.get_width() - 20, hud.time_capsule.get_height() + 12)).a > 0


class TestHealthBars:
    def test_the_player_bar_is_drawn(self, hud: HUD, window: pygame.Surface) -> None:
        hud.draw("00:00.0")
        assert window.get_at((14, 14)).a > 0

    def test_the_bar_shrinks_as_health_drops(self, hud: HUD, player) -> None:
        hud.draw("00:00.0")
        full = hud.hp_bar.get_width()
        player.hp = player.max_hp / 4
        hud.draw("00:00.0")
        assert hud.hp_bar.get_width() < full

    def test_the_bar_never_reaches_zero_width(self, hud: HUD, player) -> None:
        player.hp = 0
        hud.draw("00:00.0")
        assert hud.hp_pct == 0.01

    def test_the_boss_bar_appears_only_when_a_percentage_is_published(
            self, hud: HUD) -> None:
        hud.draw("00:00.0")
        assert hud.boss_hp_bar is None
        hud.boss_hp_pct = 0.5
        hud.draw("00:00.0")
        assert hud.boss_hp_bar is not None

    def test_the_boss_bar_fades_in(self, hud: HUD) -> None:
        hud.boss_hp_pct = 1.0
        hud.draw("00:00.0")
        first = hud.boss_hp_bar_alpha
        hud.draw("00:00.0")
        assert hud.boss_hp_bar_alpha > first

    def test_the_boss_bar_fades_out_when_the_percentage_clears(self, hud: HUD) -> None:
        hud.boss_hp_pct = 1.0
        hud.draw("00:00.0")
        hud.boss_hp_pct = None
        peak = hud.boss_hp_bar_alpha
        hud.draw("00:00.0")
        assert hud.boss_hp_bar_alpha < peak


class TestAbilityIcons:
    def test_locked_abilities_have_no_icon(self, hud: HUD, player,
                                           window: pygame.Surface) -> None:
        hud.draw("00:00.0")
        # The teleport slot sits at x ~ 140 * scale; with the ability locked it is clear.
        x = int(140 * hud.scale_factor[0]) + 4
        y = int(28 * hud.scale_factor[1]) + 4
        assert window.get_at((x, y)).a == 0

    def test_unlocking_an_ability_shows_its_icon(self, hud: HUD, player,
                                                 window: pygame.Surface) -> None:
        player.abilities["can_teleport"] = True
        hud.draw("00:00.0")
        x = int(140 * hud.scale_factor[0]) + 4
        y = int(28 * hud.scale_factor[1]) + 4
        assert window.get_at((x, y)).a > 0

    def test_an_ability_on_cooldown_is_dimmed(self, hud: HUD, player) -> None:
        player.abilities["can_teleport"] = True
        player.cooldowns["teleport"] = 3.0
        hud.draw("00:00.0")
        assert hud.icon_teleport.get_alpha() < 255

    def test_a_spent_jump_dims_the_jump_icon(self, hud: HUD, player) -> None:
        player.jump_count = player.max_jumps
        hud.draw("00:00.0")
        assert hud.icon_jump.get_alpha() == 128


class TestTimer:
    def test_the_timer_is_drawn_for_a_normal_length_string(
            self, hud: HUD, window: pygame.Surface) -> None:
        hud.draw("01:23.4")
        assert hud.old_time == "01:23.4"

    def test_a_longer_string_is_refused(self, hud: HUD) -> None:
        # __draw_time__ bails out above 7 characters, which is what makes the
        # 100-minute overflow in Level.formatted_time visible as a missing clock.
        hud.draw("100:23.4")
        assert hud.old_time == "00:00.000"

    def test_only_the_changed_glyphs_are_swapped(self, hud: HUD) -> None:
        hud.draw("01:23.4")
        before = list(hud.time_display)
        hud.draw("01:23.5")
        changed = [i for i, (a, b) in enumerate(zip(before, hud.time_display)) if a is not b]
        assert changed == [6]


class TestSaveIndicator:
    def test_the_save_icon_is_hidden_by_default(self, hud: HUD,
                                                window: pygame.Surface) -> None:
        hud.draw("00:00.0")
        x = int(window.get_width() * 0.94) + 4
        y = int(window.get_height() - (window.get_width() * 0.06)) + 4
        assert window.get_at((x, y)).a == 0

    def test_the_save_icon_appears_while_the_timer_runs(self, hud: HUD,
                                                        window: pygame.Surface) -> None:
        hud.save_icon_timer = 1.0
        hud.draw("00:00.0")
        x = int(window.get_width() * 0.94) + 4
        y = int(window.get_height() - (window.get_width() * 0.06)) + 4
        assert window.get_at((x, y)).a > 0


def test_a_retro_hud_draws_its_border(player, window: pygame.Surface) -> None:
    retro = HUD(player, window, retro = True)
    retro.draw("00:00.0")
    assert window.get_at((2, window.get_height() // 2)).a > 0
