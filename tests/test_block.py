"""Tests for the ``Block`` family: terrain, breakables, movers, doors and hazards.

``Block`` is the base for everything solid in a level, including the hazards that
damage the player, so this file also covers ``Hazard``, ``MovingHazard`` and
``FallingHazard``.
"""

from __future__ import annotations

from pathlib import Path

import pygame
import pytest

from Block import (
    Block,
    BreakableBlock,
    FallingHazard,
    Hazard,
    MovableBlock,
    MovingBlock,
    MovingHazard,
)
from Entity import Entity
from Helpers import MovementDirection, PathPoint
from support.patches import HandledError


def _terrain(assets_root: Path) -> Path:
    return assets_root / "Terrain" / "Terrain.png"


def _path(level, *tiles: tuple[int, int]) -> list[PathPoint]:
    return [PathPoint(col * level.block_size, row * level.block_size)
            for col, row in tiles]


# --------------------------------------------------------------------------- #
# Block
# --------------------------------------------------------------------------- #
class TestBlock:
    def test_a_block_is_solid_and_sized_to_its_tile(self, make_block, level) -> None:
        block = make_block()
        assert block.is_blocking is True
        assert block.rect.size == (level.block_size, level.block_size)

    def test_blocks_barely_fall(self, make_block) -> None:
        # A block's gravity is 1% of the base so a dislodged one drifts rather than drops.
        block = make_block()
        assert block.gravity == pytest.approx(Entity.GRAVITY * 0.01)

    def test_an_undamaged_block_is_left_out_of_the_save_file(self, make_block) -> None:
        assert make_block().save() is not None      # hp is 100, not 0
        block = make_block()
        block.hp = 0
        assert block.save() is None

    def test_stacking_is_recorded_from_the_layout(self, make_block) -> None:
        assert make_block(is_stacked = True).is_stacked is True
        assert make_block(is_stacked = False).is_stacked is False

    def test_blocks_survive_a_load_by_default(self, make_block) -> None:
        assert make_block().purgeable_on_load is False


class TestLoadImage:
    def test_slices_a_half_tile_and_doubles_it(self, image_master,
                                               assets_root: Path) -> None:
        sprite = Block.load_image(_terrain(assets_root), 96, 96, image_master, 0, 0)
        assert sprite.get_size() == (96, 96)     # (96//2) * 2

    def test_the_source_sheet_is_cached(self, image_master, assets_root: Path) -> None:
        Block.load_image(_terrain(assets_root), 96, 96, image_master, 0, 0)
        Block.load_image(_terrain(assets_root), 96, 96, image_master, 48, 48)
        assert len(image_master) == 1

    def test_retro_prefers_the_retro_sheet_when_one_exists(self, image_master,
                                                           assets_root: Path) -> None:
        Block.load_image(_terrain(assets_root), 96, 96, image_master, 0, 0, retro = True)
        assert any("retro" in str(key) for key in image_master)

    def test_a_missing_sheet_is_fatal(self, image_master, assets_root: Path) -> None:
        with pytest.raises(HandledError):
            Block.load_image(assets_root / "Terrain" / "nope.png", 96, 96,
                             image_master, 0, 0)


class TestPlaySound:
    def test_plays_a_named_effect_positioned_against_the_player(
            self, make_block, player, monkeypatch: pytest.MonkeyPatch) -> None:
        played: list = []

        class _Channel:
            def play(self, sound): played.append(sound)
            def set_volume(self, *a): pass

        monkeypatch.setattr(pygame.mixer, "find_channel", lambda *a, **k: _Channel())
        make_block().play_sound("door")
        assert len(played) == 1

    def test_an_unknown_effect_name_is_a_no_op(self, make_block, player,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pygame.mixer, "find_channel",
                            lambda *a, **k: pytest.fail("should not reach the mixer"))
        make_block().play_sound("no_such_sound")


# --------------------------------------------------------------------------- #
# BreakableBlock
# --------------------------------------------------------------------------- #
class TestBreakableBlock:
    @pytest.fixture
    def crate(self, level, controller, image_master, block_audios) -> BreakableBlock:
        crate = BreakableBlock(level, controller, 0, 0, level.block_size,
                               level.block_size, image_master, block_audios, False,
                               coord_x2 = 48, coord_y2 = 0)
        level.place_static(crate, 0, 0)
        return crate

    def test_the_first_hit_cracks_it(self, crate: BreakableBlock, player) -> None:
        crate.get_hit(player)
        assert crate.hp == crate.max_hp // 2
        assert crate.sprite is crate.sprite_damaged

    def test_the_second_hit_destroys_it_and_bursts(self, crate: BreakableBlock, player,
                                                   vfx) -> None:
        crate.get_hit(player)
        crate.cooldowns["get_hit"] = 0
        crate.get_hit(player)
        assert crate.hp == 0
        assert "BREAKBURST" in vfx.image_names

    def test_hits_are_rate_limited(self, crate: BreakableBlock, player) -> None:
        crate.get_hit(player)
        crate.get_hit(player)                    # still on cooldown
        assert crate.hp == crate.max_hp // 2

    def test_the_mask_is_refreshed_with_the_damaged_sprite(self, crate: BreakableBlock,
                                                           player) -> None:
        crate.get_hit(player)
        assert crate.mask.get_size() == crate.sprite_damaged.get_size()

    def test_a_destroyed_crate_does_not_come_back_on_load(self,
                                                          crate: BreakableBlock) -> None:
        assert crate.purgeable_on_load is True


# --------------------------------------------------------------------------- #
# MovingBlock
# --------------------------------------------------------------------------- #
class TestMovingBlock:
    @pytest.fixture
    def lift(self, level, controller, image_master, block_audios) -> MovingBlock:
        block = MovingBlock(level, controller, 0, 3 * level.block_size,
                            level.block_size, level.block_size, image_master,
                            block_audios, False, speed = 200,
                            path = _path(level, (0, 3), (3, 3)))
        level.blocks.append(block)
        level.dynamic_blocks.append(block)
        return block

    def test_the_index_advances_and_reverses_at_the_ends(self, lift: MovingBlock) -> None:
        lift.patrol_path_index = 0
        lift.increment_patrol_index()
        assert lift.patrol_path_index == -1      # two-point path reverses immediately
        lift.increment_patrol_index()
        assert lift.patrol_path_index == 0

    def test_patrol_drives_towards_the_waypoint(self, lift: MovingBlock) -> None:
        lift.patrol_path_index = 1
        lift.patrol(0.016)
        assert lift.should_move_horiz is True
        assert lift.direction is MovementDirection.RIGHT
        assert lift.x_vel > 0

    def test_patrol_speed_is_capped(self, lift: MovingBlock) -> None:
        lift.patrol_path_index = 1
        lift.patrol(1.0)
        assert abs(lift.x_vel) <= abs(lift.speed)

    def test_arriving_at_a_wait_point_starts_the_pause(self, lift: MovingBlock) -> None:
        lift.patrol_path[0].wait = True
        lift.patrol_path_index   = 0
        lift.rect.topleft = (int(lift.patrol_path[0].x), int(lift.patrol_path[0].y))
        lift.patrol(0.016)
        assert lift.cooldowns["wait"] == MovingBlock.PATH_STOP_TIME

    def test_a_waiting_block_does_not_move(self, lift: MovingBlock) -> None:
        lift.cooldowns["wait"] = 1.0
        lift.patrol(0.016)
        assert lift.should_move_horiz is False
        assert lift.should_move_vert is False

    def test_a_rider_inherits_the_blocks_velocity(self, lift: MovingBlock,
                                                  player) -> None:
        lift.x_vel = 150
        lift.y_vel = -50
        player.rect.y = lift.rect.y - 10        # standing on top
        lift.collide(player)
        assert player.push_x == 150
        assert player.push_y == -50

    def test_a_held_block_releases_when_the_player_arrives(self, lift: MovingBlock,
                                                           player) -> None:
        lift.hold = True
        lift.collide(player)
        assert lift.hold is False

    def test_a_held_block_stays_put(self, lift: MovingBlock, player) -> None:
        lift.hold  = True
        lift.x_vel = 100
        lift.should_move_horiz = True
        before = lift.rect.x
        lift.loop(0.1)
        assert lift.rect.x == before

    def test_a_disabled_block_stays_put(self, lift: MovingBlock, player) -> None:
        lift.is_enabled = False
        lift.x_vel = 100
        before = lift.rect.x
        lift.loop(0.1)
        assert lift.rect.x == before

    def test_bullet_time_halves_the_speed(self, lift: MovingBlock, player) -> None:
        player.is_slow_time = True
        lift.x_vel = 200
        lift.should_move_horiz = True
        lift.loop(0.1)
        assert lift.x_vel == 100

    def test_movement_stops_at_the_level_edges(self, lift: MovingBlock, level,
                                               player) -> None:
        lift.move(-10_000, 0)
        assert lift.rect.left == lift.rect.width
        assert lift.x_vel == 0.0

    def test_vertical_travel_is_clamped_to_the_waypoint(self, lift: MovingBlock) -> None:
        lift.patrol_path_index = 1
        lift.y_vel = 500
        lift.move(0, 10_000)
        assert lift.rect.y == int(lift.patrol_path[1].y)


# --------------------------------------------------------------------------- #
# Door
# --------------------------------------------------------------------------- #
class TestDoor:
    def test_a_door_starts_shut_and_stacked(self, make_door) -> None:
        door = make_door()
        assert door.is_open is False
        assert door.is_stacked is True

    def test_opening_retargets_the_door_to_its_open_position(self, make_door,
                                                             player) -> None:
        door = make_door()
        door.open()
        assert door.is_open is True
        assert door.patrol_path is door.patrol_path_open

    def test_a_locked_door_refuses_to_open(self, make_door, player) -> None:
        door = make_door(is_locked = True)
        door.open()
        assert door.is_open is False

    def test_closing_retargets_the_door_back(self, make_door, player) -> None:
        door = make_door()
        door.open()
        door.close()
        assert door.is_open is False
        assert door.patrol_path is door.patrol_path_closed

    def test_toggle_opens_then_closes(self, make_door, player) -> None:
        door = make_door()
        door.toggle_open()
        assert door.is_open is True
        door.toggle_open()
        assert door.is_open is False

    def test_toggle_cannot_open_a_locked_door(self, make_door, player) -> None:
        door = make_door(is_locked = True)
        door.toggle_open()
        assert door.is_open is False

    def test_unlocking_swaps_to_the_unlocked_sprite(self, make_door) -> None:
        door = make_door(is_locked = True, locked_coord_x = 0, locked_coord_y = 0,
                         unlocked_coord_x = 48, unlocked_coord_y = 0)
        door.unlock()
        assert door.is_locked is False
        assert door.sprite is door.unlocked_sprite
        assert door.mask is door.unlocked_mask

    def test_locking_swaps_back(self, make_door) -> None:
        door = make_door(locked_coord_x = 0, locked_coord_y = 0,
                         unlocked_coord_x = 48, unlocked_coord_y = 0)
        door.lock()
        assert door.is_locked is True
        assert door.sprite is door.locked_sprite

    def test_toggle_lock_flips_the_state(self, make_door) -> None:
        door = make_door()
        door.toggle_lock()
        assert door.is_locked is True
        door.toggle_lock()
        assert door.is_locked is False

    def test_an_entity_that_can_open_doors_opens_it_on_contact(self, make_door,
                                                               player) -> None:
        door = make_door()
        player.rect.bottom = door.rect.top + 10
        door.collide(player)
        assert door.is_open is True

    def test_an_entity_below_the_doorway_does_not_open_it(self, make_door,
                                                          player) -> None:
        door = make_door()
        player.rect.bottom = door.rect.top - 10
        door.collide(player)
        assert door.is_open is False

    def test_an_entity_without_the_ability_does_not_open_it(self, make_door, level,
                                                            controller) -> None:
        door  = make_door()
        plain = Entity(level, controller, door.rect.x, door.rect.y, 32, 32)
        door.collide(plain)
        assert door.is_open is False

    def test_a_shut_door_at_rest_short_circuits_its_loop(self, make_door,
                                                         player) -> None:
        door = make_door()
        assert door.loop(0.016) == 0.0

    def test_an_open_door_closes_once_the_player_walks_away(self, make_door,
                                                            player) -> None:
        door = make_door(col = 6, row = 6)
        door.open()
        player.rect.topleft = (0, 0)
        door.loop(0.016)
        assert door.is_open is False

    def test_an_open_door_stays_open_while_the_player_is_close(self, make_door,
                                                               player) -> None:
        door = make_door(col = 6, row = 6)
        door.open()
        player.rect.center = door.rect.center
        door.loop(0.016)
        assert door.is_open is True


# --------------------------------------------------------------------------- #
# MovableBlock
# --------------------------------------------------------------------------- #
class TestMovableBlock:
    @pytest.fixture
    def crate(self, level, controller, image_master, block_audios) -> MovableBlock:
        crate = MovableBlock(level, controller, 3 * level.block_size,
                             3 * level.block_size, level.block_size, level.block_size,
                             image_master, block_audios, False)
        level.blocks.append(crate)
        level.dynamic_blocks.append(crate)
        return crate

    def test_it_remembers_where_it_started(self, crate: MovableBlock, level) -> None:
        assert (crate.start_x, crate.start_y) == (3 * level.block_size,
                                                  3 * level.block_size)

    def test_it_passes_its_velocity_to_whatever_touches_it(self, crate: MovableBlock,
                                                           player) -> None:
        crate.x_vel = 90
        crate.collide(player)
        assert player.push_x == 90

    def test_vertical_push_only_applies_from_above(self, crate: MovableBlock,
                                                   player) -> None:
        crate.y_vel = 40
        player.rect.bottom = crate.rect.top       # player standing on it
        crate.collide(player)
        assert player.push_y == 40

        player.push_y = 0
        player.rect.bottom = crate.rect.bottom + 100
        crate.collide(player)
        assert player.push_y == 0

    def test_a_neighbouring_block_stops_horizontal_motion(self, crate: MovableBlock,
                                                          make_block, level,
                                                          player) -> None:
        make_block(col = 4, row = 3)
        crate.x_vel = 100
        crate.rect.right = 4 * level.block_size + 1
        crate.get_collisions()
        assert crate.should_move_horiz is False

    def test_gravity_accumulates_while_unsupported(self, crate: MovableBlock,
                                                   player) -> None:
        crate.loop(0.1)
        assert crate.y_vel > 0

    def test_the_push_decays_frame_by_frame(self, crate: MovableBlock, player) -> None:
        crate.push_x = 100
        crate.loop(0.1)
        assert 0 < crate.push_x < 100

    def test_falling_off_the_map_returns_it_to_its_start(self, crate: MovableBlock,
                                                         level) -> None:
        crate.rect.top = level.level_bounds[1][1]
        crate.move(0, 10)
        assert (crate.rect.x, crate.rect.y) == (crate.start_x, crate.start_y)


# --------------------------------------------------------------------------- #
# Hazard
# --------------------------------------------------------------------------- #
class TestHazard:
    def test_hazards_are_always_attacking(self, make_hazard) -> None:
        assert make_hazard().is_attacking is True

    def test_damage_scales_with_difficulty(self, make_hazard) -> None:
        assert make_hazard(difficulty = 2.0).attack_damage == Hazard.ATTACK_DAMAGE * 2

    def test_set_difficulty_rescales_the_damage(self, make_hazard) -> None:
        hazard = make_hazard(difficulty = 1.0)
        hazard.set_difficulty(3.0)
        assert hazard.attack_damage == Hazard.ATTACK_DAMAGE * 3

    def test_hit_sides_are_normalised_to_upper_case(self, make_hazard) -> None:
        assert make_hazard(hit_sides = "ud").hit_sides == "UD"

    def test_a_spriteless_hazard_falls_back_to_its_terrain_tile(self, make_hazard) -> None:
        hazard = make_hazard(sprite = None)
        assert hazard.sprite is not None

    def test_the_animation_advances_with_real_frame_times(self, make_hazard) -> None:
        # Unlike Actor.loop, Hazard.loop adds the raw float -- so hazards do animate.
        hazard = make_hazard()
        hazard.loop(1 / 150)
        assert hazard.animation_count > 0

    def test_update_sprite_cycles_and_wraps(self, make_hazard) -> None:
        hazard = make_hazard()
        hazard.animation_count = 0
        assert hazard.update_sprite() == 0
        hazard.animation_count = Hazard.ANIMATION_DELAY
        assert hazard.update_sprite() == 1
        hazard.animation_count = Hazard.ANIMATION_DELAY * len(hazard.sprites)
        assert hazard.update_sprite() == 0

    def test_update_geo_resyncs_rect_and_mask(self, make_hazard) -> None:
        hazard = make_hazard()
        hazard.update_sprite()
        hazard.update_geo()
        assert hazard.rect.size == hazard.sprite.get_size()

    def test_drawing_advances_the_animation_on_screen(self, make_hazard, surface) -> None:
        hazard = make_hazard()
        hazard.rect.topleft = (10, 10)
        hazard.draw(surface, 0, 0, {})
        assert surface.get_at((12, 12)).a > 0

    def test_an_off_screen_hazard_is_culled(self, make_hazard, surface) -> None:
        hazard = make_hazard()
        hazard.rect.topleft = (-5000, -5000)
        hazard.draw(surface, 0, 0, {})
        assert surface.get_at((0, 0)).a == 0


class TestMovingHazard:
    @pytest.fixture
    def saw(self, level, controller, image_master, sprite_master,
            block_audios) -> MovingHazard:
        hazard = MovingHazard(level, controller, 0, 3 * level.block_size,
                              level.block_size, level.block_size, image_master,
                              sprite_master, block_audios, 1.0, False, speed = 150,
                              path = _path(level, (0, 3), (3, 3)), sprite = "TestAnim")
        level.hazards.append(hazard)
        return hazard

    def test_it_is_both_a_mover_and_a_hazard(self, saw: MovingHazard) -> None:
        assert isinstance(saw, MovingBlock)
        assert isinstance(saw, Hazard)
        assert saw.is_attacking is True

    def test_it_travels_along_its_path(self, saw: MovingHazard, player) -> None:
        saw.patrol_path_index = 1
        saw.patrol(0.016)
        before = saw.rect.x
        saw.loop(0.1)
        assert saw.rect.x > before

    def test_it_is_purged_as_a_hazard_not_a_block(self, saw: MovingHazard, level) -> None:
        level.queue_purge(saw)
        assert saw in level.purge_queue["hazards"]


class TestFallingHazard:
    @pytest.fixture
    def crusher(self, level, controller, image_master, sprite_master,
                block_audios) -> FallingHazard:
        hazard = FallingHazard(level, controller, 2 * level.block_size,
                               1 * level.block_size, level.block_size,
                               level.block_size, image_master, sprite_master,
                               block_audios, 1.0, sprite = "TestAnim",
                               drop_x = 2 * level.block_size,
                               drop_y = 6 * level.block_size, fire_once = False)
        level.hazards.append(hazard)
        level.falling_hazards[2] = [hazard]
        return hazard

    def test_it_waits_above_the_player(self, crusher: FallingHazard, player) -> None:
        player.rect.topleft = (0, 0)
        crusher.loop(0.016)
        assert crusher.has_fired is False

    def test_the_player_walking_underneath_sets_it_off(self, crusher: FallingHazard,
                                                       player, level) -> None:
        player.rect.x   = crusher.rect.x
        player.rect.top = crusher.rect.bottom + 10
        crusher.loop(0.016)
        assert crusher.has_fired is True

    def test_it_accelerates_downwards_once_triggered(self, crusher: FallingHazard,
                                                     player) -> None:
        crusher.should_fire = True
        crusher.loop(0.016)
        before = crusher.rect.y
        crusher.loop(0.1)
        assert crusher.rect.y > before

    def test_landing_on_a_block_stops_it_and_bursts(self, crusher: FallingHazard,
                                                    make_block, player, vfx,
                                                    level) -> None:
        make_block(col = 2, row = 3)
        crusher.should_fire = True
        for _ in range(40):
            crusher.loop(0.05)
            if crusher.y_vel == 0 and crusher.has_fired:
                break
        assert "LANDBURST" in vfx.image_names

    def test_a_fire_once_crusher_dies_after_its_reset_delay(self, level, controller,
                                                            image_master, sprite_master,
                                                            block_audios, player) -> None:
        hazard = FallingHazard(level, controller, 0, 0, level.block_size,
                               level.block_size, image_master, sprite_master,
                               block_audios, 1.0, sprite = "TestAnim", fire_once = True)
        hazard.has_fired = True
        hazard.cooldowns["reset_time"] = 0.01
        hazard.loop(1.0)
        assert hazard.hp == 0

    def test_a_repeating_crusher_returns_to_its_perch(self, crusher: FallingHazard,
                                                      player) -> None:
        start = (crusher.start_x, crusher.start_y)
        crusher.has_fired = True
        crusher.rect.y += 300
        crusher.cooldowns["reset_time"] = 0.01
        crusher.loop(1.0)
        assert (crusher.rect.x, crusher.rect.y) == start
        assert crusher.has_fired is False

    def test_falling_off_the_bottom_starts_the_reset_timer(self, crusher: FallingHazard,
                                                           player, level) -> None:
        crusher.has_fired = True
        crusher.rect.y    = level.level_bounds[1][1] + 1
        crusher.loop(0.016)
        assert crusher.cooldowns["reset_time"] > 0

    def test_the_sprite_shows_the_falling_frame_while_in_motion(self,
                                                                crusher: FallingHazard) -> None:
        crusher.has_fired = True
        crusher.y_vel     = 100
        assert crusher.update_sprite() == -2

    def test_the_sprite_shows_the_landed_frame_once_stopped(self,
                                                            crusher: FallingHazard) -> None:
        crusher.has_fired = True
        crusher.y_vel     = 0
        assert crusher.update_sprite() == -1

    def test_before_firing_it_animates_over_the_idle_frames(self,
                                                            crusher: FallingHazard) -> None:
        crusher.has_fired     = False
        crusher.animation_count = 0
        assert crusher.update_sprite() == 0


def test_a_moving_block_does_not_always_start_at_its_nearest_waypoint(
        level, controller, image_master, block_audios) -> None:
    """Characterisation: the nearest-waypoint search never narrows its yardstick.

    ``MovingBlock.__init__`` computes ``min_dist`` from waypoint 0 and then compares
    every waypoint against that same value without ever updating it -- so the index
    ends up on the *last* waypoint closer than waypoint 0, not the closest one.
    ``NonPlayer`` does the same search correctly, which is what makes the difference
    visible: an identical path produces a different starting index for a block than
    for a guard.  See BUGS_FOUND.md #18.
    """
    block = MovingBlock(level, controller, 0, 0, level.block_size, level.block_size,
                        image_master, block_audios, False,
                        path = _path(level, (9, 0), (1, 0), (0, 0)))
    # Waypoint 2 is the closest, but waypoint 1 is the last one that beat waypoint 0.
    assert block.patrol_path_index == 2

    far = MovingBlock(level, controller, 0, 0, level.block_size, level.block_size,
                      image_master, block_audios, False,
                      path = _path(level, (9, 0), (0, 0), (5, 0)))
    assert far.patrol_path_index == 2        # 5 tiles away, not the 0-tile waypoint
