"""Tests for ``Objective`` -- collection, grouping, the on-screen pointer and persistence."""

from __future__ import annotations

import pygame
import pytest

from Objective import Objective
from Trigger import SaveTrigger
from support import stubs


class TestConstruction:
    def test_the_pointer_sprites_are_loaded_once_on_the_class(self) -> None:
        assert isinstance(Objective.POINTER_SPRITE, pygame.Surface)
        assert isinstance(Objective.POINTER_SPRITE_RETRO, pygame.Surface)
        assert Objective.POINTER_SPRITE_WIDTH == Objective.POINTER_SPRITE.get_width()

    def test_an_animated_objective_takes_its_geometry_from_the_sprite(self,
                                                                      make_objective) -> None:
        objective = make_objective()
        assert objective.rect.size == objective.sprite.get_size()

    def test_a_spriteless_objective_keeps_its_tile_geometry(self, make_objective,
                                                            level) -> None:
        objective = make_objective(sprite = None)
        assert objective.sprite is None
        assert objective.rect.size == (level.block_size, level.block_size)

    def test_objectives_never_block_movement(self, make_objective) -> None:
        assert make_objective().collide(None) is False
        assert make_objective().is_blocking is False

    def test_a_retro_level_prefers_the_retro_animation_and_pointer(
            self, retro_level, controller, sprite_master, block_audios) -> None:
        objective = Objective(retro_level, controller, 0, 0, 96, 96, sprite_master,
                              block_audios, sprite = "TestAnim")
        assert objective.pointer is Objective.POINTER_SPRITE_RETRO

    def test_the_pointer_offset_centres_it_above_the_objective(self,
                                                               make_objective) -> None:
        objective = make_objective()
        expected = (objective.rect.width - Objective.POINTER_SPRITE_WIDTH) / 2
        assert objective.pointer_offset[0] == expected


class TestCollection:
    def test_an_active_objective_is_collected_on_contact(self, make_objective,
                                                         player, level) -> None:
        objective = make_objective()
        objective.get_hit(player)
        assert objective.is_active is False
        assert objective.hp == 0
        assert objective in level.objectives_collected

    def test_an_inactive_objective_ignores_contact(self, make_objective,
                                                   player) -> None:
        objective = make_objective(is_active = False)
        assert objective.get_hit(player) == 0.0
        assert objective.hp == objective.max_hp

    def test_collecting_the_last_of_a_group_clears_the_active_objective(
            self, make_objective, player, controller) -> None:
        objective = make_objective()
        objective.get_hit(player)
        assert controller.activate_objective_calls[-1] == (None, True, False)

    def test_collecting_one_of_a_group_leaves_the_objective_standing(
            self, make_objective, player, controller) -> None:
        # Objectives group by the first word of their name.
        first  = make_objective(col = 5, row = 6, name = "Packet")
        second = make_objective(col = 6, row = 6, name = "Packet")
        first.get_hit(player)
        assert controller.activate_objective_calls == []
        assert second.hp > 0

    def test_the_last_of_a_group_fires_the_linked_triggers(self, make_objective,
                                                           player, level,
                                                           controller) -> None:
        trigger   = SaveTrigger(level, controller, 0, 0, 10, 10, None)
        objective = make_objective()
        objective.trigger = [trigger]
        objective.get_hit(player)
        assert trigger.has_fired is True

    def test_collecting_awards_a_steam_achievement(self, make_objective, player,
                                                   controller) -> None:
        controller.steamworks = stubs.STEAMWORKS()
        objective = make_objective(achievement = "ACH_PACKET")
        objective.get_hit(player)
        assert controller.steamworks.UserStats.GetAchievement("ACH_PACKET")
        assert controller.should_store_steam_stats is True

    def test_an_already_earned_achievement_is_not_re_awarded(self, make_objective,
                                                             player, controller) -> None:
        controller.steamworks = stubs.STEAMWORKS()
        controller.steamworks.UserStats.achievements["ACH_PACKET"] = True
        make_objective(achievement = "ACH_PACKET").get_hit(player)
        assert controller.should_store_steam_stats is False

    def test_collection_reports_the_wall_clock_cost(self, make_objective,
                                                    player) -> None:
        assert make_objective().get_hit(player) >= 0.0

    def test_the_pickup_sound_is_played(self, make_objective, player,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
        played: list = []

        class _Channel:
            def play(self, sound): played.append(sound)
            def set_volume(self, *a): pass

        monkeypatch.setattr(pygame.mixer, "find_channel", lambda *a, **k: _Channel())
        make_objective(sound = "objective").get_hit(player)
        assert len(played) == 1


class TestPersistence:
    def test_save_records_health(self, make_objective) -> None:
        objective = make_objective()
        assert objective.save() == {objective.name: {"hp": 100}}

    def test_loading_a_live_objective_leaves_it_in_place(self, make_objective,
                                                         level) -> None:
        objective = make_objective()
        objective.load({"hp": 100})
        assert objective not in level.purge_queue["objectives"]

    def test_loading_a_collected_objective_removes_it_again(self, make_objective,
                                                            level, player) -> None:
        objective = make_objective()
        objective.load({"hp": 0})
        assert objective in level.purge_queue["objectives"]
        assert objective in level.objectives_collected

    def test_load_assigns_health_directly_so_zero_survives_the_round_trip(
            self, make_objective, player) -> None:
        # Objective overrides load rather than using load_attribute, which would drop
        # a saved hp of 0 as falsy -- see test_entity.py for that base-class quirk.
        objective = make_objective()
        objective.load({"hp": 0})
        assert objective.hp == 0


class TestAnimation:
    def test_the_frame_advances_with_the_counter(self, make_objective) -> None:
        objective = make_objective()
        objective.animation_count = 0
        assert objective.update_sprite() == 0
        objective.animation_count = Objective.ANIMATION_DELAY
        assert objective.update_sprite() == 1

    def test_the_animation_wraps(self, make_objective) -> None:
        objective = make_objective()
        objective.animation_count = Objective.ANIMATION_DELAY * len(objective.sprites)
        assert objective.update_sprite() == 0

    def test_a_spriteless_objective_reports_frame_zero(self, make_objective) -> None:
        assert make_objective(sprite = None).update_sprite() == 0

    def test_the_loop_advances_the_counter_with_real_frame_times(self,
                                                                 make_objective) -> None:
        objective = make_objective()
        objective.loop(1 / 150)
        assert objective.animation_count > 0

    def test_update_geo_resyncs_the_rect_and_mask(self, make_objective) -> None:
        objective = make_objective()
        objective.update_sprite()
        objective.update_geo()
        assert objective.rect.size == objective.sprite.get_size()
        assert objective.mask.get_size() == objective.sprite.get_size()


class TestDraw:
    def test_an_on_screen_objective_is_drawn(self, make_objective, surface,
                                             player) -> None:
        objective = make_objective()
        objective.rect.topleft = (100, 100)
        objective.draw(surface, 0, 0, {})
        assert surface.get_at((102, 102)).a > 0

    def test_an_off_screen_objective_is_culled(self, make_objective, surface,
                                               player) -> None:
        objective = make_objective()
        objective.rect.topleft = (-5000, -5000)
        objective.draw(surface, 0, 0, {})
        assert surface.get_at((0, 0)).a == 0

    def test_an_active_objective_draws_its_pointer(self, make_objective, surface,
                                                   player) -> None:
        objective = make_objective(is_active = True)
        objective.rect.topleft = (400, 400)
        objective.draw(surface, 0, 0, {})
        pointer_y = 400 + objective.pointer_offset[1][0]
        assert surface.get_at((int(400 + objective.pointer_offset[0]) + 2,
                               int(pointer_y) + 2)).a > 0

    def test_an_inactive_objective_draws_no_pointer(self, make_objective, surface,
                                                    player) -> None:
        objective = make_objective(is_active = False)
        objective.rect.topleft = (400, 400)
        objective.draw(surface, 0, 0, {})
        pointer_y = 400 + objective.pointer_offset[1][0]
        assert surface.get_at((int(400 + objective.pointer_offset[0]) + 2,
                               int(pointer_y) + 2)).a == 0

    def test_an_off_screen_active_objective_clamps_its_pointer_to_the_border(
            self, make_objective, surface, player) -> None:
        objective = make_objective(is_active = True)
        objective.rect.topleft = (5000, 5000)
        objective.draw(surface, 0, 0, {})
        # The clamped pointer lands in the bottom-right border band.
        band = pygame.Rect(surface.get_width() - 200, surface.get_height() - 200,
                           200, 200)
        assert any(surface.get_at((x, y)).a > 0
                   for x in range(band.left, band.right, 4)
                   for y in range(band.top, band.bottom, 4))
