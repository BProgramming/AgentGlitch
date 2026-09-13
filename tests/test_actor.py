"""Tests for ``Actor`` -- movement, jumping, damage, resizing and the animation state machine.

``Actor`` is the widest class in the game: ``Player``, ``NonPlayer`` and ``Boss`` all
inherit its physics and its ``update_state`` machine.  The tests below drive a bare
``Actor`` so the base behaviour is pinned independently of the subclass overrides.
"""

from __future__ import annotations

import math

import pygame
import pytest

from Actor import Actor, MovementState
from Entity import Entity
from Helpers import MovementDirection
from Projectile import Projectile


@pytest.fixture
def actor(level, controller, player, sprite_master, enemy_audios) -> Actor:
    """A plain actor at tile (3, 3).  ``player`` is requested so the level has one."""
    return Actor(level, controller, 3 * level.block_size, 3 * level.block_size,
                 sprite_master, enemy_audios, 1.0, level.block_size, sprite = "TestAgent")


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
class TestConstruction:
    def test_sprite_and_mask_are_loaded(self, actor: Actor) -> None:
        assert actor.sprite is not None
        assert actor.mask is not None

    def test_the_actor_is_centred_and_floored_within_its_tile(self, actor: Actor,
                                                              level) -> None:
        # build_level places entities on tile corners; Actor re-seats itself so a
        # 64px sprite sits centred on a 96px tile with its feet on the tile floor.
        tile_x, tile_y = 3 * level.block_size, 3 * level.block_size
        assert actor.rect.x == tile_x + (level.block_size - actor.rect.width) // 2
        assert actor.rect.y == tile_y + (level.block_size - actor.rect.height)

    def test_the_cached_position_starts_at_the_spawn_point(self, actor: Actor) -> None:
        assert (actor.cached_x, actor.cached_y) == (actor.rect.x, actor.rect.y)

    def test_starts_facing_right_and_idle(self, actor: Actor) -> None:
        assert actor.direction is MovementDirection.RIGHT
        assert actor.facing is MovementDirection.RIGHT
        assert actor.state is MovementState.IDLE

    def test_attack_damage_is_scaled_by_difficulty(self, level, controller, player,
                                                   sprite_master, enemy_audios) -> None:
        hard = Actor(level, controller, 0, 0, sprite_master, enemy_audios, 2.0,
                     level.block_size, sprite = "TestAgent")
        assert hard.attack_damage == Actor.ATTACK_DAMAGE * 2.0

    def test_every_ability_starts_off_except_the_ones_passed_in(self, level, controller,
                                                                player, sprite_master,
                                                                enemy_audios) -> None:
        armed = Actor(level, controller, 0, 0, sprite_master, enemy_audios, 1.0,
                      level.block_size, sprite = "TestAgent", can_shoot = True,
                      can_resize = True)
        assert armed.abilities["can_shoot"] is True
        assert armed.abilities["can_resize"] is True
        assert armed.abilities["can_double_jump"] is False

    def test_actors_are_purged_on_load_unless_the_save_names_them(self, actor: Actor) -> None:
        assert actor.purgeable_on_load is True

    def test_a_projectile_sprite_is_resolved(self, actor: Actor) -> None:
        assert isinstance(actor.proj_sprite, pygame.Surface)


# --------------------------------------------------------------------------- #
# properties
# --------------------------------------------------------------------------- #
class TestProperties:
    def test_max_jumps_follows_the_double_jump_ability(self, actor: Actor) -> None:
        assert actor.max_jumps == 1
        actor.abilities["can_double_jump"] = True
        assert actor.max_jumps == 2

    def test_gravity_scales_with_size(self, actor: Actor) -> None:
        base = actor.gravity
        actor.size = 2.0
        assert actor.gravity == base * 2.0

    def test_gravity_is_quartered_while_rising_off_a_wall(self, actor: Actor) -> None:
        actor.is_wall_jumping = True
        actor.y_vel = 10          # positive y_vel means falling in screen space
        assert actor.gravity == Entity.GRAVITY / 4
        actor.y_vel = -10         # rising: the reduction does not apply
        assert actor.gravity == Entity.GRAVITY


# --------------------------------------------------------------------------- #
# movement
# --------------------------------------------------------------------------- #
class TestMove:
    def test_moves_by_the_requested_delta(self, actor: Actor) -> None:
        start = actor.rect.x
        actor.move(20, 0)
        assert actor.rect.x == start + 20

    def test_fractional_deltas_are_truncated(self, actor: Actor) -> None:
        start = actor.rect.x
        actor.move(0.9, 0)
        assert actor.rect.x == start

    def test_stops_at_the_left_edge_with_a_small_overhang(self, actor: Actor) -> None:
        actor.rect.left = 0
        actor.move(-1000, 0)
        assert actor.rect.left == -actor.rect.width // 5

    def test_stops_at_the_right_edge_with_a_small_overhang(self, actor: Actor,
                                                           level) -> None:
        actor.move(10_000, 0)
        assert actor.rect.right == level.level_bounds[1][0] + (actor.rect.width // 5)

    def test_hitting_the_ceiling_bounces_the_vertical_velocity(self, actor: Actor) -> None:
        actor.rect.top = 0
        actor.y_vel = -400
        actor.move(0, -10)
        assert actor.y_vel == 200        # reversed and halved by hit_head

    def test_falling_past_the_bottom_kills(self, actor: Actor, level) -> None:
        actor.rect.top = level.level_bounds[1][1]
        actor.move(0, 10)
        assert actor.hp == 0

    def test_a_zero_delta_changes_nothing(self, actor: Actor) -> None:
        before = actor.rect.topleft
        actor.move(0, 0)
        assert actor.rect.topleft == before


class TestCache:
    def _make_cacheable(self, actor: Actor) -> None:
        actor.state      = MovementState.IDLE
        actor.hp         = actor.max_hp
        actor.jump_count = 0
        actor.y_vel      = 0
        actor.cooldowns["get_hit"] = 0

    def test_caches_position_size_and_cooldowns_when_settled(self, actor: Actor) -> None:
        self._make_cacheable(actor)
        actor.rect.topleft = (400, 500)
        actor.size = actor.size_target = 1.5
        actor.cache()
        assert (actor.cached_x, actor.cached_y) == (400, 500)
        assert actor.cached_size == 1.5
        assert actor.cached_cooldowns is not actor.cooldowns

    @pytest.mark.parametrize("field, value", [
        ("state",      MovementState.JUMP),
        ("jump_count", 1),
        ("y_vel",      -50),
    ])
    def test_does_not_cache_mid_manoeuvre(self, actor: Actor, field, value) -> None:
        self._make_cacheable(actor)
        before = (actor.cached_x, actor.cached_y)
        actor.rect.topleft = (400, 500)
        setattr(actor, field, value)
        actor.cache()
        assert (actor.cached_x, actor.cached_y) == before

    def test_does_not_cache_while_damaged(self, actor: Actor) -> None:
        self._make_cacheable(actor)
        before = (actor.cached_x, actor.cached_y)
        actor.rect.topleft = (400, 500)
        actor.hp -= 1
        actor.cache()
        assert (actor.cached_x, actor.cached_y) == before

    def test_does_not_cache_during_hit_invulnerability(self, actor: Actor) -> None:
        self._make_cacheable(actor)
        before = (actor.cached_x, actor.cached_y)
        actor.rect.topleft = (400, 500)
        actor.cooldowns["get_hit"] = 0.5
        actor.cache()
        assert (actor.cached_x, actor.cached_y) == before

    def test_the_base_revert_is_inert(self, actor: Actor) -> None:
        assert actor.revert() == 0


# --------------------------------------------------------------------------- #
# jumping and landing
# --------------------------------------------------------------------------- #
class TestJump:
    def test_a_jump_sets_an_upward_velocity(self, actor: Actor) -> None:
        actor.jump()
        assert actor.y_vel == -Actor.VELOCITY_JUMP
        assert actor.jump_count == 1
        assert actor.should_move_vert is True

    def test_a_second_jump_is_refused_without_the_ability(self, actor: Actor) -> None:
        actor.jump()
        actor.y_vel = 0
        actor.jump()
        assert actor.jump_count == 1
        assert actor.y_vel == 0

    def test_double_jump_is_allowed_with_the_ability_and_spawns_trail_vfx(
            self, actor: Actor, vfx) -> None:
        actor.abilities["can_double_jump"] = True
        actor.jump()
        actor.jump()
        assert actor.jump_count == 2
        assert "JUMPLINES" in vfx.image_names

    def test_jumping_cancels_a_crouch(self, actor: Actor) -> None:
        actor.is_crouching = True
        actor.jump()
        assert actor.is_crouching is False

    def test_a_dead_actor_cannot_jump(self, actor: Actor) -> None:
        actor.hp = 0
        actor.jump()
        assert actor.jump_count == 0

    def test_a_wall_jump_pushes_off_and_flips_the_facing(self, actor: Actor) -> None:
        actor.is_wall_jumping = True
        actor.direction = actor.facing = MovementDirection.RIGHT
        start = actor.rect.x
        actor.jump()
        assert actor.is_wall_jumping is False
        assert actor.direction is MovementDirection.LEFT
        assert actor.facing is MovementDirection.LEFT
        assert actor.rect.x < start


class TestLand:
    def test_landing_clears_the_jump_state(self, actor: Actor) -> None:
        actor.y_vel = 300
        actor.jump_count = 2
        actor.is_wall_jumping = True
        actor.land()
        assert (actor.y_vel, actor.jump_count, actor.is_wall_jumping) == (0.0, 0, False)
        assert actor.should_move_vert is False

    def test_a_short_drop_does_no_damage(self, actor: Actor) -> None:
        actor.y_vel = 2 * Actor.VELOCITY_JUMP     # exactly at the threshold
        actor.land()
        assert actor.hp == actor.max_hp

    def test_a_long_drop_costs_health(self, actor: Actor) -> None:
        actor.y_vel = 1200
        actor.land()
        assert actor.hp == pytest.approx(100 - (1200 * 1200) / 18000)

    def test_being_larger_softens_the_landing(self, actor: Actor) -> None:
        actor.y_vel = 1200
        actor.size  = 2.0
        actor.land()
        assert actor.hp == pytest.approx(100 - (1200 * 1200) / 36000)

    def test_a_fatal_drop_kills(self, actor: Actor) -> None:
        actor.y_vel = 6000
        actor.land()
        assert actor.hp <= 0

    def test_the_player_gets_a_rumble_on_a_heavy_landing(self, player, controller,
                                                         gamepad) -> None:
        controller.gamepad = gamepad
        player.y_vel = 1200
        player.land()
        assert gamepad.rumbles

    def test_a_non_player_actor_never_rumbles(self, actor: Actor, controller,
                                              gamepad) -> None:
        controller.gamepad = gamepad
        actor.y_vel = 1200
        actor.land()
        assert gamepad.rumbles == []


def test_hit_head_reverses_and_damps(actor: Actor) -> None:
    actor.y_vel = -400
    actor.hit_head()
    assert actor.y_vel == 200


# --------------------------------------------------------------------------- #
# damage and death
# --------------------------------------------------------------------------- #
class TestGetHit:
    def test_damage_is_taken_from_the_attackers_stat(self, actor: Actor, level,
                                                     controller) -> None:
        attacker = Entity(level, controller, 0, 0, 4, 4)
        attacker.attack_damage = 30
        actor.get_hit(attacker)
        assert actor.hp == 70

    def test_invulnerability_and_heal_delay_cooldowns_are_started(self, actor: Actor,
                                                                  level, controller) -> None:
        attacker = Entity(level, controller, 0, 0, 4, 4)
        attacker.attack_damage = 1
        actor.get_hit(attacker)
        assert actor.cooldowns["get_hit"] == Actor.GET_HIT_COOLDOWN
        assert actor.cooldowns["heal"] == Actor.HEAL_DELAY * actor.difficulty

    def test_an_attacker_with_no_damage_stat_still_starts_the_cooldown(
            self, actor: Actor, level, controller) -> None:
        actor.get_hit(Entity(level, controller, 0, 0, 4, 4))
        assert actor.hp == 100
        assert actor.cooldowns["get_hit"] == Actor.GET_HIT_COOLDOWN

    def test_fatal_damage_kills(self, actor: Actor, level, controller) -> None:
        attacker = Entity(level, controller, 0, 0, 4, 4)
        attacker.attack_damage = 500
        actor.get_hit(attacker)
        assert actor.hp <= 0

    def test_damage_that_lands_exactly_on_zero_does_not_call_die(
            self, actor: Actor, level, controller) -> None:
        # `if self.hp < 0` is strict, so an exact kill leaves die() unrun; the
        # entity is still collected by Entity.loop on the next frame.
        attacker = Entity(level, controller, 0, 0, 4, 4)
        attacker.attack_damage = 100
        actor.get_hit(attacker)
        assert actor.hp == 0


class TestDie:
    def test_die_zeroes_health(self, actor: Actor) -> None:
        actor.die()
        assert actor.hp == 0

    def test_the_death_cooldown_never_starts_from_a_zero_value(self, actor: Actor) -> None:
        """Characterisation of a real defect.

        ``die`` guards on ``self.cooldowns.get("dead")`` -- a *truthiness* test.  The
        cooldown's resting value is ``0.0``, which is falsy, so the guard fails and
        ``DEATH_TIME`` is never assigned.  The practical effect: the DEAD animation
        never gets a chance to play and the player's death rumble never fires,
        because ``Entity.loop`` purges the actor on the very next frame.
        See BUGS_FOUND.md #8.
        """
        actor.cooldowns["dead"] = 0.0
        actor.die()
        assert actor.cooldowns["dead"] == 0.0

    def test_the_death_cooldown_does_start_from_a_negative_value(self, actor: Actor) -> None:
        actor.cooldowns["dead"] = -0.1
        actor.die()
        assert actor.cooldowns["dead"] == Actor.DEATH_TIME


# --------------------------------------------------------------------------- #
# difficulty and resizing
# --------------------------------------------------------------------------- #
class TestSetDifficulty:
    def test_scales_health_and_damage(self, actor: Actor) -> None:
        actor.set_difficulty(2.0)
        assert actor.max_hp == 200
        assert actor.hp == 200
        assert actor.attack_damage == Actor.ATTACK_DAMAGE * 2

    def test_rescales_projectiles_in_flight(self, actor: Actor) -> None:
        actor.abilities["can_shoot"] = True
        actor.shoot_at_target((actor.rect.centerx + 200, actor.rect.centery))
        projectile = actor.active_projectiles[0]
        before = projectile.speed
        actor.set_difficulty(2.0)
        assert projectile.speed != before
        assert projectile.attack_damage == actor.attack_damage


class TestResize:
    @pytest.fixture
    def resizer(self, actor: Actor) -> Actor:
        actor.abilities["can_resize"] = True
        return actor

    def test_grow_moves_towards_the_upper_limit(self, resizer: Actor) -> None:
        resizer.grow()
        assert resizer.size_target == Actor.RESIZE_SCALE_LIMIT

    def test_shrink_moves_towards_the_lower_limit(self, resizer: Actor) -> None:
        resizer.shrink()
        assert resizer.size_target == pytest.approx(1 / Actor.RESIZE_SCALE_LIMIT)

    def test_resizing_starts_the_cooldowns(self, resizer: Actor) -> None:
        resizer.grow()
        assert resizer.cooldowns["resize"] == Actor.RESIZE_DELAY
        assert resizer.cooldowns["resize_delay"] == Actor.RESIZE_DELAY

    def test_growing_scales_attack_damage(self, resizer: Actor) -> None:
        before = resizer.attack_damage
        resizer.grow()
        assert resizer.attack_damage == before * Actor.RESIZE_SCALE_LIMIT

    def test_resizing_is_refused_without_the_ability(self, actor: Actor) -> None:
        actor.grow()
        assert actor.size_target == 1.0

    def test_resizing_is_refused_while_on_cooldown(self, resizer: Actor) -> None:
        resizer.cooldowns["resize"] = 1.0
        resizer.grow()
        assert resizer.size_target == 1.0

    def test_resizing_is_refused_when_dead(self, resizer: Actor) -> None:
        resizer.hp = 0
        resizer.grow()
        assert resizer.size_target == 1.0

    def test_resizing_to_the_current_size_is_a_no_op(self, resizer: Actor) -> None:
        before = resizer.attack_damage
        resizer.resize(1.0)
        assert resizer.attack_damage == before
        assert resizer.cooldowns["resize"] == 0.0


# --------------------------------------------------------------------------- #
# shooting
# --------------------------------------------------------------------------- #
class TestShootAtTarget:
    def test_launches_a_projectile_and_starts_the_cooldown(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery + 300))
        assert len(actor.active_projectiles) == 1
        assert actor.is_attacking is True
        assert actor.cooldowns["launch_projectile"] == Actor.LAUNCH_PROJECTILE_COOLDOWN

    def test_the_shot_is_flattened_to_the_horizontal(self, actor: Actor) -> None:
        # Aim is taken as (target_x, own centery): actors shoot straight along the floor.
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery + 300))
        projectile = actor.active_projectiles[0]
        assert projectile.target[1] == pytest.approx(actor.rect.centery, abs = 1)

    def test_a_second_shot_is_refused_while_on_cooldown(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        assert len(actor.active_projectiles) == 1

    def test_a_dead_actor_cannot_shoot(self, actor: Actor) -> None:
        actor.hp = 0
        actor.shoot_at_target((0, 0))
        assert actor.active_projectiles == []

    def test_projectiles_are_numbered_for_the_save_file(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        assert "projectile #1" in actor.active_projectiles[0].name


# --------------------------------------------------------------------------- #
# save / load
# --------------------------------------------------------------------------- #
class TestSaveLoad:
    def test_saves_position_cooldowns_size_and_projectiles(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        payload = actor.save()[actor.name]
        assert payload["cached x y"] == (actor.cached_x, actor.cached_y)
        assert payload["size"] == actor.size
        assert len(payload["projectiles"]) == 1

    def test_load_restores_position_and_size(self, actor: Actor) -> None:
        actor.load({
            "cached x y": (321, 123),
            "cooldowns":  dict(actor.cooldowns),
            "hp":         55,
            "size":       1.5,
            "size_target": 1.5,
            "projectiles": [],
        })
        assert actor.rect.topleft == (321, 123)
        assert (actor.cached_x, actor.cached_y) == (321, 123)
        assert actor.hp == 55
        assert actor.size == 1.5

    def test_load_rehydrates_projectiles(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        payload = actor.save()[actor.name]
        actor.active_projectiles.clear()

        actor.load(payload)
        assert len(actor.active_projectiles) == 1
        assert isinstance(actor.active_projectiles[0], Projectile)

    def test_a_round_trip_preserves_the_cooldown_dict(self, actor: Actor) -> None:
        actor.cooldowns["get_hit"] = 0.4
        actor.cache()
        payload = actor.save()[actor.name]
        fresh_cooldowns = dict(payload["cooldowns"])
        actor.cooldowns = {}
        actor.load(payload)
        assert actor.cooldowns == fresh_cooldowns


# --------------------------------------------------------------------------- #
# animation state machine
# --------------------------------------------------------------------------- #
class TestUpdateState:
    def test_idle_by_default(self, actor: Actor) -> None:
        actor.update_state()
        assert actor.state is MovementState.IDLE

    def test_horizontal_intent_becomes_run(self, actor: Actor) -> None:
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.state is MovementState.RUN

    def test_crouching_while_moving_becomes_crouch(self, actor: Actor) -> None:
        actor.should_move_horiz = True
        actor.is_crouching = True
        actor.update_state()
        assert actor.state is MovementState.CROUCH

    def test_crouching_while_still_becomes_idle_crouch(self, actor: Actor) -> None:
        actor.is_crouching = True
        actor.update_state()
        assert actor.state is MovementState.IDLE_CROUCH

    def test_rising_becomes_jump(self, actor: Actor) -> None:
        actor.should_move_vert = True
        actor.y_vel = -200
        actor.update_state()
        assert actor.state is MovementState.JUMP

    def test_a_second_jump_becomes_double_jump(self, actor: Actor) -> None:
        actor.should_move_vert = True
        actor.y_vel = -200
        actor.jump_count = 2
        actor.update_state()
        assert actor.state is MovementState.DOUBLE_JUMP

    def test_falling_fast_enough_becomes_fall(self, actor: Actor) -> None:
        actor.should_move_vert = True
        actor.y_vel = Actor.MIN_FALL_VEL + 1
        actor.update_state()
        assert actor.state is MovementState.FALL

    def test_drifting_below_the_fall_threshold_stays_idle(self, actor: Actor) -> None:
        actor.should_move_vert = True
        actor.y_vel = Actor.MIN_FALL_VEL - 1
        actor.update_state()
        assert actor.state is MovementState.IDLE

    def test_wall_jumping_takes_priority_over_falling(self, actor: Actor) -> None:
        actor.abilities["can_wall_jump"] = True
        actor.is_wall_jumping  = True
        actor.should_move_vert = True
        actor.update_state()
        assert actor.state is MovementState.WALL_JUMP

    def test_attacking_selects_the_attack_variant(self, actor: Actor) -> None:
        actor.should_move_horiz = True
        actor.is_attacking = True
        actor.update_state()
        assert actor.state is MovementState.RUN_ATTACK

    def test_the_hit_animation_holds_until_the_cooldown_expires(self, actor: Actor) -> None:
        actor.cooldowns["get_hit"] = 0.5
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.state is MovementState.HIT

    def test_teleporting_takes_priority_over_movement(self, actor: Actor) -> None:
        actor.teleport_distance = 50
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.state is MovementState.TELEPORT

    def test_resizing_takes_priority_over_everything_but_death(self, actor: Actor) -> None:
        actor.size_target = 1.5
        actor.cooldowns["get_hit"] = 1.0
        actor.update_state()
        assert actor.state is MovementState.RESIZE

    def test_death_wins_outright(self, actor: Actor) -> None:
        actor.hp = 0
        actor.cooldowns["dead"] = 1.0
        actor.size_target = 1.5
        actor.update_state()
        assert actor.state is MovementState.DEAD

    def test_state_changed_reports_transitions_only(self, actor: Actor) -> None:
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.state_changed is True
        actor.update_state()
        assert actor.state_changed is False

    def test_entering_a_new_state_resets_the_animation_counter(self, actor: Actor) -> None:
        actor.animation_count = 10
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.animation_count == 0

    def test_a_state_with_no_sprite_sheet_is_rejected(self, actor: Actor) -> None:
        """The final guard in update_state keeps the actor on a state it can draw."""
        del actor.sprites["RUN_RIGHT"]
        actor.should_move_horiz = True
        actor.update_state()
        assert actor.state is MovementState.IDLE

    def test_an_animated_attack_walks_wind_up_to_wind_down(self, actor: Actor) -> None:
        actor.is_animated_attack = True
        actor.is_attacking       = True

        actor.update_state()
        assert actor.state is MovementState.WIND_UP

        actor.is_final_anim_frame = True
        actor.update_state()
        assert actor.state is MovementState.ATTACK_ANIM

        actor.update_state()
        assert actor.state is MovementState.WIND_DOWN

        actor.update_state()
        assert actor.is_attacking is False
        assert actor.state is MovementState.IDLE


class TestUpdateSprite:
    def test_selects_the_frame_from_the_animation_counter(self, actor: Actor) -> None:
        actor.animation_count = 0
        assert actor.update_sprite() == 0
        actor.animation_count = Actor.ANIMATION_DELAY
        assert actor.update_sprite() == 1

    def test_the_animation_wraps(self, actor: Actor) -> None:
        frames = len(actor.sprites["IDLE_RIGHT"])
        actor.animation_count = Actor.ANIMATION_DELAY * frames
        assert actor.update_sprite() == 0

    def test_the_last_frame_is_flagged(self, actor: Actor) -> None:
        frames = len(actor.sprites["IDLE_RIGHT"])
        actor.animation_count = Actor.ANIMATION_DELAY * (frames - 1)
        actor.update_sprite()
        assert actor.is_final_anim_frame is True

    def test_a_resized_actor_gets_a_scaled_sprite(self, actor: Actor) -> None:
        base = actor.update_sprite() and None or actor.sprite.get_width()
        actor.size = 2.0
        actor.update_sprite()
        assert actor.sprite.get_width() > base

    def test_the_facing_direction_selects_the_sheet(self, actor: Actor) -> None:
        actor.facing = MovementDirection.LEFT
        actor.update_sprite()
        assert actor.sprite is actor.sprites["IDLE_LEFT"][0]

    def test_update_geo_resyncs_the_rect_and_mask_to_the_sprite(self, actor: Actor) -> None:
        actor.size = 2.0
        actor.update_sprite()
        actor.update_geo()
        assert actor.rect.size == actor.sprite.get_size()
        assert actor.mask.get_size() == actor.sprite.get_size()


# --------------------------------------------------------------------------- #
# loop
# --------------------------------------------------------------------------- #
class TestLoop:
    def test_a_pathless_non_player_actor_does_not_move_itself(self, actor: Actor) -> None:
        # Only the player and actors with a patrol path run the physics block.
        before = actor.rect.topleft
        actor.loop(0.1)
        assert actor.rect.topleft == before

    def test_healing_ticks_up_when_the_ability_is_on_and_the_delay_has_passed(
            self, actor: Actor) -> None:
        actor.abilities["can_heal"] = True
        actor.hp = 50
        actor.cooldowns["heal"] = 0
        actor.loop(1.0)
        assert actor.hp > 50

    def test_healing_waits_for_the_delay(self, actor: Actor) -> None:
        actor.abilities["can_heal"] = True
        actor.hp = 50
        actor.cooldowns["heal"] = 5.0
        actor.loop(0.1)
        assert actor.hp == 50

    def test_healing_stops_at_full_health(self, actor: Actor) -> None:
        actor.abilities["can_heal"] = True
        actor.cooldowns["heal"] = 0
        actor.loop(100.0)
        assert actor.hp == actor.max_hp

    def test_spent_projectiles_are_dropped(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        actor.active_projectiles[0].hp = 0
        actor.loop(0.016)
        assert actor.active_projectiles == []

    def test_live_projectiles_are_advanced(self, actor: Actor) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        projectile = actor.active_projectiles[0]
        before = projectile.rect.centerx
        actor.loop(0.05)
        assert projectile.rect.centerx != before

    def test_gravity_accumulates_for_an_actor_that_runs_the_physics_block(
            self, player) -> None:
        player.loop(0.1)
        assert player.y_vel > 0

    def test_the_animation_counter_is_truncated_to_whole_seconds(self,
                                                                 actor: Actor) -> None:
        """Characterisation of a real defect.

        ``Actor.loop`` does ``self.animation_count += int(dtime)``.  The engine feeds
        it seconds (``clock.tick(150) / 1000``), so ``int(dtime)`` is 0 on every
        frame and the counter never advances -- actors are frozen on frame 0 of every
        animation.  ``Objective`` and ``Hazard`` use ``+= dtime`` and animate
        correctly, which is what makes the difference visible in game.
        See BUGS_FOUND.md #9.
        """
        actor.animation_count = 0
        for _ in range(100):
            actor.loop(1 / 150)
        assert actor.animation_count == 0

        actor.loop(1.5)
        assert actor.animation_count == 1


class TestDraw:
    def test_draws_the_sprite_at_the_camera_offset(self, actor: Actor,
                                                   surface: pygame.Surface) -> None:
        actor.rect.topleft = (100, 100)
        actor.draw(surface, 100, 100, actor.controller.master_volume)
        assert surface.get_at((2, 2)).a > 0

    def test_off_screen_actors_are_culled(self, actor: Actor,
                                          surface: pygame.Surface) -> None:
        actor.rect.topleft = (-5000, -5000)
        actor.draw(surface, 0, 0, actor.controller.master_volume)
        assert surface.get_at((0, 0)) == pygame.Color(0, 0, 0, 0)

    def test_projectiles_are_drawn_with_their_owner(self, actor: Actor,
                                                    surface: pygame.Surface) -> None:
        actor.shoot_at_target((actor.rect.centerx + 300, actor.rect.centery))
        drawn: list[str] = []
        actor.active_projectiles[0].draw = lambda *a, **k: drawn.append("proj")  # type: ignore[method-assign]
        actor.draw(surface, 0, 0, actor.controller.master_volume)
        assert drawn == ["proj"]


def test_movement_state_str_is_the_name_used_for_sprite_lookups() -> None:
    # `f"{state}_{facing}"` is the sprite key, so this must stay the bare name.
    assert str(MovementState.DOUBLE_JUMP_ATTACK) == "DOUBLE_JUMP_ATTACK"
    assert math.isclose(Actor.ANIMATION_DELAY, 0.05)
