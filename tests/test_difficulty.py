"""The difficulty contract: how many hits it takes, at every setting on the ladder.

Difficulty in Agent Glitch is expressed as *durability*, not damage.  Every hit --
the agent's and an enemy's -- lands for the same amount at every setting; what the
setting changes is how much of it each side can absorb.  The design target is a
straight line between the two ends of the ladder:

    setting     hits to kill an enemy     hits before the agent dies
    EASIEST      1                        10
    EASY         2                         8
    MEDIUM       3                         6
    HARD         4                         4
    HARDEST      5                         2

These tests are the executable form of that table.  Rather than asserting on the
scaling helpers alone, they count real hits through ``get_hit`` -- the path the
game actually takes -- so that a change to the damage numbers, the health numbers,
or the death threshold all show up here as a changed hit count.
"""

from __future__ import annotations

import pytest

from Actor import Actor
from Helpers import (
    DifficultyScale,
    PathPoint,
    HITS_TO_DIE_RANGE,
    HITS_TO_KILL_RANGE,
    difficulty_ratio,
    enemy_health_scale,
    player_health_scale,
)
from NonPlayer import NonPlayer
from Player import Player


# The table above, as data.  Ordered easiest to hardest.
CONTRACT: list[tuple[DifficultyScale, int, int]] = [
    (DifficultyScale.EASIEST, 1, 10),
    (DifficultyScale.EASY,    2,  8),
    (DifficultyScale.MEDIUM,  3,  6),
    (DifficultyScale.HARD,    4,  4),
    (DifficultyScale.HARDEST, 5,  2),
]

MAX_HITS: int = 50  # a loop guard; any real answer is far below this


def _hits_to_drop(target: Actor, attacker: Actor) -> int:
    """Return how many times `attacker` must hit `target` before it is dead."""
    for hit in range(1, MAX_HITS + 1):
        target.get_hit(attacker)
        if target.hp <= 0:
            return hit
    raise AssertionError(
        f"{target.name} survived {MAX_HITS} hits of {attacker.attack_damage} "
        f"from {target.max_hp} hp -- the hit is probably doing nothing"
    )


# --------------------------------------------------------------------------- #
# the contract itself
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(("scale", "to_kill", "to_die"), CONTRACT,
                         ids = [row[0].name for row in CONTRACT])
class TestTheHitsContract:
    def test_hits_to_kill_an_enemy(self, make_player, make_enemy,
                                   scale, to_kill, to_die) -> None:
        player = make_player(difficulty = scale)
        enemy  = make_enemy(col = 4, difficulty = scale)
        assert _hits_to_drop(enemy, player) == to_kill

    def test_hits_before_the_agent_dies(self, make_player, make_enemy,
                                        scale, to_kill, to_die) -> None:
        player = make_player(difficulty = scale)
        enemy  = make_enemy(col = 4, difficulty = scale)
        assert _hits_to_drop(player, enemy) == to_die

    def test_switching_to_the_setting_mid_run_honours_the_same_contract(
            self, make_player, make_enemy, scale, to_kill, to_die) -> None:
        """The menu path has to land on the same numbers as the level-build path."""
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        player.set_difficulty(float(scale))
        enemy.set_difficulty(float(scale))
        assert _hits_to_drop(enemy, player) == to_kill

    def test_switching_to_the_setting_mid_run_honours_the_death_count(
            self, make_player, make_enemy, scale, to_kill, to_die) -> None:
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        player.set_difficulty(float(scale))
        enemy.set_difficulty(float(scale))
        assert _hits_to_drop(player, enemy) == to_die


class TestTheShapeOfTheCurve:
    def test_it_is_a_straight_line_in_both_directions(self) -> None:
        """Evenly spaced steps -- one hit harder to kill, one fewer to survive, each notch."""
        kills = [row[1] for row in CONTRACT]
        dies  = [row[2] for row in CONTRACT]
        assert {b - a for a, b in zip(kills, kills[1:])} == {1}
        assert {b - a for a, b in zip(dies, dies[1:])} == {-2}

    def test_damage_is_flat_on_both_sides(self, make_player, make_enemy) -> None:
        agent    = {make_player(difficulty = s).attack_damage for s in DifficultyScale}
        opponent = {make_enemy(col = 4, difficulty = s).attack_damage for s in DifficultyScale}
        assert agent == {Actor.ATTACK_DAMAGE * 2}
        assert opponent == {Actor.ATTACK_DAMAGE}

    def test_the_agent_loses_durability_as_the_setting_rises(self, make_player) -> None:
        healths = [make_player(difficulty = s).max_hp for s in DifficultyScale]
        assert healths == [100, 80, 60, 40, 20]

    def test_enemies_gain_durability_as_the_setting_rises(self, make_enemy) -> None:
        healths = [make_enemy(col = 4, difficulty = s, hp = 100).max_hp
                   for s in DifficultyScale]
        assert healths == [20, 40, 60, 80, 100]

    def test_enemies_are_authored_at_full_strength(self, make_enemy) -> None:
        """HARDEST is the number in the .agd file; every easier setting shaves it down."""
        assert make_enemy(col = 4, difficulty = DifficultyScale.HARDEST, hp = 37).max_hp == 37


# --------------------------------------------------------------------------- #
# the helpers underneath
# --------------------------------------------------------------------------- #
class TestDifficultyRatio:
    def test_the_ladder_is_evenly_spaced_in_position(self) -> None:
        """The values are not evenly spaced, so "linear" has to mean linear in position."""
        assert [difficulty_ratio(float(s)) for s in DifficultyScale] == [0.0, 0.25, 0.5, 0.75, 1.0]

    def test_a_value_between_two_settings_interpolates_within_that_step(self) -> None:
        # 0.75 is halfway between EASY (0.50) and MEDIUM (1.00), so halfway between
        # their positions -- 0.25 and 0.50 -- even though the raw span is wider than
        # the one below it.
        assert difficulty_ratio(0.75) == pytest.approx(0.375)

    def test_it_clamps_off_either_end(self) -> None:
        assert difficulty_ratio(-5.0) == 0.0
        assert difficulty_ratio(0.0) == 0.0
        assert difficulty_ratio(99.0) == 1.0

    def test_it_is_monotonic(self) -> None:
        samples = [difficulty_ratio(v / 20) for v in range(0, 60)]
        assert samples == sorted(samples)


class TestHealthScales:
    def test_the_player_scale_walks_the_hits_to_die_range(self) -> None:
        easiest, hardest = HITS_TO_DIE_RANGE
        assert player_health_scale(DifficultyScale.EASIEST) == pytest.approx(1.0)
        assert player_health_scale(DifficultyScale.HARDEST) == pytest.approx(hardest / easiest)

    def test_the_enemy_scale_walks_the_hits_to_kill_range(self) -> None:
        easiest, hardest = HITS_TO_KILL_RANGE
        assert enemy_health_scale(DifficultyScale.EASIEST) == pytest.approx(easiest / hardest)
        assert enemy_health_scale(DifficultyScale.HARDEST) == pytest.approx(1.0)

    def test_the_two_scales_move_in_opposite_directions(self) -> None:
        player = [player_health_scale(s) for s in DifficultyScale]
        enemy  = [enemy_health_scale(s) for s in DifficultyScale]
        assert player == sorted(player, reverse = True)
        assert enemy == sorted(enemy)

    def test_neither_scale_ever_reaches_zero(self) -> None:
        """A zero scale would mean a one-frame death or an enemy that cannot be hit."""
        for value in [v / 20 for v in range(0, 60)]:
            assert player_health_scale(value) > 0
            assert enemy_health_scale(value) > 0


# --------------------------------------------------------------------------- #
# round numbers mean the death threshold has to be exact
# --------------------------------------------------------------------------- #
class TestDepletedIsDead:
    def test_a_hit_that_lands_exactly_on_zero_kills(self, make_player, make_enemy) -> None:
        """Every setting lands damage on round numbers, so zero is the common case."""
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        enemy.hp = player.attack_damage
        enemy.get_hit(player)
        assert enemy.hp == 0
        assert enemy.cooldowns["dead"] == Actor.DEATH_TIME

    def test_the_death_animation_gets_to_play(self, make_player, make_enemy) -> None:
        """Entity.loop holds off the purge while the dead cooldown is still running.

        With the kill landing on exactly zero and die() never firing, that cooldown
        stayed at 0.0 and the corpse was queued for removal on the very next frame --
        no death animation, no body.
        """
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        enemy.hp = player.attack_damage
        enemy.get_hit(player)
        enemy.loop(0.016)
        assert enemy not in enemy.level.purge_queue["enemies"]
        assert enemy.cooldowns["dead"] > 0

    def test_the_body_is_purged_once_the_cooldown_runs_out(self, make_player,
                                                           make_enemy) -> None:
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        enemy.hp = player.attack_damage
        enemy.get_hit(player)
        enemy.loop(Actor.DEATH_TIME + 0.1)
        assert enemy in enemy.level.purge_queue["enemies"]

    def test_a_kill_is_credited_exactly_once(self, make_player, make_enemy) -> None:
        """A corpse stays collidable for DEATH_TIME; hitting it must not re-credit."""
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        player.kills_this_level = 0
        for _ in range(MAX_HITS):
            enemy.get_hit(player)
        assert player.kills_this_level == 1

    def test_a_corpse_takes_no_further_damage(self, make_player, make_enemy) -> None:
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 4, difficulty = DifficultyScale.MEDIUM)
        _hits_to_drop(enemy, player)
        resting = enemy.hp
        enemy.get_hit(player)
        assert enemy.hp == resting

    def test_a_melee_swing_reaches_a_live_enemy_standing_on_top_of_the_agent(
            self, make_player, make_enemy) -> None:
        """The positive control for the corpse test below -- proves the swing connects."""
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 1, row = 1, difficulty = DifficultyScale.MEDIUM)
        enemy.is_hostile = True
        before = enemy.hp
        player.attack()
        assert enemy.hp == before - player.attack_damage

    def test_the_agent_does_not_swing_at_a_corpse(self, make_player, make_enemy) -> None:
        player = make_player(difficulty = DifficultyScale.MEDIUM)
        enemy  = make_enemy(col = 1, row = 1, difficulty = DifficultyScale.MEDIUM)
        enemy.is_hostile        = True
        enemy.hp                = 0
        player.kills_this_level = 0
        player.attack()
        assert player.kills_this_level == 0
        assert enemy.hp == 0

    def test_a_corpse_is_not_shoved_across_the_floor(self, make_player, level,
                                                    controller, sprite_master,
                                                    enemy_audios) -> None:
        """A swing pushes a patrolling guard back.  A dead one should just lie there."""
        def _guard() -> NonPlayer:
            guard = NonPlayer(level, controller, level.block_size, level.block_size,
                              sprite_master, enemy_audios, DifficultyScale.MEDIUM,
                              level.block_size, sprite = "TestAgent",
                              path = [PathPoint(level.block_size, level.block_size),
                                      PathPoint(6 * level.block_size, level.block_size)])
            guard.is_hostile = True
            level.enemies.append(guard)
            return guard

        player = make_player(difficulty = DifficultyScale.MEDIUM)

        alive = _guard()
        player.attack()
        assert alive.push_x != 0            # the positive control: swings do shove

        alive.hp    = 0
        alive.push_x = 0
        player.attack()
        assert alive.push_x == 0
