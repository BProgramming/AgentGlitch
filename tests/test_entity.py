"""Tests for ``Entity`` -- the base class every other game object inherits from.

Most of these behaviours are overridden further down the hierarchy, but the base
implementations are what ``Trigger``, plain ``Block`` and the teleport ray-cast in
``Player.teleport`` actually run, so they are worth pinning on their own.
"""

from __future__ import annotations

import pygame
import pytest

from Entity import Entity
from Helpers import MovementDirection
from Trigger import Trigger


@pytest.fixture
def entity(level, controller) -> Entity:
    return Entity(level, controller, 100, 200, 32, 48)


class TestConstruction:
    def test_name_embeds_the_spawn_coordinates(self, level, controller) -> None:
        # The save file is keyed on this name, so the format is load-bearing.
        assert Entity(level, controller, 3, 4, 8, 8, name = "Crate").name == "Crate (3, 4)"

    def test_rect_matches_the_requested_geometry(self, entity: Entity) -> None:
        assert entity.rect.topleft == (100, 200)
        assert entity.rect.size == (32, 48)
        assert (entity.width, entity.height) == (32, 48)

    def test_mask_is_derived_from_the_sprite(self, entity: Entity) -> None:
        assert entity.mask is not None
        assert entity.mask.get_size() == (32, 48)

    def test_defaults(self, entity: Entity) -> None:
        assert entity.is_blocking is True
        assert entity.is_stacked is False
        assert entity.attack_damage is None
        assert entity.hp == entity.max_hp == 100
        assert entity.direction is None
        assert entity.trigger == []
        assert entity.abilities == {}
        assert entity.cooldowns == {}
        assert entity.purgeable_on_load is False

    def test_is_a_pygame_sprite(self, entity: Entity) -> None:
        # collide_mask/collide_rect are used all over the codebase, and they require it.
        assert isinstance(entity, pygame.sprite.Sprite)

    def test_non_blocking_entities_can_be_requested(self, level, controller) -> None:
        assert Entity(level, controller, 0, 0, 4, 4, is_blocking = False).collide(None) is False


class TestGravity:
    def test_base_gravity_is_the_class_constant(self, entity: Entity) -> None:
        assert entity.gravity == Entity.GRAVITY


class TestDamageAndDeath:
    def test_die_zeroes_hp_and_returns_no_time_offset(self, entity: Entity) -> None:
        assert entity.die() == 0.0
        assert entity.hp == 0

    def test_get_hit_is_inert_on_the_base_class(self, entity: Entity) -> None:
        assert entity.get_hit(entity) == 0.0
        assert entity.hp == 100

    def test_set_difficulty_is_inert_on_the_base_class(self, entity: Entity) -> None:
        entity.set_difficulty(2.0)
        assert entity.hp == 100


class TestSaveLoad:
    def test_save_round_trips_hp(self, entity: Entity) -> None:
        entity.hp = 55
        payload = entity.save()
        assert payload == {entity.name: {"hp": 55}}

        restored = Entity(entity.level, entity.controller, 100, 200, 32, 48)
        restored.load(payload[entity.name])
        assert restored.hp == 55

    def test_load_attribute_restores_falsy_values(self, entity: Entity) -> None:
        """A saved hp of 0 -- a dead entity -- has to survive the round trip.

        The check is presence, not truthiness, so 0, 0.0 and False all restore.
        """
        entity.hp = 100
        entity.load({"hp": 0})
        assert entity.hp == 0

    def test_load_attribute_restores_a_false_flag(self, entity: Entity) -> None:
        entity.is_blocking = True
        entity.load_attribute({"is_blocking": False}, "is_blocking")
        assert entity.is_blocking is False

    def test_load_attribute_skips_a_missing_key(self, entity: Entity) -> None:
        entity.load_attribute({}, "hp")
        assert entity.hp == 100

    def test_load_attribute_skips_an_explicit_none(self, entity: Entity) -> None:
        entity.load_attribute({"hp": None}, "hp")
        assert entity.hp == 100

    def test_load_ignores_keys_it_does_not_know(self, entity: Entity) -> None:
        entity.load({"hp": 10, "unknown": 99})
        assert entity.hp == 10
        assert not hasattr(entity, "unknown")


class TestCooldowns:
    def test_positive_cooldowns_decay_by_the_frame_time(self, entity: Entity) -> None:
        entity.cooldowns = {"a": 1.0}
        entity.update_cooldowns(0.25)
        assert entity.cooldowns["a"] == pytest.approx(0.75)

    def test_a_cooldown_can_overshoot_below_zero_for_one_frame(self, entity: Entity) -> None:
        """Characterisation: the clamp happens on the *next* tick, not this one.

        Every gate in the game reads ``cooldown <= 0``, so the transient negative is
        harmless -- but anything that ever displays a cooldown must not assume >= 0.
        """
        entity.cooldowns = {"a": 0.1}
        entity.update_cooldowns(1.0)
        assert entity.cooldowns["a"] == pytest.approx(-0.9)
        entity.update_cooldowns(1.0)
        assert entity.cooldowns["a"] == 0.0

    def test_zero_cooldowns_are_left_alone(self, entity: Entity) -> None:
        entity.cooldowns = {"a": 0.0}
        entity.update_cooldowns(1.0)
        assert entity.cooldowns["a"] == 0.0


class TestLoop:
    def test_loop_ticks_cooldowns(self, entity: Entity) -> None:
        entity.cooldowns = {"a": 1.0}
        entity.loop(0.5)
        assert entity.cooldowns["a"] == pytest.approx(0.5)

    def test_a_dead_entity_asks_to_be_purged(self, level, controller) -> None:
        trigger = Trigger(level, controller, 0, 0, 10, 10, None, name = "Alarm")
        level.triggers.append(trigger)
        trigger.hp = 0
        trigger.loop(0.016)
        assert trigger in level.purge_queue["triggers"]

    def test_a_bare_entity_matches_no_purge_bucket(self, entity: Entity, level) -> None:
        """Characterisation: ``Level.queue_purge`` files by ``isinstance``.

        Anything that is not a Trigger, Hazard, Block, NonPlayer or Objective is
        silently dropped on the floor.  In practice nothing bare ever lives in a
        level list -- ``Player.teleport`` builds throwaway ``Entity`` instances for
        ray-casting, and projectiles are owned by their firing actor -- but a new
        entity family added outside that isinstance chain would never be collected.
        """
        entity.hp = 0
        entity.loop(0.016)
        assert all(not bucket for bucket in level.purge_queue.values())

    def test_a_death_cooldown_defers_the_purge(self, entity: Entity, level) -> None:
        entity.cooldowns = {"dead": 1.5}
        entity.hp = 0
        entity.loop(0.016)
        assert all(not bucket for bucket in level.purge_queue.values())

    def test_a_living_entity_is_never_purged(self, entity: Entity, level) -> None:
        entity.loop(0.016)
        assert all(not bucket for bucket in level.purge_queue.values())

    def test_loop_returns_no_time_offset(self, entity: Entity) -> None:
        assert entity.loop(0.016) == 0.0


class TestDraw:
    def test_draws_when_on_screen(self, entity: Entity, surface: pygame.Surface) -> None:
        entity.sprite.fill((255, 0, 0, 255))
        entity.rect.topleft = (10, 10)
        entity.draw(surface, 0, 0, {})
        assert surface.get_at((12, 12)) == pygame.Color(255, 0, 0, 255)

    def test_the_camera_offset_shifts_the_blit(self, entity: Entity,
                                               surface: pygame.Surface) -> None:
        entity.sprite.fill((0, 255, 0, 255))
        entity.rect.topleft = (110, 110)
        entity.draw(surface, 100, 100, {})
        assert surface.get_at((12, 12)) == pygame.Color(0, 255, 0, 255)

    @pytest.mark.parametrize("topleft", [(-500, 10), (10, -500), (5000, 10), (10, 5000)])
    def test_off_screen_entities_are_culled(self, entity: Entity, surface: pygame.Surface,
                                            topleft) -> None:
        entity.sprite.fill((255, 0, 255, 255))
        entity.rect.topleft = topleft
        entity.draw(surface, 0, 0, {})
        assert surface.get_at((0, 0)) == pygame.Color(0, 0, 0, 0)

    def test_a_spriteless_entity_draws_nothing(self, entity: Entity,
                                               surface: pygame.Surface) -> None:
        entity.sprite = None
        entity.draw(surface, 0, 0, {})
        assert surface.get_at((0, 0)) == pygame.Color(0, 0, 0, 0)


class TestLinkTriggers:
    def test_a_string_reference_is_resolved_into_trigger_objects(
            self, entity: Entity, level, controller) -> None:
        alarm = Trigger(level, controller, 0, 0, 10, 10, None, name = "Alarm")
        gate  = Trigger(level, controller, 0, 0, 10, 10, None, name = "Gate")
        entity.trigger = "Alarm Gate"
        entity.link_triggers([alarm, gate])
        assert entity.trigger == [alarm, gate]

    def test_an_already_resolved_list_is_left_alone(self, entity: Entity, level,
                                                    controller) -> None:
        alarm = Trigger(level, controller, 0, 0, 10, 10, None, name = "Alarm")
        entity.trigger = [alarm]
        entity.link_triggers([])
        assert entity.trigger == [alarm]

    def test_no_reference_is_a_no_op(self, entity: Entity) -> None:
        entity.link_triggers([])
        assert entity.trigger == []


def test_direction_defaults_to_none_so_generic_checks_can_short_circuit(
        entity: Entity) -> None:
    # Block/Actor comparisons like `ent.direction == MovementDirection.RIGHT` rely on
    # this being present-but-None on entities that do not move.
    assert entity.direction is None
    assert entity.direction != MovementDirection.RIGHT
