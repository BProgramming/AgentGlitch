"""Tests for ``ParticleEffect`` and its Rain / Snow / FilmGrain presets."""

from __future__ import annotations

import random

import pygame
import pytest

from ParticleEffect import FilmGrain, ParticleEffect, ParticleType, Rain, Snow


@pytest.fixture
def static_effect(level) -> ParticleEffect:
    return ParticleEffect(level, None, 2, 2, 20, (255, 255, 255, 255), y_vel = 0.2)


@pytest.fixture
def variable_effect(level, window) -> ParticleEffect:
    return ParticleEffect(level, window, 3, 3, 5, (255, 255, 255, 255),
                          effect_type = ParticleType.VARIABLE, should_move = False)


class TestStaticEffect:
    def test_it_builds_one_surface_covering_the_level(self, static_effect, level) -> None:
        assert isinstance(static_effect.image, pygame.Surface)
        assert static_effect.image.get_size() == level.level_bounds[1]

    def test_the_type_property_reports_the_kind(self, static_effect) -> None:
        assert static_effect.type is ParticleType.STATIC

    def test_particles_actually_land_on_the_surface(self, level) -> None:
        random.seed(1)
        effect = ParticleEffect(level, None, 4, 4, 400, (255, 0, 0, 255))
        width, height = effect.image.get_size()
        assert any(effect.image.get_at((x, y)).a > 0
                   for x in range(0, width, 16) for y in range(0, height, 16))

    def test_generation_is_deterministic_for_a_fixed_seed(self, level) -> None:
        random.seed(9)
        first = ParticleEffect.generate_static_effect(2, 2, 30, (255, 255, 255, 255),
                                                      ((0, 0), (200, 200)), False)
        random.seed(9)
        second = ParticleEffect.generate_static_effect(2, 2, 30, (255, 255, 255, 255),
                                                       ((0, 0), (200, 200)), False)
        assert pygame.image.tostring(first, "RGBA") == pygame.image.tostring(second, "RGBA")


class TestVariableEffect:
    def test_it_builds_a_list_of_particle_surfaces(self, variable_effect) -> None:
        assert isinstance(variable_effect.image, list)
        assert len(variable_effect.image) == 5

    def test_the_type_property_reports_the_kind(self, variable_effect) -> None:
        assert variable_effect.type is ParticleType.VARIABLE

    def test_cycling_eventually_picks_a_different_frame(self, variable_effect) -> None:
        random.seed(4)
        start = variable_effect.image_index
        for _ in range(20):
            variable_effect.cycle_image(ParticleEffect.VARIABLE_IMAGE_DISPLAY_TIME * 2)
            if variable_effect.image_index != start:
                break
        assert variable_effect.image_index != start

    def test_cycling_waits_for_the_display_time(self, variable_effect) -> None:
        variable_effect.image_index = 0
        variable_effect.cycle_image(ParticleEffect.VARIABLE_IMAGE_DISPLAY_TIME / 10)
        assert variable_effect.image_index == 0

    def test_a_static_image_is_never_cycled(self, static_effect) -> None:
        static_effect.cycle_image(10)
        assert static_effect.image_index == 0


class TestMovement:
    def test_a_falling_layer_scrolls_downwards(self, level) -> None:
        effect = ParticleEffect(level, None, 2, 2, 5, (255, 255, 255, 255), y_vel = 120)
        effect.loop(1.0)
        assert effect.pos_y == pytest.approx(120)

    def test_the_layer_wraps_when_it_runs_off_the_bottom(self, level) -> None:
        effect = ParticleEffect(level, None, 2, 2, 5, (255, 255, 255, 255), y_vel = 120)
        effect.pos_y = effect.rect.height - 10
        effect.loop(1.0)
        assert effect.pos_y == pytest.approx(110)

    def test_a_leftward_layer_wraps_at_the_left_edge(self, level) -> None:
        effect = ParticleEffect(level, None, 2, 2, 5, (255, 255, 255, 255), x_vel = -50)
        effect.pos_x = 0
        effect.loop(1.0)
        assert effect.pos_x == pytest.approx(effect.rect.width - 50)

    def test_sub_pixel_velocities_accumulate_instead_of_truncating(
            self, static_effect) -> None:
        """The scroll position is a float, so slow layers still creep.

        ``pygame.Rect`` coordinates are integers; driving the layer straight off the
        rect truncated any per-frame delta below 1px to zero and lost it, which at
        Rain's shipped 0.2 px/s meant the weather never moved at all.
        """
        static_effect.y_vel = 0.2
        for _ in range(1000):
            static_effect.loop(1 / 150)
        assert static_effect.pos_y == pytest.approx(0.2 * 1000 / 150)

    def test_the_wrap_preserves_the_sub_pixel_remainder(self, level) -> None:
        effect = ParticleEffect(level, None, 2, 2, 5, (255, 255, 255, 255), y_vel = 100)
        effect.pos_y = effect.rect.height - 0.25
        effect.loop(0.5)
        assert effect.pos_y == pytest.approx(49.75)

    def test_a_stationary_layer_never_moves(self, variable_effect) -> None:
        before = (variable_effect.rect.x, variable_effect.rect.y)
        variable_effect.loop(5.0)
        assert (variable_effect.rect.x, variable_effect.rect.y) == before

    def test_the_loop_reports_no_time_offset(self, static_effect) -> None:
        assert static_effect.loop(0.016) == 0.0


class TestDraw:
    def test_a_scrolling_layer_is_tiled_to_cover_the_wrap_seam(self, static_effect,
                                                               surface) -> None:
        static_effect.draw(surface, 0, 0, {})

    def test_a_static_single_surface_is_blitted_at_the_origin(self, level,
                                                              surface) -> None:
        effect = ParticleEffect(level, None, 4, 4, 200, (255, 0, 0, 255),
                                should_move = False)
        effect.draw(surface, 0, 0, {})

    def test_a_variable_layer_scatters_its_particles(self, variable_effect,
                                                     surface) -> None:
        random.seed(2)
        variable_effect.draw(surface, 0, 0, {})


class TestPresets:
    def test_rain_scales_its_particle_count_to_the_level(self, level) -> None:
        rain = Rain(level)
        assert rain.y_vel > 0
        assert rain.x_vel == 0

    def test_angled_rain_drifts_sideways(self, level) -> None:
        assert Rain(level, angled = True).x_vel < 0

    def test_snow_falls_more_slowly_than_rain(self, level) -> None:
        assert Snow(level).y_vel < Rain(level).y_vel

    def test_film_grain_is_a_fixed_overlay_sized_to_the_window(self, level,
                                                               window) -> None:
        grain = FilmGrain(level, window)
        assert grain.should_move is False
        assert grain.type is ParticleType.VARIABLE

    def test_film_grain_uses_the_retro_palette_on_a_retro_level(self, retro_level,
                                                                window) -> None:
        assert FilmGrain(retro_level, window).image is not None
