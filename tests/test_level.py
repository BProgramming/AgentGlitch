"""Tests for ``Level`` -- the entity registry, spatial index and achievement ledger.

``Level.__init__`` parses a grid and builds every entity in it; that path is covered
end to end in ``tests/test_integration_level.py``.  Everything here exercises the
*methods* on a level whose entity graph has been injected directly, using the
``StubLevel`` subclass so the code under test is the shipped implementation.
"""

from __future__ import annotations

from pathlib import Path

import pygame
import pytest

from Block import FallingHazard
from Level import Level
from ParticleEffect import FilmGrain, Rain, Snow
from Trigger import Trigger
from support import stubs


# --------------------------------------------------------------------------- #
# formatted_time
# --------------------------------------------------------------------------- #
class TestFormattedTime:
    @pytest.mark.parametrize("seconds, expected", [
        (0,       "00:00.0"),
        (5.4,     "00:05.4"),
        (59.99,   "00:59.9"),
        (60,      "01:00.0"),
        (65.5,    "01:05.5"),
        (605.0,   "10:05.0"),
        (3599.9,  "59:59.9"),
    ])
    def test_formats_as_mm_ss_t(self, level, seconds, expected) -> None:
        level.time = seconds
        assert level.formatted_time == expected

    def test_stays_within_the_seven_characters_the_hud_allows(self, level) -> None:
        # HUD.__draw_time__ silently refuses to render anything longer than 7 chars.
        for seconds in (0, 61, 599.9, 3599.9):
            level.time = seconds
            assert len(level.formatted_time) == 7

    def test_the_clock_clamps_instead_of_overflowing_the_hud_budget(self, level) -> None:
        """Past 99 minutes the string would grow to 8 characters and vanish.

        HUD.__draw_time__ refuses to draw anything longer than 7, so the clock is
        pinned at its maximum rather than disappearing.
        """
        level.time = 6000                      # 100 minutes
        assert level.formatted_time == "99:59.9"
        level.time = 1_000_000
        assert level.formatted_time == "99:59.9"

    def test_a_negative_clock_reads_as_zero(self, level) -> None:
        level.time = -5
        assert level.formatted_time == "00:00.0"


# --------------------------------------------------------------------------- #
# entity registry
# --------------------------------------------------------------------------- #
class TestEntities:
    def test_entities_lists_the_player_first(self, level, player) -> None:
        assert level.entities[0] is player

    def test_entities_concatenates_every_category(self, level, player, controller,
                                                  make_block, make_hazard, make_enemy,
                                                  make_objective) -> None:
        trigger   = Trigger(level, controller, 0, 0, 10, 10, None)
        level.triggers.append(trigger)
        block     = make_block(col = 0, row = 7)
        hazard    = make_hazard()
        enemy     = make_enemy()
        objective = make_objective()

        assert level.entities == [player, trigger, block, hazard, enemy, objective]

    def test_the_player_property_exposes_the_private_field(self, level, player) -> None:
        assert level.player is player

    def test_retro_is_read_only_from_the_private_field(self, level, retro_level) -> None:
        assert level.retro is False
        assert retro_level.retro is True


# --------------------------------------------------------------------------- #
# spatial queries
# --------------------------------------------------------------------------- #
class TestGetEntitiesInRange:
    def test_returns_the_static_blocks_around_a_point(self, level, make_block) -> None:
        here  = make_block(col = 4, row = 4)
        near  = make_block(col = 5, row = 4)
        far   = make_block(col = 9, row = 4)
        point = (4 * level.block_size, 4 * level.block_size)

        found = level.get_entities_in_range(point, blocks_only = True, include_doors = False)
        assert here in found and near in found
        assert far not in found

    def test_the_window_widens_with_the_distance_arguments(self, level, make_block) -> None:
        far   = make_block(col = 7, row = 4)
        point = (4 * level.block_size, 4 * level.block_size)

        assert far not in level.get_entities_in_range(point, blocks_only = True,
                                                      include_doors = False)
        assert far in level.get_entities_in_range(point, dist_x = (1, 4), blocks_only = True,
                                                  include_doors = False)

    def test_empty_tiles_are_filtered_out(self, level) -> None:
        found = level.get_entities_in_range((0, 0), blocks_only = True, include_doors = False)
        assert None not in found

    def test_clamps_at_the_level_edges(self, level, make_block) -> None:
        corner = make_block(col = 0, row = 0)
        assert corner in level.get_entities_in_range((0, 0), blocks_only = True,
                                                     include_doors = False)

        last_col = len(level.static_blocks[0]) - 1
        last_row = len(level.static_blocks) - 1
        edge = make_block(col = last_col, row = last_row)
        point = (last_col * level.block_size, last_row * level.block_size)
        assert edge in level.get_entities_in_range(point, blocks_only = True,
                                                   include_doors = False)

    def test_doors_are_included_by_default_and_can_be_excluded(self, level,
                                                               make_door) -> None:
        door  = make_door(col = 4, row = 4)
        point = (4 * level.block_size, 4 * level.block_size)
        assert door in level.get_entities_in_range(point, blocks_only = True)
        assert door not in level.get_entities_in_range(point, blocks_only = True,
                                                       include_doors = False)

    def test_doors_are_indexed_by_column_not_row(self, level, make_door) -> None:
        """The door index is keyed on x alone, so a door is 'near' any y in its column."""
        door = make_door(col = 4, row = 0)
        point = (4 * level.block_size, 7 * level.block_size)
        assert door in level.get_entities_in_range(point, blocks_only = True)

    def test_blocks_only_excludes_movers_hazards_and_actors(self, level, make_hazard,
                                                            make_enemy, make_objective,
                                                            make_block) -> None:
        make_block(col = 4, row = 4)
        hazard    = make_hazard(col = 4, row = 4)
        enemy     = make_enemy(col = 4, row = 4)
        objective = make_objective(col = 4, row = 4)
        point     = (4 * level.block_size, 4 * level.block_size)

        blocks_only = level.get_entities_in_range(point, blocks_only = True,
                                                  include_doors = False)
        assert hazard not in blocks_only
        assert enemy not in blocks_only
        assert objective not in blocks_only

    def test_hazards_can_be_opted_back_in_alongside_blocks(self, level, make_hazard) -> None:
        hazard = make_hazard(col = 4, row = 4)
        point  = (4 * level.block_size, 4 * level.block_size)
        assert hazard in level.get_entities_in_range(point, blocks_only = True,
                                                     include_hazards = True)

    def test_the_full_query_returns_triggers_hazards_enemies_and_objectives(
            self, level, controller, make_hazard, make_enemy, make_objective) -> None:
        trigger = Trigger(level, controller, 4 * level.block_size, 4 * level.block_size,
                          96, 96, None)
        level.triggers.append(trigger)
        hazard    = make_hazard(col = 4, row = 4)
        enemy     = make_enemy(col = 4, row = 4)
        objective = make_objective(col = 4, row = 4)

        found = level.get_entities_in_range((4 * level.block_size, 4 * level.block_size))
        for entity in (trigger, hazard, enemy, objective):
            assert entity in found

    def test_dynamic_entities_far_away_are_excluded(self, level, make_enemy) -> None:
        enemy = make_enemy(col = 9, row = 0)
        assert enemy not in level.get_entities_in_range((0, 0))


class TestStaticBlockSlice(object):
    def test_slices_one_and_a_half_screens_from_the_camera_offset(self, level,
                                                                  make_block) -> None:
        for col in range(len(level.static_blocks[0])):
            make_block(col = col, row = 0)
        window = pygame.Surface((level.block_size * 2, level.block_size * 2))

        rows = level.__get_static_block_slice__(window, 0, 0)
        assert len(rows[0]) == 3   # int(2 * 1.5) columns


# --------------------------------------------------------------------------- #
# purging
# --------------------------------------------------------------------------- #
class TestPurge:
    def test_a_trigger_is_removed_from_the_trigger_list(self, level, controller) -> None:
        trigger = Trigger(level, controller, 0, 0, 10, 10, None)
        level.triggers.append(trigger)
        level.queue_purge(trigger)
        level.purge()
        assert level.triggers == []

    def test_a_block_leaves_both_the_flat_list_and_the_static_grid(self, level,
                                                                   make_block) -> None:
        block = make_block(col = 2, row = 7)
        level.queue_purge(block)
        level.purge()
        assert block not in level.blocks
        assert block not in level.static_blocks[7]

    def test_a_moving_block_leaves_the_dynamic_list_too(self, level, controller,
                                                        image_master, block_audios) -> None:
        from Block import MovingBlock
        mover = MovingBlock(level, controller, 0, 0, 96, 96, image_master, block_audios,
                            False)
        level.blocks.append(mover)
        level.dynamic_blocks.append(mover)
        level.queue_purge(mover)
        level.purge()
        assert mover not in level.blocks
        assert mover not in level.dynamic_blocks

    def test_a_hazard_goes_to_the_hazard_bucket_not_the_block_bucket(self, level,
                                                                     make_hazard) -> None:
        # Hazard subclasses Block, and the isinstance chain checks Hazard first.
        hazard = make_hazard()
        level.queue_purge(hazard)
        assert hazard in level.purge_queue["hazards"]
        assert hazard not in level.purge_queue["blocks"]
        level.purge()
        assert hazard not in level.hazards

    def test_a_falling_hazard_is_also_pulled_from_the_column_index(
            self, level, controller, image_master, sprite_master, block_audios) -> None:
        hazard = FallingHazard(level, controller, 0, 0, 96, 96, image_master,
                               sprite_master, block_audios, 1.0, sprite = "TestAnim")
        level.hazards.append(hazard)
        level.falling_hazards[0] = [hazard]

        level.queue_purge(hazard)
        level.purge()
        assert 0 not in level.falling_hazards

    def test_one_of_several_falling_hazards_leaves_the_column_intact(
            self, level, controller, image_master, sprite_master, block_audios) -> None:
        first  = FallingHazard(level, controller, 0, 0, 96, 96, image_master,
                               sprite_master, block_audios, 1.0, sprite = "TestAnim")
        second = FallingHazard(level, controller, 0, 96, 96, 96, image_master,
                               sprite_master, block_audios, 1.0, sprite = "TestAnim")
        level.hazards += [first, second]
        level.falling_hazards[0] = [first, second]

        level.queue_purge(first)
        level.purge()
        assert level.falling_hazards[0] == [second]

    def test_an_enemy_and_an_objective_go_to_their_own_buckets(self, level, make_enemy,
                                                               make_objective) -> None:
        enemy     = make_enemy()
        objective = make_objective()
        level.queue_purge(enemy)
        level.queue_purge(objective)
        level.purge()
        assert enemy not in level.enemies
        assert objective not in level.objectives

    def test_purging_twice_is_harmless(self, level, make_enemy) -> None:
        enemy = make_enemy()
        level.queue_purge(enemy)
        level.purge()
        level.purge()
        assert level.enemies == []

    def test_the_queue_is_emptied_after_a_purge(self, level, make_enemy) -> None:
        level.queue_purge(make_enemy())
        level.purge()
        assert all(not bucket for bucket in level.purge_queue.values())

    def test_queueing_the_same_entity_twice_is_deduplicated(self, level,
                                                            make_enemy) -> None:
        enemy = make_enemy()
        level.queue_purge(enemy)
        level.queue_purge(enemy)
        assert len(level.purge_queue["enemies"]) == 1


# --------------------------------------------------------------------------- #
# achievements
# --------------------------------------------------------------------------- #
class TestAwardAchievements:
    @pytest.fixture
    def steam(self):
        return stubs.STEAMWORKS()

    @pytest.fixture
    def scored(self, level, player, make_enemy):
        """A level set up so that *no* achievement condition is met."""
        make_enemy()
        level.achievements = {
            "target_time":    "ACH_FAST",
            "all_objectives": "ACH_COLLECTOR",
            "no_kills":       "ACH_PACIFIST",
            "all_kills":      "ACH_CLEANER",
            "no_death":       "ACH_SURVIVOR",
            "no_hit":         "ACH_UNTOUCHED",
            "no_seen":        "ACH_SHADOW",
        }
        level.target_time           = 60
        level.time                  = 120
        level.objectives_available  = 2
        level.enemies_available     = 2
        player.kills_this_level     = 1
        player.deaths_this_level    = 1
        player.been_hit_this_level  = True
        player.been_seen_this_level = True
        return level

    def test_nothing_is_unlocked_when_nothing_is_earned(self, scored, steam) -> None:
        assert scored.award_achievements(steam) is False
        assert steam.UserStats.achievements == {}

    def test_beating_the_target_time_unlocks_it(self, scored, steam) -> None:
        scored.time = 30
        assert scored.award_achievements(steam) is True
        assert steam.UserStats.GetAchievement("ACH_FAST")

    def test_matching_the_target_time_exactly_counts(self, scored, steam) -> None:
        scored.time = scored.target_time
        scored.award_achievements(steam)
        assert steam.UserStats.GetAchievement("ACH_FAST")

    def test_a_zero_target_time_disables_the_award(self, scored, steam) -> None:
        scored.target_time = 0
        scored.time        = 0
        scored.award_achievements(steam)
        assert not steam.UserStats.GetAchievement("ACH_FAST")

    def test_collecting_every_objective_unlocks_the_collector(self, scored, steam,
                                                              make_objective) -> None:
        scored.objectives_collected = [make_objective(), make_objective(col = 6)]
        scored.objectives_available = 2
        scored.award_achievements(steam)
        assert steam.UserStats.GetAchievement("ACH_COLLECTOR")

    def test_a_level_with_no_objectives_cannot_unlock_the_collector(self, scored,
                                                                    steam) -> None:
        scored.objectives_available = 0
        scored.objectives_collected = []
        scored.award_achievements(steam)
        assert not steam.UserStats.GetAchievement("ACH_COLLECTOR")

    def test_killing_nobody_unlocks_the_pacifist(self, scored, steam) -> None:
        scored.player.kills_this_level = 0
        scored.award_achievements(steam)
        assert steam.UserStats.GetAchievement("ACH_PACIFIST")

    def test_killing_everybody_unlocks_the_cleaner(self, scored, steam) -> None:
        scored.player.kills_this_level = scored.enemies_available
        scored.award_achievements(steam)
        assert steam.UserStats.GetAchievement("ACH_CLEANER")

    def test_pacifist_and_cleaner_are_mutually_exclusive(self, scored, steam) -> None:
        scored.player.kills_this_level = 0
        scored.enemies_available       = 0
        scored.award_achievements(steam)
        # kills == 0 wins the if/elif, so an enemy-free level is pacifist, not cleaner.
        assert steam.UserStats.GetAchievement("ACH_PACIFIST")
        assert not steam.UserStats.GetAchievement("ACH_CLEANER")

    def test_surviving_untouched_and_unseen_each_unlock(self, scored, steam) -> None:
        scored.player.deaths_this_level    = 0
        scored.player.been_hit_this_level  = False
        scored.player.been_seen_this_level = False
        scored.award_achievements(steam)
        for name in ("ACH_SURVIVOR", "ACH_UNTOUCHED", "ACH_SHADOW"):
            assert steam.UserStats.GetAchievement(name)

    def test_an_already_unlocked_achievement_is_not_set_again(self, scored, steam) -> None:
        scored.time = 30
        steam.UserStats.achievements["ACH_FAST"] = True
        calls: list[str] = []
        steam.UserStats.SetAchievement = lambda name: calls.append(name)  # type: ignore[method-assign]
        scored.award_achievements(steam)
        assert "ACH_FAST" not in calls

    def test_no_steam_connection_reports_no_awards(self, scored) -> None:
        scored.time = 30
        assert scored.award_achievements(None) is False

    def test_a_level_without_achievement_names_awards_nothing(self, scored, steam) -> None:
        scored.achievements = {}
        scored.time         = 30
        assert scored.award_achievements(steam) is False


# --------------------------------------------------------------------------- #
# recap text
# --------------------------------------------------------------------------- #
class TestRecapText:
    def test_reports_time_and_objective_percentage(self, level, player,
                                                   make_objective) -> None:
        level.time                  = 65.5
        level.objectives_collected  = [make_objective()]
        level.objectives_available  = 4
        text = level.get_recap_text()
        assert "Mission time: 01:05.5." in text[0]
        assert "1 of 4 (25%)" in text[1]

    def test_no_objectives_available_reads_as_zero_percent(self, level, player) -> None:
        level.objectives_available = 0
        assert "(0%)" in level.get_recap_text()[1]

    def test_a_clean_run_lists_every_commendation(self, level, player) -> None:
        player.kills_this_level     = 0
        player.deaths_this_level    = 0
        player.been_hit_this_level  = False
        player.been_seen_this_level = False
        text = " ".join(level.get_recap_text())
        for phrase in ("Nonlethal:", "Survivor:", "Untouchable:", "Shadow:"):
            assert phrase in text

    def test_a_messy_run_reports_counts_instead(self, level, player) -> None:
        player.kills_this_level     = 2
        player.deaths_this_level    = 3
        player.been_hit_this_level  = True
        player.been_seen_this_level = True
        level.enemies_available     = 4
        text = " ".join(level.get_recap_text())
        assert "Enemies dispatched: 2 of 4 (50 %)." in text
        assert "Deaths: 3." in text
        assert "Untouchable:" not in text
        assert "Shadow:" not in text

    def test_kills_with_no_enemies_available_reads_as_zero_percent(self, level,
                                                                   player) -> None:
        player.kills_this_level = 1
        level.enemies_available = 0
        assert "(0 %)" in " ".join(level.get_recap_text())


# --------------------------------------------------------------------------- #
# particle effects
# --------------------------------------------------------------------------- #
class TestGenParticleEffect:
    def test_rain_and_snow_by_name(self, level, window) -> None:
        assert isinstance(level.gen_particle_effect("RAIN", window), Rain)
        assert isinstance(level.gen_particle_effect("SNOW", window), Snow)

    @pytest.mark.parametrize("name", ["FILM", "FILM GRAIN", "GRAIN", "OLD FILM"])
    def test_film_grain_matches_on_substring(self, level, window, name) -> None:
        assert isinstance(level.gen_particle_effect(name, window), FilmGrain)

    def test_an_unknown_name_yields_nothing(self, level, window) -> None:
        assert level.gen_particle_effect("FOG", window) is None

    def test_none_yields_nothing(self, level, window) -> None:
        assert level.gen_particle_effect(None, window) is None


# --------------------------------------------------------------------------- #
# drawing
# --------------------------------------------------------------------------- #
class TestDraw:
    def test_draws_the_effects_layer_first(self, level, player, surface) -> None:
        level.draw(surface, 0, 0, level.controller.master_volume)
        assert level.visual_effects_manager.draw_calls == 1

    def test_non_blocking_entities_are_drawn_after_the_player(self, level, player,
                                                              surface, make_block) -> None:
        """Foreground decoration must not be painted under the agent."""
        order: list[str] = []
        overlay = make_block(col = 1, row = 1, is_blocking = False, place = False)
        level.dynamic_blocks.append(overlay)

        overlay.draw = lambda *a, **k: order.append("overlay")   # type: ignore[method-assign]
        player.draw  = lambda *a, **k: order.append("player")    # type: ignore[method-assign]

        level.draw(surface, 0, 0, level.controller.master_volume)
        assert order == ["player", "overlay"]

    def test_particle_effects_are_drawn_last(self, level, player, surface, window) -> None:
        effect = level.gen_particle_effect("RAIN", window)
        level.particle_effects.append(effect)
        order: list[str] = []
        effect.draw = lambda *a, **k: order.append("effect")     # type: ignore[method-assign]
        player.draw = lambda *a, **k: order.append("player")     # type: ignore[method-assign]
        level.draw(surface, 0, 0, level.controller.master_volume)
        assert order == ["player", "effect"]


# --------------------------------------------------------------------------- #
# debug image dumps
# --------------------------------------------------------------------------- #
class TestDebugImageDumps:
    def test_gen_image_writes_a_png_named_after_the_level(self, level, player,
                                                          assets_root: Path) -> None:
        level.gen_image()
        assert (assets_root / "Misc" / f"{level.name}.png").is_file()

    def test_gen_background_writes_a_schematic(self, level, player, make_block,
                                               make_door, assets_root: Path) -> None:
        make_block(col = 0, row = 7)
        make_door(col = 3, row = 6)
        level.gen_background()
        assert (assets_root / "Misc" / f"{level.name}_bg.png").is_file()


def test_block_size_default_is_the_class_constant(level) -> None:
    assert Level.BLOCK_SIZE == 96
    assert level.block_size == Level.BLOCK_SIZE
