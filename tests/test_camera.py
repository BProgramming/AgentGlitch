"""Tests for ``Camera`` -- focus tracking, offset clamping and layer composition."""

from __future__ import annotations

import time

import pygame
import pytest

from Camera import Camera
from HUD import HUD


@pytest.fixture
def camera(window: pygame.Surface) -> Camera:
    return Camera(window)


@pytest.fixture
def hud(player, window: pygame.Surface) -> HUD:
    return HUD(player, window)


@pytest.fixture
def prepared(camera: Camera, level, hud: HUD, player) -> Camera:
    """A camera attached to a level whose background tiles across the map."""
    level.background = "Test.png"
    camera.prepare(level, hud)
    return camera


class TestConstruction:
    def test_the_viewport_matches_the_window(self, camera: Camera,
                                             window: pygame.Surface) -> None:
        assert camera.width == window.get_width()
        assert camera.height == window.get_height()

    def test_the_scroll_margins_are_fractions_of_the_viewport(self,
                                                              camera: Camera) -> None:
        assert camera.scroll_width == camera.width * Camera.SCROLL_AREA_WIDTH_PCT_FIXED
        assert camera.scroll_height == camera.height * Camera.SCROLL_AREA_HEIGHT_PCT_FIXED

    def test_it_starts_unattached(self, camera: Camera) -> None:
        assert camera.level is None
        assert camera.hud is None
        assert (camera.offset_x, camera.offset_y) == (0.0, 0.0)


class TestFocus:
    def test_focus_point_sets_the_focus_directly(self, camera: Camera) -> None:
        camera.focus_point(100, 200)
        assert (camera.focus_x, camera.focus_y) == (100, 200)

    def test_a_player_focused_camera_snaps_to_the_player(self, prepared: Camera,
                                                         player) -> None:
        assert prepared.scroll_to_player(0.016) is True
        assert prepared.focus_x == player.rect.centerx
        assert prepared.focus_y == player.rect.centery

    def test_without_a_level_there_is_nothing_to_follow(self, camera: Camera) -> None:
        assert camera.scroll_to_player(0.016) is False

    def test_a_free_camera_scrolls_towards_the_player_instead_of_snapping(
            self, prepared: Camera, player) -> None:
        prepared.focus_player = False
        prepared.focus_point(0, 0)
        assert prepared.scroll_to_player(0.016) is False
        assert prepared.focus_x > 0


class TestScrollToPoint:
    def test_it_advances_towards_the_target(self, prepared: Camera) -> None:
        prepared.focus_point(0, 0)
        prepared.scroll_to_point(0.1, 1000, 0)
        assert 0 < prepared.focus_x <= 1000

    def test_the_step_size_follows_the_scroll_speed(self, prepared: Camera) -> None:
        prepared.focus_point(0, 0)
        prepared.scroll_to_point(0.1, 10_000, 0)
        assert prepared.focus_x == pytest.approx(0.1 * Camera.SCROLL_SPEED, rel = 0.01)

    def test_it_does_not_overshoot(self, prepared: Camera) -> None:
        prepared.focus_point(0, 0)
        prepared.scroll_to_point(10.0, 100, 50)
        assert (prepared.focus_x, prepared.focus_y) == (100, 50)

    def test_arriving_reports_success_when_no_dwell_is_required(self,
                                                                prepared: Camera) -> None:
        prepared.focus_point(100, 50)
        assert prepared.scroll_to_point(0.016, 100, 50) is True

    def test_a_dwell_time_holds_the_camera_before_reporting_success(
            self, prepared: Camera) -> None:
        prepared.focus_point(100, 50)
        assert prepared.scroll_to_point(0.5, 100, 50, target_wait_time = 1.0) is False
        assert prepared.scroll_to_point(0.6, 100, 50, target_wait_time = 1.0) is True

    def test_moving_again_resets_the_dwell_timer(self, prepared: Camera) -> None:
        prepared.focus_point(100, 50)
        prepared.scroll_to_point(0.5, 100, 50, target_wait_time = 10.0)
        prepared.scroll_to_point(0.1, 900, 50, target_wait_time = 10.0)
        assert prepared.scroll_wait_time == 0


class TestOffsetClamping:
    def test_the_offset_never_goes_past_the_left_edge(self, prepared: Camera) -> None:
        prepared.focus_point(0, 0)
        prepared.__update_offset__()
        assert prepared.offset_x >= prepared.level.level_bounds[0][0]

    def test_the_offset_never_goes_past_the_right_edge(self, prepared: Camera,
                                                       level) -> None:
        prepared.focus_point(level.level_bounds[1][0], level.level_bounds[1][1])
        prepared.__update_offset__()
        assert prepared.offset_x <= level.level_bounds[1][0] - prepared.width

    def test_without_level_bounds_the_offset_is_left_alone(self, camera: Camera) -> None:
        camera.focus_point(500, 500)
        camera.__update_offset__()
        assert (camera.offset_x, camera.offset_y) == (0.0, 0.0)


class TestLayers:
    def test_a_small_background_is_tiled_across_the_level(self, prepared: Camera,
                                                          level) -> None:
        assert len(prepared.bg_tileset) > 1

    def test_a_background_larger_than_the_level_needs_a_single_tile(
            self, camera: Camera, level, hud: HUD) -> None:
        level.background = "Wide.png"
        camera.prepare(level, hud)
        assert len(camera.bg_tileset) == 1

    def test_a_missing_background_falls_back_to_blue(self, camera: Camera, level,
                                                     hud: HUD) -> None:
        level.background = "NoSuchBackground.png"
        camera.prepare(level, hud)
        assert camera.bg_image is not None

    def test_no_foreground_is_configured_by_default(self, prepared: Camera) -> None:
        assert prepared.fg_image is None

    def test_a_configured_foreground_is_loaded(self, camera: Camera, level,
                                               hud: HUD) -> None:
        level.foreground = "Wide.png"
        camera.prepare(level, hud)
        assert camera.fg_image is not None

    def test_a_missing_foreground_is_skipped_silently(self, camera: Camera, level,
                                                      hud: HUD) -> None:
        level.foreground = "NotThere.png"
        camera.prepare(level, hud)
        assert camera.fg_image is None

    def test_retro_levels_tint_both_layers(self, camera: Camera, retro_level, player,
                                           window) -> None:
        retro_level.background = "Wide.png"
        retro_level.foreground = "Wide.png"
        camera.prepare(retro_level, HUD(player, window, retro = True))
        assert camera.bg_image is not None
        assert camera.fg_image is not None


class TestDraw:
    def test_drawing_composes_background_level_and_hud(self, camera: Camera, level,
                                                       hud: HUD, player) -> None:
        level.background = "Wide.png"
        level.foreground = "Wide.png"
        camera.prepare(level, hud)
        camera.draw(level.controller.master_volume)
        assert level.visual_effects_manager.draw_calls == 1

    def test_a_tiled_background_draws_without_a_subsurface(self, prepared: Camera,
                                                           level) -> None:
        prepared.draw(level.controller.master_volume)

    def test_the_boss_health_bar_is_handed_to_the_hud_then_cleared(
            self, prepared: Camera, level, hud: HUD) -> None:
        level.boss_hp_pct = 0
        prepared.draw(level.controller.master_volume)
        assert hud.boss_hp_pct == 0
        assert level.boss_hp_pct is None

    def test_glitch_fragments_are_blitted_over_the_top(self, prepared: Camera,
                                                       level) -> None:
        fragment = pygame.Surface((20, 20), pygame.SRCALPHA)
        fragment.fill((255, 0, 0, 255))
        prepared.draw(level.controller.master_volume, glitches = [[fragment, (0, 0)]])
        assert prepared.win.get_at((5, 5)) == pygame.Color(255, 0, 0, 255)


@pytest.mark.slow
class TestFades:
    @pytest.fixture(autouse = True)
    def _no_sleeping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The fade runs 64 frames with a 10ms sleep each; the sleep adds nothing here.
        monkeypatch.setattr(time, "sleep", lambda _: None)

    def test_fade_in_completes(self, prepared: Camera, level) -> None:
        prepared.fade_in(level.controller)

    def test_fade_out_completes_and_clears_the_window(self, prepared: Camera,
                                                      level) -> None:
        prepared.fade_out(level.controller)
        assert prepared.win.get_at((5, 5))[:3] == (0, 0, 0)


def test_a_background_smaller_than_the_window_crashes_a_small_level(
        camera: Camera, controller, player, window, hud: HUD) -> None:
    """Characterisation of a latent crash.

    When a level is small enough to need only one tile of its background,
    ``Camera.draw`` takes a window-sized subsurface of that image.  If the image is
    smaller than the window, pygame refuses -- so a compact level paired with a
    compact background image takes the game down on the first frame.  The same
    applies to *every* foreground, which is always subsurfaced.
    See BUGS_FOUND.md #20.
    """
    from support.doubles import StubLevel

    tiny = StubLevel(controller, width_blocks = 2, height_blocks = 2)
    tiny.background = "Test.png"          # 320x240, smaller than the 1280x720 window
    controller.level = tiny
    tiny.set_player(player)
    camera.prepare(tiny, hud)

    assert len(camera.bg_tileset) == 1
    with pytest.raises(ValueError):
        camera.draw(controller.master_volume)
