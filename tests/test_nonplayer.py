"""Tests for ``NonPlayer`` -- patrol routes, the alert state machine and player detection.

The alert machine (PATROL / WAIT / SEARCH / PURSUE) is the part of the game most
likely to regress silently, because a broken transition still *looks* like an NPC
walking around.  These tests drive each transition explicitly.
"""

from __future__ import annotations

import pygame
import pytest

from Actor import MovementState
from Block import Door
from Helpers import DifficultyScale, MovementDirection, PathPoint
from NonPlayer import NPCAlertState, NonPlayer


def _path(level, *tiles: tuple[int, int]) -> list[PathPoint]:
    """Build a patrol path from tile coordinates, in the shape ``load_path`` returns."""
    return [PathPoint(col * level.block_size, row * level.block_size)
            for col, row in tiles]


@pytest.fixture
def guard(make_enemy, player) -> NonPlayer:
    """A hostile, pathless guard four tiles to the player's right."""
    return make_enemy(col = 4, row = 1)


@pytest.fixture
def patroller(level, controller, player, sprite_master, enemy_audios) -> NonPlayer:
    """A guard walking a three-point route along row 1."""
    enemy = NonPlayer(level, controller, 4 * level.block_size, 1 * level.block_size,
                      sprite_master, enemy_audios, 1.0, level.block_size,
                      sprite = "TestAgent", path = _path(level, (4, 1), (6, 1), (8, 1)))
    level.enemies.append(enemy)
    return enemy


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #
class TestConstruction:
    def test_npcs_move_slower_than_the_player(self, guard: NonPlayer) -> None:
        assert guard.target_vel == NonPlayer.VELOCITY_TARGET

    def test_health_scales_with_difficulty(self, make_enemy) -> None:
        assert make_enemy(difficulty = 2.0, hp = 50).max_hp == 100

    def test_a_stationary_guard_sees_twice_as_far(self, level, guard: NonPlayer,
                                                  patroller: NonPlayer) -> None:
        # Sentries have to compensate for never turning a corner.
        assert guard.spot_range == NonPlayer.PLAYER_SPOT_RANGE * level.block_size * 2
        assert patroller.spot_range == NonPlayer.PLAYER_SPOT_RANGE * level.block_size

    def test_starts_in_the_patrol_state(self, guard: NonPlayer) -> None:
        assert guard.alert_state is NPCAlertState.PATROL

    def test_hostility_is_configurable(self, make_enemy) -> None:
        assert make_enemy().is_hostile is True
        assert make_enemy(is_hostile = False).is_hostile is False

    def test_path_points_are_re_seated_to_match_the_sprite(self, patroller: NonPlayer,
                                                           level) -> None:
        # Paths are authored on tile corners; the NPC stands centred with its feet down.
        offset_x = (level.block_size - patroller.rect.width) // 2
        assert patroller.patrol_path[0].x == 4 * level.block_size + offset_x

    def test_the_starting_waypoint_is_the_nearest_one(self, level, controller, player,
                                                      sprite_master,
                                                      enemy_audios) -> None:
        enemy = NonPlayer(level, controller, 6 * level.block_size, level.block_size,
                          sprite_master, enemy_audios, 1.0, level.block_size,
                          sprite = "TestAgent",
                          path = _path(level, (0, 1), (6, 1), (9, 1)))
        assert enemy.patrol_path_index == 1

    def test_the_starting_facing_points_at_the_first_waypoint(self, level, controller,
                                                              player, sprite_master,
                                                              enemy_audios) -> None:
        enemy = NonPlayer(level, controller, 6 * level.block_size, level.block_size,
                          sprite_master, enemy_audios, 1.0, level.block_size,
                          sprite = "TestAgent", path = _path(level, (2, 1)))
        assert enemy.facing is MovementDirection.LEFT

    def test_a_vision_cone_exists_for_both_states_and_both_facings(self,
                                                                   guard: NonPlayer) -> None:
        for mood in ("hidden", "spotted"):
            for facing in (MovementDirection.LEFT, MovementDirection.RIGHT):
                assert isinstance(guard.vision[mood][facing], pygame.Surface)

    def test_a_collision_message_is_loaded_from_its_file(self, make_enemy) -> None:
        enemy = make_enemy(collision_message = "message.txt")
        assert enemy.collision_message == ["First line.", "Second line."]

    def test_a_dict_collision_message_carries_text_and_audio(self, make_enemy,
                                                             assets_root) -> None:
        wav = assets_root / "SoundEffects" / "triggers" / "beep.wav"
        enemy = make_enemy(collision_message = {"text": "message.txt", "audio": str(wav)})
        assert enemy.collision_message["text"] == ["First line.", "Second line."]
        assert isinstance(enemy.collision_message["audio"], pygame.mixer.Sound)

    def test_a_bark_is_rendered_into_a_speech_box(self, make_enemy) -> None:
        enemy = make_enemy(bark = "bark.txt")
        assert isinstance(enemy.bark, pygame.Surface)
        assert enemy.has_barked is False


# --------------------------------------------------------------------------- #
# perception
# --------------------------------------------------------------------------- #
class TestSpotPlayer:
    def _face_the_player(self, guard: NonPlayer) -> None:
        guard.facing = guard.direction = MovementDirection.LEFT

    def test_sees_a_player_in_front_and_in_range(self, guard: NonPlayer) -> None:
        self._face_the_player(guard)
        assert guard.__spot_player__() is True

    def test_does_not_see_a_player_behind(self, guard: NonPlayer) -> None:
        guard.facing = MovementDirection.RIGHT
        assert guard.__spot_player__() is False

    def test_recently_taking_a_hit_lets_a_guard_spot_behind_them(self,
                                                                 guard: NonPlayer) -> None:
        guard.facing = MovementDirection.RIGHT
        guard.cooldowns["get_hit"] = 0.5
        assert guard.__spot_player__() is True

    def test_does_not_see_a_player_out_of_range(self, guard: NonPlayer, player) -> None:
        self._face_the_player(guard)
        guard.spot_range = 10
        assert guard.__spot_player__() is False

    def test_a_wall_between_them_blocks_line_of_sight(self, guard: NonPlayer,
                                                      make_block) -> None:
        self._face_the_player(guard)
        make_block(col = 2, row = 1)
        assert guard.__spot_player__() is False

    def test_spotting_starts_the_re_check_cooldown(self, guard: NonPlayer) -> None:
        self._face_the_player(guard)
        guard.__spot_player__()
        assert guard.cooldowns["spot_player"] == NonPlayer.PLAYER_SPOT_COOLDOWN

    def test_spotting_marks_the_level_as_no_longer_stealthed(self, guard: NonPlayer,
                                                             player) -> None:
        self._face_the_player(guard)
        guard.__spot_player__()
        assert player.been_seen_this_level is True

    def test_an_armed_guard_shoots_at_range(self, guard: NonPlayer) -> None:
        self._face_the_player(guard)
        guard.abilities["can_shoot"] = True
        guard.state = MovementState.IDLE
        guard.__spot_player__()
        assert len(guard.active_projectiles) == 1

    def test_an_armed_guard_holds_fire_up_close(self, guard: NonPlayer, player) -> None:
        self._face_the_player(guard)
        guard.abilities["can_shoot"] = True
        guard.rect.centerx = player.rect.centerx + 10
        guard.__spot_player__()
        assert guard.active_projectiles == []

    def test_a_crouching_player_is_harder_to_see(self, guard: NonPlayer, player) -> None:
        wide = guard.__adj_spot_range__()
        player.is_crouching = True
        assert guard.__adj_spot_range__() == pytest.approx(wide / 1.5)

    def test_a_grown_player_is_easier_to_see(self, guard: NonPlayer, player) -> None:
        base = guard.__adj_spot_range__()
        player.size = 2.0
        assert guard.__adj_spot_range__() == pytest.approx(base * 2)


class TestFindFloor:
    def test_reports_solid_ground_ahead(self, guard: NonPlayer, make_block,
                                        level) -> None:
        make_block(col = 4, row = 2)
        guard.rect.bottom = 2 * level.block_size + 1
        assert guard.__find_floor__(guard.rect.width) is True

    def test_reports_a_gap(self, guard: NonPlayer, level) -> None:
        guard.rect.bottom = 2 * level.block_size + 1
        assert guard.__find_floor__(guard.rect.width) is False


# --------------------------------------------------------------------------- #
# patrol bookkeeping
# --------------------------------------------------------------------------- #
class TestPatrolIndex:
    def test_advances_forwards(self, patroller: NonPlayer) -> None:
        patroller.patrol_path_index = 0
        patroller.__increment_patrol_index__()
        assert patroller.patrol_path_index == 1

    def test_reverses_at_the_far_end(self, patroller: NonPlayer) -> None:
        patroller.patrol_path_index = len(patroller.patrol_path) - 2
        patroller.__increment_patrol_index__()
        assert patroller.patrol_path_index == -1

    def test_walks_backwards_once_reversed(self, patroller: NonPlayer) -> None:
        patroller.patrol_path_index = -1
        patroller.__increment_patrol_index__()
        assert patroller.patrol_path_index == -2

    def test_wraps_round_at_the_near_end(self, patroller: NonPlayer) -> None:
        patroller.patrol_path_index = -len(patroller.patrol_path) + 1
        patroller.__increment_patrol_index__()
        assert patroller.patrol_path_index == 0

    def test_kill_at_end_removes_the_npc_instead_of_turning_round(
            self, level, controller, player, sprite_master, enemy_audios) -> None:
        enemy = NonPlayer(level, controller, 0, level.block_size, sprite_master,
                          enemy_audios, 1.0, level.block_size, sprite = "TestAgent",
                          path = _path(level, (0, 1), (2, 1)), kill_at_end = True)
        level.enemies.append(enemy)
        enemy.patrol_path_index = 0
        enemy.__increment_patrol_index__()
        assert enemy in level.purge_queue["enemies"]


# --------------------------------------------------------------------------- #
# alert state machine
# --------------------------------------------------------------------------- #
class TestEnterSearch:
    def test_enters_search_and_starts_both_timers(self, guard: NonPlayer) -> None:
        guard._enter_search(from_pursue = False)
        assert guard.alert_state is NPCAlertState.SEARCH
        assert guard.cooldowns["alert_cooldown"] == NonPlayer.ALERT_COOLDOWN
        assert guard.cooldowns["search_turn"] == NonPlayer.SEARCH_LOOK_TIME

    def test_spotting_the_player_shows_the_alert_icon(self, guard: NonPlayer, vfx) -> None:
        guard._enter_search(from_pursue = False)
        assert "SPOTPLAYER" in vfx.image_names

    def test_losing_the_player_shows_the_confused_icon(self, guard: NonPlayer,
                                                       vfx) -> None:
        guard._enter_search(from_pursue = True)
        assert "LOSEPLAYER" in vfx.image_names


class TestPatrolStateMachine:
    def test_a_guard_that_spots_the_player_moves_to_search(self, guard: NonPlayer) -> None:
        guard.facing = guard.direction = MovementDirection.LEFT
        guard.patrol(0.016)
        assert guard.alert_state is NPCAlertState.SEARCH

    def test_search_swings_the_guard_round_when_the_look_timer_expires(
            self, guard: NonPlayer) -> None:
        guard.alert_state = NPCAlertState.SEARCH
        guard.cooldowns["search_turn"] = 0
        facing = guard.facing
        guard.patrol(0.016)
        assert guard.facing is facing.swap()
        assert guard.cooldowns["search_turn"] == NonPlayer.SEARCH_LOOK_TIME

    def test_search_escalates_to_pursue_when_the_player_is_still_visible(
            self, guard: NonPlayer) -> None:
        guard.alert_state = NPCAlertState.SEARCH
        guard.facing = guard.direction = MovementDirection.LEFT
        guard.cooldowns["alert_cooldown"] = 0
        guard.cooldowns["search_turn"]    = 1.0
        guard.patrol(0.016)
        assert guard.alert_state is NPCAlertState.PURSUE

    def test_search_falls_back_to_patrol_when_the_player_is_gone(self,
                                                                 guard: NonPlayer) -> None:
        guard.alert_state = NPCAlertState.SEARCH
        guard.facing = guard.direction = MovementDirection.RIGHT
        guard.cooldowns["alert_cooldown"] = 0
        guard.cooldowns["search_turn"]    = 1.0
        guard.patrol(0.016)
        assert guard.alert_state is NPCAlertState.PATROL

    def test_a_waiting_guard_holds_until_the_timer_runs_out(self,
                                                            patroller: NonPlayer) -> None:
        patroller.alert_state      = NPCAlertState.WAIT
        patroller.cooldowns["wait"] = 1.0
        patroller.patrol(0.016)
        assert patroller.alert_state is NPCAlertState.WAIT
        assert patroller.should_move_horiz is False

    def test_a_waiting_guard_resumes_when_the_timer_expires(self,
                                                            patroller: NonPlayer) -> None:
        patroller.alert_state       = NPCAlertState.WAIT
        patroller.cooldowns["wait"] = 0
        patroller.patrol(0.016)
        assert patroller.alert_state is NPCAlertState.PATROL

    def test_a_waiting_guard_can_still_be_startled(self, patroller: NonPlayer) -> None:
        patroller.alert_state       = NPCAlertState.WAIT
        patroller.cooldowns["wait"] = 1.0
        patroller.facing = patroller.direction = MovementDirection.LEFT
        patroller.patrol(0.016)
        assert patroller.alert_state is NPCAlertState.SEARCH

    def test_a_pursuing_guard_that_loses_the_player_drops_to_search(
            self, patroller: NonPlayer) -> None:
        patroller.alert_state = NPCAlertState.PURSUE
        patroller.facing = patroller.direction = MovementDirection.RIGHT
        patroller.patrol(0.016)
        assert patroller.alert_state is NPCAlertState.SEARCH

    def test_a_pursuing_guard_chases_the_player(self, patroller: NonPlayer,
                                                player) -> None:
        patroller.alert_state = NPCAlertState.PURSUE
        patroller.facing = patroller.direction = MovementDirection.LEFT
        patroller.cooldowns["spot_player"] = 1.0
        patroller.patrol(0.016)
        assert patroller.should_move_horiz is True
        assert patroller.direction is MovementDirection.LEFT

    def test_an_armed_pursuer_backs_off_to_its_preferred_range(self,
                                                               patroller: NonPlayer,
                                                               player) -> None:
        patroller.alert_state = NPCAlertState.PURSUE
        patroller.abilities["can_shoot"] = True
        patroller.cooldowns["spot_player"] = 1.0
        patroller.rect.centerx = player.rect.centerx + 20
        patroller.patrol(0.016)
        assert patroller.facing is patroller.direction.swap()

    def test_an_armed_pursuer_stands_and_fires_at_range(self, patroller: NonPlayer) -> None:
        patroller.alert_state = NPCAlertState.PURSUE
        patroller.abilities["can_shoot"] = True
        patroller.cooldowns["spot_player"] = 1.0
        patroller.patrol(0.016)
        assert patroller.is_attacking is True
        assert patroller.x_vel == 0.0

    def test_a_guard_recovering_from_a_hit_does_not_act(self, guard: NonPlayer) -> None:
        guard.cooldowns["get_hit"] = 1.0
        guard.alert_state = NPCAlertState.PATROL
        guard.facing = guard.direction = MovementDirection.LEFT
        guard.patrol(0.016)
        assert guard.alert_state is NPCAlertState.PATROL

    @pytest.mark.parametrize("state", [MovementState.WIND_UP, MovementState.WIND_DOWN])
    def test_a_guard_mid_attack_animation_does_not_act(self, guard: NonPlayer,
                                                       state) -> None:
        guard.state = state
        guard.facing = guard.direction = MovementDirection.LEFT
        guard.patrol(0.016)
        assert guard.alert_state is NPCAlertState.PATROL

    def test_a_friendly_npc_never_reacts_to_the_player(self, make_enemy, player) -> None:
        friend = make_enemy(col = 4, row = 1, is_hostile = False)
        friend.facing = friend.direction = MovementDirection.LEFT
        friend.patrol(0.016)
        assert friend.alert_state is NPCAlertState.PATROL

    def test_a_patroller_walks_towards_its_waypoint(self, patroller: NonPlayer) -> None:
        patroller.patrol_path_index = 1
        patroller.alert_state = NPCAlertState.PATROL
        patroller.facing = patroller.direction = MovementDirection.RIGHT
        patroller.cooldowns["spot_player"] = 0
        patroller.is_hostile = False           # keep detection out of this one
        patroller.patrol(0.016)
        assert patroller.should_move_horiz is True
        assert patroller.direction is MovementDirection.RIGHT

    def test_reaching_a_wait_waypoint_starts_the_wait(self, patroller: NonPlayer) -> None:
        patroller.is_hostile = False
        patroller.patrol_path[0].wait = True
        patroller.patrol_path_index   = 0
        patroller.rect.x = int(patroller.patrol_path[0].x)
        patroller.patrol(0.016)
        assert patroller.alert_state is NPCAlertState.WAIT
        assert patroller.cooldowns["wait"] == NonPlayer.PATH_WAIT_TIME

    def test_reaching_a_plain_waypoint_advances_the_index(self,
                                                          patroller: NonPlayer) -> None:
        patroller.is_hostile = False
        patroller.patrol_path_index = 0
        patroller.rect.x = int(patroller.patrol_path[0].x)
        patroller.patrol(0.016)
        assert patroller.patrol_path_index == 1

    def test_a_patroller_jumps_a_gap_in_the_floor(self, patroller: NonPlayer,
                                                  make_block, level) -> None:
        patroller.is_hostile = False
        patroller.patrol_path_index = 1
        patroller.should_move_vert  = False
        patroller.jump_count        = 0
        patroller.patrol(0.016)
        assert patroller.jump_count == 1


# --------------------------------------------------------------------------- #
# collisions
# --------------------------------------------------------------------------- #
class TestCollide:
    def test_an_unlocked_door_is_opened_and_waited_for(self, patroller: NonPlayer,
                                                       level, controller, image_master,
                                                       block_audios) -> None:
        door = Door(level, controller, patroller.rect.right + 1, patroller.rect.y,
                    level.block_size, level.block_size, image_master, block_audios, True)
        patroller.direction = MovementDirection.RIGHT
        patroller.collide(door)
        assert door.is_open is True
        assert patroller._waiting_for_door is True

    def test_a_guard_waiting_on_a_door_stands_still(self, patroller: NonPlayer, level,
                                                    controller, image_master,
                                                    block_audios) -> None:
        door = Door(level, controller, patroller.rect.x, patroller.rect.y,
                    level.block_size, level.block_size, image_master, block_audios, True)
        level.add_door(door, patroller.rect.x // level.block_size)
        patroller._waiting_for_door = True
        patroller.is_hostile = False
        patroller.patrol(0.016)
        assert patroller.should_move_horiz is False

    def test_the_wait_clears_once_the_door_is_out_of_the_way(self, patroller: NonPlayer) -> None:
        patroller.is_hostile = False
        patroller._waiting_for_door = True
        patroller.patrol(0.016)
        assert patroller._waiting_for_door is False

    def test_a_locked_door_makes_a_patroller_turn_round(self, patroller: NonPlayer,
                                                        level, controller, image_master,
                                                        block_audios) -> None:
        door = Door(level, controller, patroller.rect.right + 1, patroller.rect.y,
                    level.block_size, level.block_size, image_master, block_audios, True,
                    is_locked = True)
        patroller.direction = patroller.facing = MovementDirection.RIGHT
        patroller.patrol_path_index = 0
        patroller.collide(door)
        assert patroller._waiting_for_door is False

    def test_a_low_obstacle_is_jumped(self, patroller: NonPlayer, make_block) -> None:
        block = make_block(col = 5, row = 1, is_stacked = False, place = False)
        block.rect.topleft = (patroller.rect.right + 1, patroller.rect.y)
        patroller.direction = MovementDirection.RIGHT
        patroller.collide(block)
        assert patroller.jump_count == 1

    def test_bumping_into_the_player_queues_the_collision_message(self, make_enemy,
                                                                  player) -> None:
        enemy = make_enemy(collision_message = "message.txt")
        enemy.collide(player)
        assert enemy.queued_message == ["First line.", "Second line."]
        assert enemy.collision_message is None

    def test_the_collision_message_only_plays_once(self, make_enemy, player) -> None:
        enemy = make_enemy(collision_message = "message.txt")
        enemy.collide(player)
        enemy.queued_message = None
        enemy.collide(player)
        assert enemy.queued_message is None

    def test_bumping_into_the_player_triggers_a_bark(self, make_enemy, player) -> None:
        enemy = make_enemy(bark = "bark.txt")
        enemy.collide(player)
        assert enemy.has_barked is True
        assert enemy.cooldowns["bark"] == NonPlayer.BARK_TIME

    def test_collide_always_reports_the_npc_as_solid(self, guard: NonPlayer,
                                                     player) -> None:
        assert guard.collide(player) is True


class TestQueuedMessage:
    def test_a_text_message_is_displayed_without_typing(self, make_enemy, player,
                                                        display_texts) -> None:
        enemy = make_enemy(collision_message = "message.txt")
        enemy.collide(player)
        enemy.play_queued_message()
        assert display_texts[-1].lines == ["First line.", "Second line."]
        assert display_texts[-1].kwargs["should_type_text"] is False

    def test_an_audio_message_passes_the_sound_through(self, make_enemy, player,
                                                       display_texts,
                                                       assets_root) -> None:
        wav = assets_root / "SoundEffects" / "triggers" / "beep.wav"
        enemy = make_enemy(collision_message = {"text": "message.txt", "audio": str(wav)})
        enemy.collide(player)
        enemy.play_queued_message()
        assert display_texts[-1].kwargs["audio"] is not None

    def test_the_queue_is_cleared_after_playing(self, make_enemy, player) -> None:
        enemy = make_enemy(collision_message = "message.txt")
        enemy.collide(player)
        enemy.play_queued_message()
        assert enemy.queued_message is None

    def test_nothing_queued_is_a_cheap_no_op(self, guard: NonPlayer,
                                             display_texts) -> None:
        guard.play_queued_message()
        assert display_texts == []


# --------------------------------------------------------------------------- #
# barks, drawing, death
# --------------------------------------------------------------------------- #
class TestBark:
    def test_a_bark_expires_once_its_cooldown_runs_out(self, make_enemy, player) -> None:
        enemy = make_enemy(bark = "bark.txt")
        enemy.collide(player)
        enemy.cooldowns["bark"] = 0
        enemy.loop(0.016)
        assert enemy.bark is None
        assert enemy.has_barked is False

    def test_set_bark_returns_none_for_empty_text(self, guard: NonPlayer) -> None:
        assert guard.set_bark(None) is None
        assert guard.set_bark("") is None

    def test_set_bark_joins_multiple_lines(self, guard: NonPlayer) -> None:
        assert isinstance(guard.set_bark(["one", "two"]), pygame.Surface)


class TestDraw:
    @staticmethod
    def _cone_sample(enemy) -> tuple[int, int]:
        """A point well inside the drawn cone but clear of the NPC's own sprite."""
        return (enemy.rect.centerx + 300,
                enemy.rect.y + (7 * enemy.rect.height // 24) + 4)

    def test_the_vision_cone_is_shown_on_easy_difficulties(self, make_enemy, player,
                                                           surface) -> None:
        enemy = make_enemy(difficulty = float(DifficultyScale.EASIEST))
        enemy.rect.topleft = (100, 100)
        enemy.draw(surface, 0, 0, enemy.controller.master_volume)
        assert surface.get_at(self._cone_sample(enemy)).a > 0

    def test_the_vision_cone_is_hidden_on_medium_and_above(self, make_enemy, player,
                                                           surface) -> None:
        enemy = make_enemy(difficulty = float(DifficultyScale.MEDIUM))
        enemy.rect.topleft = (100, 100)
        enemy.draw(surface, 0, 0, enemy.controller.master_volume)
        assert surface.get_at(self._cone_sample(enemy)).a == 0

    def test_a_friendly_npc_never_shows_a_cone(self, make_enemy, player,
                                               surface) -> None:
        enemy = make_enemy(difficulty = float(DifficultyScale.EASIEST),
                           is_hostile = False)
        enemy.rect.topleft = (100, 100)
        enemy.draw(surface, 0, 0, enemy.controller.master_volume)
        assert surface.get_at(self._cone_sample(enemy)).a == 0

    def test_an_active_bark_is_drawn_above_the_npc(self, make_enemy, player,
                                                   surface) -> None:
        enemy = make_enemy(bark = "bark.txt")
        enemy.rect.topleft = (100, 300)
        enemy.collide(player)
        enemy.draw(surface, 0, 0, enemy.controller.master_volume)
        assert surface.get_at((105, 300 - enemy.bark.get_height() + 5)).a > 0


class TestDeath:
    def test_dying_credits_the_player_with_a_kill(self, guard: NonPlayer, player) -> None:
        guard.die()
        assert player.kills_this_level == 1

    def test_alert_state_str_is_the_bare_name(self) -> None:
        assert str(NPCAlertState.PURSUE) == "PURSUE"
