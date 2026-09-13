"""Tests for ``Player`` -- the abilities, per-level statistics and input-facing verbs.

``Player`` is the only actor the engine drives directly from input, so most of these
methods are the far end of a key binding.  Physics it inherits from ``Actor`` is
covered in ``tests/test_actor.py``.
"""

from __future__ import annotations

import pytest

from Actor import MovementState
from Block import BreakableBlock
from Helpers import DifficultyScale, MovementDirection
from Player import Player
from Trigger import SaveTrigger


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
class TestConstruction:
    def test_the_traversal_abilities_are_granted_up_front(self, player: Player) -> None:
        assert player.abilities["can_open_doors"] is True
        assert player.abilities["can_move_blocks"] is True
        assert player.abilities["can_heal"] is True

    def test_the_special_abilities_start_locked(self, player: Player) -> None:
        for ability in ("can_double_jump", "can_teleport", "can_block",
                        "can_bullet_time", "can_wall_jump", "can_resize"):
            assert player.abilities[ability] is False

    def test_player_specific_cooldowns_exist(self, player: Player) -> None:
        for name in ("teleport", "teleport_delay", "block", "bullet_time",
                     "bullet_time_active", "dead"):
            assert name in player.cooldowns

    def test_the_player_is_faster_than_a_generic_actor(self, player: Player) -> None:
        assert player.target_vel == Player.VELOCITY_TARGET
        assert player.x_accel_max_time == Player.ACCEL_MAX_TIME

    def test_health_scales_inversely_with_difficulty(self, make_player) -> None:
        """Full health at EASIEST, a fifth of it at HARDEST, stepping evenly between."""
        assert make_player(difficulty = 0.25).max_hp == 100
        assert make_player(difficulty = 0.50).max_hp == 80
        assert make_player(difficulty = 1.00).max_hp == 60
        assert make_player(difficulty = 1.50).max_hp == 40
        assert make_player(difficulty = 2.00).max_hp == 20
        assert make_player(difficulty = 1.00).hp == 60

    def test_the_player_hits_twice_as_hard_as_the_base_actor_at_every_difficulty(
            self, make_player) -> None:
        """The agent's punch is flat -- difficulty costs durability, not damage."""
        from Actor import Actor
        damages = {make_player(difficulty = scale).attack_damage
                   for scale in DifficultyScale}
        assert damages == {Actor.ATTACK_DAMAGE * 2}

    def test_per_level_statistics_start_clean(self, player: Player) -> None:
        assert player.been_hit_this_level is False
        assert player.been_seen_this_level is False
        assert player.deaths_this_level == 0
        assert player.kills_this_level == 0

    def test_the_name_is_stable_because_the_save_file_keys_on_it(self,
                                                                 player: Player) -> None:
        assert player.name.startswith("Player (")


class TestRetroSprites:
    def test_both_sprite_sets_are_loaded(self, player: Player) -> None:
        assert player.sprites_set[0] is not None
        assert player.sprites_set[1] is not None

    def test_toggling_swaps_the_active_set(self, player: Player) -> None:
        player.toggle_retro()
        assert player.is_retro is True
        assert player.sprites is player.sprites_set[1]
        player.toggle_retro()
        assert player.is_retro is False
        assert player.sprites is player.sprites_set[0]

    def test_a_retro_level_starts_in_retro(self, retro_level, controller, sprite_master,
                                           player_audios) -> None:
        player = Player(retro_level, controller, 96, 96, sprite_master, player_audios,
                        1.0, retro_level.block_size, sprite = "Player1",
                        retro_sprite = "RetroPlayer1")
        assert player.is_retro is True


# --------------------------------------------------------------------------- #
# simple verbs
# --------------------------------------------------------------------------- #
class TestMovementVerbs:
    def test_move_right_sets_intent_and_facing(self, player: Player) -> None:
        player.move_right()
        assert player.should_move_horiz is True
        assert player.direction is MovementDirection.RIGHT
        assert player.facing is MovementDirection.RIGHT

    def test_move_left_sets_intent_and_facing(self, player: Player) -> None:
        player.move_left()
        assert player.direction is MovementDirection.LEFT
        assert player.facing is MovementDirection.LEFT

    def test_reversing_direction_zeroes_the_carried_velocity(self, player: Player) -> None:
        player.move_right()
        player.x_vel = 300
        player.move_left()
        assert player.x_vel == 0

    def test_continuing_in_the_same_direction_keeps_the_velocity(self,
                                                                 player: Player) -> None:
        player.move_right()
        player.x_vel = 300
        player.move_right()
        assert player.x_vel == 300

    def test_a_dead_player_cannot_move(self, player: Player) -> None:
        player.hp = 0
        player.move_left()
        assert player.should_move_horiz is False

    def test_stop_clears_the_movement_intent(self, player: Player) -> None:
        player.move_right()
        player.stop()
        assert player.should_move_horiz is False

    def test_crouch_toggles(self, player: Player) -> None:
        player.toggle_crouch()
        assert player.is_crouching is True
        player.toggle_crouch()
        assert player.is_crouching is False


# --------------------------------------------------------------------------- #
# blocking
# --------------------------------------------------------------------------- #
class TestBlock:
    def test_raising_a_shield_starts_both_cooldowns_and_spawns_the_vfx(
            self, player: Player, vfx) -> None:
        player.abilities["can_block"] = True
        player.block()
        assert player.cooldowns["blocking_effect"] == Player.BLOCK_EFFECT_TIME
        assert player.cooldowns["block"] == Player.BLOCK_COOLDOWN
        assert "BLOCKSHIELD" in vfx.image_names

    def test_blocking_is_refused_without_the_ability(self, player: Player, vfx) -> None:
        player.block()
        assert vfx.spawned == []

    def test_blocking_is_refused_while_on_cooldown(self, player: Player, vfx) -> None:
        player.abilities["can_block"] = True
        player.cooldowns["block"] = 1.0
        player.block()
        assert vfx.spawned == []

    def test_the_shield_is_linked_to_the_player_so_it_follows_them(self,
                                                                   player: Player,
                                                                   vfx) -> None:
        player.abilities["can_block"] = True
        player.block()
        effect = vfx.spawned_named("BLOCKSHIELD")[0]
        assert effect.linked_to_source is True


# --------------------------------------------------------------------------- #
# taking damage
# --------------------------------------------------------------------------- #
class TestGetHit:
    def test_a_hit_is_recorded_for_the_end_of_level_recap(self, player: Player,
                                                          make_enemy) -> None:
        enemy = make_enemy()
        player.get_hit(enemy)
        assert player.been_hit_this_level is True

    def test_health_is_reduced_by_the_attackers_damage(self, player: Player,
                                                       make_enemy) -> None:
        enemy = make_enemy()
        before = player.hp
        player.get_hit(enemy)
        assert player.hp == before - enemy.attack_damage

    def test_the_player_is_invulnerable_while_the_camera_is_panning(
            self, player: Player, make_enemy, controller) -> None:
        controller.should_scroll_to_point = {"coords": (0, 0), "time": 0.0}
        player.get_hit(make_enemy())
        assert player.hp == player.max_hp
        assert player.been_hit_this_level is False

    def test_an_active_shield_absorbs_one_enemy_hit_and_is_spent(
            self, player: Player, make_enemy) -> None:
        player.cooldowns["blocking_effect"] = Player.BLOCK_EFFECT_TIME
        player.get_hit(make_enemy())
        assert player.hp == player.max_hp
        assert player.cooldowns["blocking_effect"] == 0

    def test_a_shield_does_not_absorb_a_hazard(self, player: Player, make_hazard) -> None:
        player.cooldowns["blocking_effect"] = Player.BLOCK_EFFECT_TIME
        player.get_hit(make_hazard())
        assert player.hp < player.max_hp

    def test_being_hit_rumbles_the_gamepad(self, player: Player, controller,
                                           gamepad, make_enemy) -> None:
        controller.gamepad = gamepad
        player.get_hit(make_enemy())
        assert gamepad.rumbles


# --------------------------------------------------------------------------- #
# revert
# --------------------------------------------------------------------------- #
class TestRevert:
    def test_restores_the_cached_position_health_and_size(self, player: Player) -> None:
        player.cached_x, player.cached_y = 640, 320
        player.cached_size = player.cached_size_target = 1.5
        player.rect.topleft = (0, 0)
        player.hp   = 1
        player.size = 0.5

        player.revert()
        assert player.rect.topleft == (640, 320)
        assert player.hp == player.max_hp
        assert player.size == 1.5

    def test_counts_the_death(self, player: Player) -> None:
        player.revert()
        assert player.deaths_this_level == 1

    def test_clears_the_death_cooldown_and_momentum(self, player: Player) -> None:
        player.cooldowns["dead"] = 1.5
        player.x_vel = player.y_vel = 500
        player.revert()
        assert player.cooldowns["dead"] == 0.0
        assert player.x_vel == player.y_vel == 0.0

    def test_shows_one_of_the_respawn_messages(self, player: Player, display_texts) -> None:
        player.revert()
        assert len(display_texts) == 1
        assert display_texts[-1].text

    def test_returns_the_wall_clock_cost_so_the_engine_can_subtract_it(
            self, player: Player) -> None:
        assert player.revert() >= 0.0

    def test_reverting_copies_the_cooldowns_rather_than_aliasing_them(
            self, player: Player) -> None:
        """The snapshot has to survive the revert it was restored from.

        Sharing one dict meant every later cooldown tick also mutated the checkpoint,
        so dying twice between saves restored the decayed values.
        """
        player.revert()
        assert player.cooldowns is not player.cached_cooldowns

        player.cooldowns["teleport"] = 99
        assert player.cached_cooldowns["teleport"] != 99

    def test_reverting_twice_restores_the_same_cooldowns_both_times(
            self, player: Player) -> None:
        player.cached_cooldowns["teleport"] = 2.5

        player.revert()
        player.update_cooldowns(1.0)
        player.revert()
        assert player.cooldowns["teleport"] == pytest.approx(2.5)


# --------------------------------------------------------------------------- #
# teleport
# --------------------------------------------------------------------------- #
class TestTeleport:
    def test_refused_without_the_ability(self, player: Player) -> None:
        player.teleport()
        assert player.teleport_distance == 0

    def test_dashes_the_full_range_across_empty_ground(self, player: Player) -> None:
        player.abilities["can_teleport"] = True
        player.teleport()
        # the search runs from int(VELOCITY_TARGET * MULTIPLIER_TELEPORT) + 1 downwards
        expected = int(Player.VELOCITY_TARGET * Player.MULTIPLIER_TELEPORT) + 1
        assert player.teleport_distance == expected

    def test_dashes_left_when_facing_left(self, player: Player) -> None:
        player.abilities["can_teleport"] = True
        player.rect.x = 500
        player.direction = MovementDirection.LEFT
        player.teleport()
        assert player.teleport_distance < 0

    def test_starts_the_delay_and_the_cooldown(self, player: Player) -> None:
        player.abilities["can_teleport"] = True
        player.teleport()
        assert player.cooldowns["teleport_delay"] == Player.TELEPORT_DELAY
        assert player.cooldowns["teleport"] == Player.TELEPORT_DELAY

    def test_refused_while_on_cooldown(self, player: Player) -> None:
        player.abilities["can_teleport"] = True
        player.cooldowns["teleport"] = 1.0
        player.teleport()
        assert player.teleport_distance == 0

    def test_refused_when_dead(self, player: Player) -> None:
        player.abilities["can_teleport"] = True
        player.hp = 0
        player.teleport()
        assert player.teleport_distance == 0

    def test_stops_short_of_a_wall(self, player: Player, make_block, level) -> None:
        player.abilities["can_teleport"] = True
        full = int(Player.VELOCITY_TARGET * Player.MULTIPLIER_TELEPORT) + 1
        # A wall two tiles to the right is well inside the full dash range.
        make_block(col = 3, row = 1)
        player.teleport()
        assert 0 < player.teleport_distance < full

    def test_a_fully_blocked_dash_does_nothing(self, player: Player, make_block) -> None:
        player.abilities["can_teleport"] = True
        for col in range(1, 6):
            make_block(col = col, row = 1)
        player.teleport()
        assert player.teleport_distance == 0

    def test_the_dash_is_performed_on_the_next_loop_and_leaves_a_trail(
            self, player: Player, vfx) -> None:
        player.abilities["can_teleport"] = True
        player.teleport()
        start = player.rect.x
        player.cooldowns["teleport_delay"] = 0
        player.loop(0.016)
        assert player.rect.x > start
        assert "DASHCLOUD" in vfx.image_names
        assert player.teleport_distance == 0


# --------------------------------------------------------------------------- #
# melee attack
# --------------------------------------------------------------------------- #
class TestAttack:
    def test_attacking_marks_the_player_as_attacking(self, player: Player) -> None:
        player.attack()
        assert player.is_attacking is True

    def test_a_state_that_cannot_attack_is_ignored(self, player: Player) -> None:
        player.state = MovementState.DEAD
        player.attack()
        assert player.is_attacking is False

    def test_a_hostile_enemy_in_front_takes_damage_and_is_knocked_back(
            self, player: Player, make_enemy, level) -> None:
        enemy = make_enemy(col = 1, row = 1)
        enemy.patrol_path = [object()]          # knockback only applies to patrollers
        enemy.rect.topleft = (player.rect.x + 10, player.rect.y)
        before = enemy.hp
        player.facing = player.direction = MovementDirection.RIGHT

        player.attack()
        assert enemy.hp < before
        assert enemy.push_x != 0

    def test_an_enemy_behind_the_player_is_untouched(self, player: Player,
                                                     make_enemy) -> None:
        enemy = make_enemy(col = 1, row = 1)
        enemy.rect.topleft = (player.rect.x + 10, player.rect.y)
        before = enemy.hp
        player.facing = MovementDirection.LEFT
        player.attack()
        assert enemy.hp == before

    def test_a_friendly_npc_is_not_attacked(self, player: Player, make_enemy) -> None:
        friend = make_enemy(col = 1, row = 1, is_hostile = False)
        friend.rect.topleft = (player.rect.x + 10, player.rect.y)
        before = friend.hp
        player.attack()
        assert friend.hp == before

    def test_a_breakable_block_in_reach_is_damaged(self, player: Player, level,
                                                   controller, image_master,
                                                   block_audios) -> None:
        crate = BreakableBlock(level, controller, player.rect.x, player.rect.y,
                               level.block_size, level.block_size, image_master,
                               block_audios, False)
        level.place_static(crate, 1, 1)
        player.attack()
        assert crate.hp < crate.max_hp

    def test_nothing_in_reach_is_harmless(self, player: Player) -> None:
        assert player.attack() >= 0.0


# --------------------------------------------------------------------------- #
# bullet time
# --------------------------------------------------------------------------- #
class TestBulletTime:
    def test_refused_without_the_ability(self, player: Player) -> None:
        player.bullet_time()
        assert player.is_slow_time is False

    def test_engaging_starts_the_active_window_and_the_cooldown(self,
                                                                player: Player) -> None:
        player.abilities["can_bullet_time"] = True
        player.bullet_time()
        assert player.is_slow_time is True
        assert player.cooldowns["bullet_time_active"] == Player.BULLET_TIME_ACTIVE
        assert player.cooldowns["bullet_time"] == Player.BULLET_TIME_COOLDOWN

    def test_toggling_off_early_clears_the_active_window(self, player: Player) -> None:
        player.abilities["can_bullet_time"] = True
        player.bullet_time()
        player.bullet_time()
        assert player.is_slow_time is False
        assert player.cooldowns["bullet_time_active"] == 0

    def test_cannot_re_engage_until_the_cooldown_expires(self, player: Player) -> None:
        player.abilities["can_bullet_time"] = True
        player.bullet_time()
        player.bullet_time()          # off
        player.bullet_time()          # blocked by the remaining cooldown
        assert player.is_slow_time is False

    def test_a_dead_player_cannot_slow_time(self, player: Player) -> None:
        player.abilities["can_bullet_time"] = True
        player.hp = 0
        player.bullet_time()
        assert player.is_slow_time is False

    def test_the_effect_lapses_when_its_window_closes(self, player: Player) -> None:
        player.abilities["can_bullet_time"] = True
        player.bullet_time()
        player.cooldowns["bullet_time_active"] = 0
        player.loop(0.016)
        assert player.is_slow_time is False


# --------------------------------------------------------------------------- #
# triggers
# --------------------------------------------------------------------------- #
class TestGetTriggers:
    def test_an_overlapping_trigger_fires(self, player: Player, level, controller) -> None:
        trigger = SaveTrigger(level, controller, player.rect.x, player.rect.y, 96, 96, None)
        level.triggers.append(trigger)
        player.get_triggers()
        assert trigger.has_fired is True
        assert controller.save_calls == 1

    def test_a_fire_once_trigger_is_queued_for_removal(self, player: Player, level,
                                                       controller) -> None:
        trigger = SaveTrigger(level, controller, player.rect.x, player.rect.y, 96, 96, None)
        level.triggers.append(trigger)
        player.get_triggers()
        assert trigger in level.purge_queue["triggers"]

    def test_a_repeatable_trigger_stays(self, player: Player, level, controller) -> None:
        trigger = SaveTrigger(level, controller, player.rect.x, player.rect.y, 96, 96,
                              None, fire_once = False)
        level.triggers.append(trigger)
        player.get_triggers()
        assert trigger not in level.purge_queue["triggers"]

    def test_a_distant_trigger_does_not_fire(self, player: Player, level,
                                             controller) -> None:
        trigger = SaveTrigger(level, controller, 800, 700, 96, 96, None)
        level.triggers.append(trigger)
        player.get_triggers()
        assert trigger.has_fired is False

    def test_the_loop_always_checks_triggers(self, player: Player, level,
                                             controller) -> None:
        trigger = SaveTrigger(level, controller, player.rect.x, player.rect.y, 96, 96, None)
        level.triggers.append(trigger)
        player.loop(0.016)
        assert trigger.has_fired is True


# --------------------------------------------------------------------------- #
# difficulty and persistence
# --------------------------------------------------------------------------- #
class TestDifficultyAndSave:
    def test_a_harder_setting_lowers_health_and_leaves_damage_alone(self,
                                                                    player: Player) -> None:
        max_hp, damage = player.max_hp, player.attack_damage       # MEDIUM: 60 hp
        player.set_difficulty(2.0)                                 # HARDEST: 20 hp
        assert max_hp == 60
        assert player.max_hp == player.hp == 20
        assert player.attack_damage == damage

    def test_an_easier_setting_raises_health_and_leaves_damage_alone(self,
                                                                     player: Player) -> None:
        max_hp, damage = player.max_hp, player.attack_damage       # MEDIUM: 60 hp
        player.set_difficulty(0.25)                                # EASIEST: 100 hp
        assert max_hp == 60
        assert player.max_hp == player.hp == 100
        assert player.attack_damage == damage

    def test_the_agent_is_weaker_the_harder_the_setting(self, make_player) -> None:
        """Matches the menu copy: "Agent is weaker" on the harder settings."""
        healths = [make_player(difficulty = scale).max_hp for scale in DifficultyScale]
        assert healths == sorted(healths, reverse = True)
        assert len(set(healths)) == len(healths)

    def test_switching_difficulty_matches_starting_at_it(self, make_player,
                                                          player: Player) -> None:
        """The menu path and the level-build path must agree on the numbers."""
        player.set_difficulty(2.0)
        fresh = make_player(difficulty = 2.0)
        assert player.max_hp == pytest.approx(fresh.max_hp)
        assert player.attack_damage == pytest.approx(fresh.attack_damage)

    def test_repeated_difficulty_changes_do_not_compound(self, player: Player) -> None:
        """The scale is absolute, so MEDIUM -> HARD -> MEDIUM returns to MEDIUM.

        Controller.set_difficulty walks every entity with the new absolute scale;
        applying it to the current value each time used to leave the player on
        two-thirds of the health they started with.
        """
        max_hp, damage = player.max_hp, player.attack_damage
        player.set_difficulty(2.0)
        player.set_difficulty(1.0)
        assert player.max_hp == pytest.approx(max_hp)
        assert player.attack_damage == pytest.approx(damage)

    def test_setting_the_same_difficulty_twice_is_a_no_op(self, player: Player) -> None:
        max_hp = player.max_hp
        player.set_difficulty(player.difficulty)
        player.set_difficulty(player.difficulty)
        assert player.max_hp == max_hp

    def test_save_includes_the_per_level_statistics(self, player: Player) -> None:
        player.been_hit_this_level = True
        player.kills_this_level    = 3
        payload = player.save()[player.name]
        assert payload["been_hit_this_level"] is True
        assert payload["kills_this_level"] == 3

    def test_load_restores_the_statistics_and_the_actor_state(self,
                                                              player: Player) -> None:
        player.been_seen_this_level = True
        player.deaths_this_level    = 2
        player.rect.topleft = player.cached_x, player.cached_y = (300, 200)
        payload = player.save()[player.name]

        player.been_seen_this_level = False
        player.deaths_this_level    = 0
        player.rect.topleft = (0, 0)

        player.load(payload)
        assert player.been_seen_this_level is True
        assert player.deaths_this_level == 2
        assert player.rect.topleft == (300, 200)


def test_a_dead_player_is_never_collected_by_the_level_purge(player: Player,
                                                             level) -> None:
    """``Level.queue_purge`` has no Player branch -- the engine reverts them instead."""
    player.hp = 0
    player.loop(0.016)
    assert all(player not in bucket for bucket in level.purge_queue.values())
