"""Tests for ``Projectile`` -- travel, range clamping and impact."""

from __future__ import annotations

import math

import pygame
import pytest

from Projectile import Projectile


@pytest.fixture
def bullet_sprite(sprite_master) -> pygame.Surface:
    from Helpers import load_sprite_sheets
    return load_sprite_sheets("Projectiles", "Bullet", sprite_master)["BULLET"][0]


@pytest.fixture
def make_projectile(level, controller, player, bullet_sprite):
    def _make(x: float = 200, y: float = 200, target = (600, 200),
              max_dist: float = 500, damage: float = 10, difficulty: float = 1.0,
              **kwargs) -> Projectile:
        return Projectile(level, controller, x, y, target, max_dist, damage,
                          difficulty, sprite = bullet_sprite, **kwargs)
    return _make


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
class TestConstruction:
    def test_it_is_centred_on_its_spawn_point(self, make_projectile) -> None:
        assert make_projectile(x = 200, y = 300).rect.center == (200, 300)

    def test_speed_scales_with_sprite_size_and_difficulty(self, make_projectile,
                                                          bullet_sprite) -> None:
        ratio = Projectile.STOCK_PROJECTILE_SIZE / bullet_sprite.get_width()
        expected = (0.75 * Projectile.MAX_SPEED * ratio) + \
                   (0.25 * Projectile.MAX_SPEED * 1.0 * ratio)
        assert make_projectile().speed == pytest.approx(expected)

    def test_a_harder_difficulty_makes_a_faster_bullet(self, make_projectile) -> None:
        assert make_projectile(difficulty = 2.0).speed > make_projectile().speed

    def test_a_missing_target_aims_at_twice_the_spawn_point(self, make_projectile) -> None:
        # A degenerate fallback -- (x*2, y*2) -- but it keeps the constructor total.
        # clamp_target then rescales that point out to max_dist along the same bearing.
        bullet = make_projectile(x = 100, y = 100, target = None, max_dist = 10_000)
        assert bullet.target[0] == bullet.target[1]
        assert bullet.angle == pytest.approx(45)

    def test_the_sprite_is_rotated_to_face_the_target(self, make_projectile,
                                                      bullet_sprite) -> None:
        up = make_projectile(x = 300, y = 300, target = (300, 0))
        assert up.angle == pytest.approx(-90)
        assert up.sprite is not bullet_sprite

    def test_a_mask_is_built_for_collision(self, make_projectile) -> None:
        assert make_projectile().mask is not None

    def test_a_spriteless_projectile_degrades_gracefully(self, level, controller,
                                                         player) -> None:
        bullet = Projectile(level, controller, 10, 10, (50, 10), 100, 5, 1.0)
        assert bullet.speed == 0
        assert bullet.sprite is None
        assert bullet.mask is None


# --------------------------------------------------------------------------- #
# interpolation and range
# --------------------------------------------------------------------------- #
class TestLerp:
    def test_scalar_interpolation(self) -> None:
        assert Projectile.__lerp_point__(0, 100, 0.25) == 25
        assert Projectile.__lerp_point__(100, 0, 0.5) == 50

    def test_point_interpolation_returns_ints(self, make_projectile) -> None:
        assert make_projectile().lerp((0, 0), (10, 20), 0.5) == (5, 10)


class TestClampTarget:
    def test_a_far_target_is_pulled_back_to_the_range_limit(self,
                                                            make_projectile) -> None:
        bullet = make_projectile(x = 0, y = 0, target = (10_000, 0), max_dist = 500)
        assert math.dist(bullet.rect.center, bullet.target) == pytest.approx(500, abs = 2)

    def test_a_near_target_is_pushed_out_to_the_range_limit(self,
                                                            make_projectile) -> None:
        # clamp_target always rescales to max_dist -- it is a range, not a cap.
        bullet = make_projectile(x = 0, y = 0, target = (10, 0), max_dist = 500)
        assert math.dist(bullet.rect.center, bullet.target) == pytest.approx(500, abs = 2)

    def test_a_target_on_top_of_the_muzzle_is_left_alone(self, make_projectile) -> None:
        bullet = make_projectile(x = 100, y = 100, target = (100, 100), max_dist = 500)
        assert bullet.target == (100, 100)


# --------------------------------------------------------------------------- #
# movement
# --------------------------------------------------------------------------- #
class TestMove:
    def test_it_travels_towards_its_target(self, make_projectile) -> None:
        # y = 600 keeps the flight path clear of the player, who spawns near the top.
        bullet = make_projectile(x = 100, y = 600, target = (900, 600))
        bullet.move(50)
        assert bullet.rect.centerx > 100

    def test_arriving_destroys_it(self, make_projectile) -> None:
        bullet = make_projectile(x = 100, y = 600, target = (900, 600))
        for _ in range(200):
            bullet.move(20)
            if bullet.hp == 0:
                break
        assert bullet.hp == 0

    def test_a_step_larger_than_the_remaining_range_lands_on_the_target(
            self, make_projectile) -> None:
        """The lerp weight is clamped at 1, so a huge step arrives instead of overshooting.

        Real frame times keep the step well below the range; this bites on a long
        stall or a very fast projectile.
        """
        bullet   = make_projectile(x = 100, y = 600, target = (900, 600))
        target_x = bullet.target[0]
        bullet.move(10_000)
        assert bullet.rect.centerx == target_x
        assert bullet.hp == 0

    def test_hitting_the_player_damages_them_and_destroys_the_bullet(
            self, make_projectile, player) -> None:
        bullet = make_projectile(x = player.rect.centerx, y = player.rect.centery,
                                 target = (900, player.rect.centery))
        before = player.hp
        bullet.move(10)
        assert bullet.hp == 0
        assert player.hp < before

    def test_hitting_a_block_destroys_it_without_moving_on(self, make_projectile,
                                                           make_block, level) -> None:
        block  = make_block(col = 5, row = 5)
        bullet = make_projectile(x = block.rect.centerx, y = block.rect.centery,
                                 target = (900, block.rect.centery))
        position = bullet.rect.center
        bullet.move(50)
        assert bullet.hp == 0
        assert bullet.rect.center == position

    def test_a_spriteless_projectile_cannot_move(self, level, controller, player) -> None:
        bullet = Projectile(level, controller, 10, 10, (500, 10), 100, 5, 1.0)
        before = bullet.rect.center
        bullet.move(100)
        assert bullet.rect.center == before


class TestLoop:
    def test_the_loop_advances_the_bullet(self, make_projectile) -> None:
        bullet = make_projectile(x = 100, y = 600, target = (900, 600))
        before = bullet.rect.centerx
        bullet.loop(0.05)
        assert bullet.rect.centerx > before

    def test_bullet_time_halves_the_distance_covered(self, make_projectile,
                                                     player) -> None:
        fast = make_projectile(x = 100, y = 600, target = (900, 600))
        fast.loop(0.05)
        travelled_fast = fast.rect.centerx - 100

        player.is_slow_time = True
        slow = make_projectile(x = 100, y = 600, target = (900, 600))
        slow.loop(0.05)
        travelled_slow = slow.rect.centerx - 100

        assert travelled_slow < travelled_fast

    def test_the_loop_reports_no_time_offset(self, make_projectile) -> None:
        assert make_projectile().loop(0.016) == 0.0


# --------------------------------------------------------------------------- #
# impact, difficulty, persistence
# --------------------------------------------------------------------------- #
class TestImpactAndPersistence:
    def test_collide_destroys_the_projectile_and_reports_a_hit(self, make_projectile,
                                                               player) -> None:
        bullet = make_projectile()
        assert bullet.collide(player) is True
        assert bullet.hp == 0

    def test_set_difficulty_rescales_the_speed(self, make_projectile) -> None:
        easy = make_projectile(difficulty = 1.0)
        easy.set_difficulty(2.0)
        assert easy.speed == pytest.approx(make_projectile(difficulty = 2.0).speed)

    def test_repeated_difficulty_changes_do_not_compound(self, make_projectile) -> None:
        bullet = make_projectile(difficulty = 1.0)
        before = bullet.speed
        bullet.set_difficulty(2.0)
        bullet.set_difficulty(1.0)
        assert bullet.speed == pytest.approx(before)

    def test_save_captures_flight_state(self, make_projectile) -> None:
        bullet  = make_projectile()
        payload = bullet.save()[bullet.name]
        assert payload["cached x y"] == (bullet.rect.x, bullet.rect.y)
        assert payload["speed"] == bullet.speed
        assert payload["angle"] == bullet.angle

    def test_load_restores_flight_state(self, make_projectile) -> None:
        bullet = make_projectile()
        bullet.load({"hp": 40, "cached x y": (11, 22), "speed": 99.5,
                     "max_dist": 250, "angle": 45.0})
        assert bullet.rect.topleft == (11, 22)
        assert (bullet.hp, bullet.speed, bullet.max_dist, bullet.angle) == \
               (40, 99.5, 250, 45.0)

    def test_a_round_trip_keeps_the_bullet_on_course(self, make_projectile) -> None:
        bullet  = make_projectile(x = 100, y = 600, target = (900, 600))
        payload = bullet.save()[bullet.name]
        bullet.rect.topleft = (0, 0)
        bullet.load(payload)
        assert bullet.rect.topleft == tuple(payload["cached x y"])
