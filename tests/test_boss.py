"""Tests for ``Boss`` -- on-screen presence, the boss health bar and boss music."""

from __future__ import annotations

import pytest

from Actor import MovementState
from Boss import Boss
from Trigger import SaveTrigger


@pytest.fixture
def boss(level, controller, player, sprite_master, enemy_audios) -> Boss:
    boss = Boss(level, controller, 5 * level.block_size, level.block_size,
                sprite_master, enemy_audios, 1.0, level.block_size,
                sprite = "TestAgent", hp = 500)
    level.enemies.append(boss)
    return boss


class TestConstruction:
    def test_a_boss_sees_further_than_a_regular_guard(self, boss: Boss,
                                                      level) -> None:
        # A pathless NPC doubles its range, so the constant is applied twice over.
        assert boss.spot_range == Boss.PLAYER_SPOT_RANGE * level.block_size * 2

    def test_bosses_use_the_animated_attack_sequence(self, boss: Boss) -> None:
        assert boss.is_animated_attack is True

    def test_the_wind_up_frames_have_audio_hooks(self, boss: Boss) -> None:
        for state in ("WIND_UP", "ATTACK_ANIM", "WIND_DOWN"):
            assert state in boss.audio_trigger_frames

    def test_music_is_resolved_from_the_music_folder(self, level, controller, player,
                                                     sprite_master, enemy_audios) -> None:
        boss = Boss(level, controller, 0, 0, sprite_master, enemy_audios, 1.0,
                    level.block_size, sprite = "TestAgent",
                    music = "track_one.mp3 track_two.mp3")
        assert len(boss.music) == 2

    def test_no_music_configured_leaves_it_unset(self, boss: Boss) -> None:
        assert boss.music is None

    def test_the_health_bar_is_shown_by_default(self, boss: Boss) -> None:
        assert boss.show_health_bar is True


class TestOnScreenPresence:
    def test_a_nearby_boss_becomes_on_screen(self, boss: Boss, player) -> None:
        player.rect.topleft = boss.rect.topleft
        boss.__update_onscreen_presence__()
        assert boss.is_on_screen is True

    def test_a_distant_boss_drops_off_screen(self, boss: Boss, player) -> None:
        boss.is_on_screen = True
        player.rect.topleft = (0, 0)
        boss.rect.topleft   = (5000, 5000)
        boss.__update_onscreen_presence__()
        assert boss.is_on_screen is False

    def test_presence_uses_hysteresis_so_the_bar_does_not_flicker(self, boss: Boss,
                                                                  player, level) -> None:
        # Between spot_range and 2 * spot_range neither branch fires, so the state
        # holds whatever it was.
        player.rect.topleft = (boss.rect.x + int(1.5 * boss.spot_range), boss.rect.y)
        boss.is_on_screen = True
        level.boss_hp_pct = 0.5
        boss.__update_onscreen_presence__()
        assert boss.is_on_screen is True


class TestHealthBar:
    def test_an_on_screen_boss_publishes_its_health(self, boss: Boss, level) -> None:
        boss.is_on_screen = True
        boss.__update_health_bar__()
        assert level.boss_hp_pct == pytest.approx(1.0)

    def test_the_percentage_tracks_damage(self, boss: Boss, level) -> None:
        boss.is_on_screen = True
        boss.hp = boss.max_hp / 4
        boss.__update_health_bar__()
        assert level.boss_hp_pct == pytest.approx(0.25)

    def test_an_off_screen_boss_clears_the_bar(self, boss: Boss, level) -> None:
        level.boss_hp_pct = 0.5
        boss.is_on_screen = False
        boss.__update_health_bar__()
        assert level.boss_hp_pct is None

    def test_a_boss_configured_without_a_bar_never_publishes_one(self, level,
                                                                 controller, player,
                                                                 sprite_master,
                                                                 enemy_audios) -> None:
        boss = Boss(level, controller, 0, 0, sprite_master, enemy_audios, 1.0,
                    level.block_size, sprite = "TestAgent", show_health_bar = False)
        boss.is_on_screen = True
        boss.loop(0.016)
        assert level.boss_hp_pct is None


class TestMusic:
    def test_arriving_on_screen_queues_the_boss_track(self, boss: Boss, level,
                                                      controller) -> None:
        boss.music = ["track_one.mp3"]
        boss.is_on_screen = True
        boss.__queue_music__()
        assert boss.music_is_playing is True

    def test_leaving_the_arena_restores_the_level_track(self, boss: Boss,
                                                        controller) -> None:
        boss.music_is_playing = True
        boss.is_on_screen     = False
        boss.__queue_music__()
        assert boss.music_is_playing is False

    def test_dying_restores_the_level_track(self, boss: Boss) -> None:
        boss.music_is_playing = True
        boss.is_on_screen     = True
        boss.hp = 0
        boss.__queue_music__()
        assert boss.music_is_playing is False


class TestDeath:
    def test_dying_clears_the_health_bar(self, boss: Boss, level, player) -> None:
        boss.die()
        assert level.boss_hp_pct == 0

    def test_dying_fires_the_linked_triggers(self, boss: Boss, level, controller,
                                             player) -> None:
        trigger = SaveTrigger(level, controller, 0, 0, 10, 10, None)
        boss.trigger = [trigger]
        boss.die()
        assert trigger.has_fired is True

    def test_dying_still_credits_the_player_with_a_kill(self, boss: Boss,
                                                        player) -> None:
        boss.die()
        assert player.kills_this_level == 1


class TestSprite:
    def test_update_sprite_delegates_to_the_actor_animation(self, boss: Boss) -> None:
        boss.animation_count = 0
        assert boss.update_sprite() == 0

    def test_boss_specific_attack_audio_is_looked_up_by_name(self, boss: Boss,
                                                             level) -> None:
        # The folder key is "<FIRST WORD OF NAME>_<STATE>"; with no such bank loaded
        # the lookup simply finds nothing and no audio is queued.
        boss.state = MovementState.WIND_UP
        boss.update_sprite()
        assert boss.active_audio is None


def test_the_loop_runs_presence_health_and_music_before_the_actor_loop(boss: Boss,
                                                                      player,
                                                                      level) -> None:
    player.rect.topleft = boss.rect.topleft
    boss.loop(0.016)
    assert boss.is_on_screen is True
    assert level.boss_hp_pct == pytest.approx(1.0)
