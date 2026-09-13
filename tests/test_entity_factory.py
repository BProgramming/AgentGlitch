"""Tests for ``EntityFactory`` -- the token-to-entity construction layer."""

from __future__ import annotations

import pygame
import pytest

from Block import (
    Block,
    BreakableBlock,
    Door,
    FallingHazard,
    Hazard,
    MovableBlock,
    MovingBlock,
)
from Boss import Boss
from EntityFactory import build_entity, build_level, convert_coords
from Helpers import MovementDirection, load_levels, load_object_dicts
from NonPlayer import NonPlayer
from Objective import Objective
from Player import Player
from Trigger import (
    AchievementTrigger,
    CameraToPlayerTrigger,
    ChangeLevelTrigger,
    CinematicTrigger,
    DiscordStatusTrigger,
    ObjectiveTrigger,
    PropertyTrigger,
    RevertTrigger,
    SaveTrigger,
    SoundTrigger,
    SwapLevelTrigger,
    TextTrigger,
    Trigger,
)
from support.assets import LEVEL_NAME, OBJECT_DICT


BLOCK_SIZE = 96


# --------------------------------------------------------------------------- #
# convert_coords
# --------------------------------------------------------------------------- #
class TestConvertCoords:
    def test_small_values_are_treated_as_tile_indices(self) -> None:
        # Below half a block, a coordinate is a sheet index and gets scaled up.
        assert convert_coords(0, 96) == 0
        assert convert_coords(2, 96) == 96
        assert convert_coords(47, 96) == 47 * 48

    def test_values_at_or_above_the_half_block_are_already_pixels(self) -> None:
        assert convert_coords(48, 96) == 48
        assert convert_coords(480, 96) == 480

    def test_the_threshold_follows_the_block_size(self) -> None:
        assert convert_coords(20, 64) == 20 * 32
        assert convert_coords(40, 64) == 40


# --------------------------------------------------------------------------- #
# build_entity
# --------------------------------------------------------------------------- #
class TestBuildEntity:
    @pytest.fixture
    def build(self, level, controller, sprite_master, image_master, enemy_audios,
              block_audios, message_audios):
        def _build(token: str, i: int = 2, j: int = 3, **overrides):
            entry = OBJECT_DICT[token]
            data  = dict(entry["data"])
            data.update(overrides)
            return build_entity(entry["type"].upper(), data, token, level, controller,
                                i, j, BLOCK_SIZE, OBJECT_DICT, sprite_master,
                                image_master, enemy_audios, block_audios,
                                message_audios)
        return _build

    @pytest.mark.parametrize("token, expected", [
        ("B", Block),
        ("X", BreakableBlock),
        ("M", MovingBlock),
        ("V", MovableBlock),
        ("D", Door),
        ("H", Hazard),
        ("F", FallingHazard),
        ("E", NonPlayer),
        ("O", Objective),
        ("S", SaveTrigger),
        ("C", ChangeLevelTrigger),
    ])
    def test_each_token_builds_its_class(self, build, token, expected) -> None:
        assert isinstance(build(token), expected)

    def test_an_unknown_type_builds_nothing(self, build) -> None:
        assert build("?") is None

    def test_entities_land_on_their_tile(self, build) -> None:
        block = build("B", i = 2, j = 3)
        assert block.rect.topleft == (3 * BLOCK_SIZE, 2 * BLOCK_SIZE)

    def test_a_named_entity_keeps_its_name(self, build) -> None:
        assert build("B").name.startswith("Ground")

    def test_an_unnamed_entity_falls_back_to_its_token(self, build, level,
                                                       controller, sprite_master,
                                                       image_master, enemy_audios,
                                                       block_audios,
                                                       message_audios) -> None:
        built = build_entity("BLOCK", {"coord_x": 0, "coord_y": 0}, "B", level,
                             controller, 0, 0, BLOCK_SIZE, OBJECT_DICT, sprite_master,
                             image_master, enemy_audios, block_audios, message_audios)
        assert built.name.startswith("B (")

    def test_triggers_are_anchored_by_their_bottom_edge(self, build, level,
                                                        controller, sprite_master,
                                                        image_master, enemy_audios,
                                                        block_audios,
                                                        message_audios) -> None:
        # A trigger's i is the row of its *bottom* tile, so a taller trigger starts
        # further up the map.
        data = {"width": 2, "height": 3, "input": None}
        built = build_entity("TRIGGER", data, "T", level, controller, 5, 1, BLOCK_SIZE,
                             OBJECT_DICT, sprite_master, image_master, enemy_audios,
                             block_audios, message_audios)
        assert built.rect.topleft == (1 * BLOCK_SIZE, (5 - 2) * BLOCK_SIZE)
        assert built.rect.size == (2 * BLOCK_SIZE, 3 * BLOCK_SIZE)

    def test_a_patrol_path_is_resolved_relative_to_the_spawn_tile(self, build) -> None:
        mover = build("M", i = 2, j = 3)
        assert mover.patrol_path is not None
        assert mover.patrol_path[0].x == 3 * BLOCK_SIZE

    def test_a_null_path_leaves_the_entity_stationary(self, build) -> None:
        assert build("E").patrol_path is None

    def test_hazard_hit_sides_are_normalised(self, build) -> None:
        assert build("H").hit_sides == "UDLR"

    def test_falling_hazard_drop_distances_are_scaled_to_pixels(self, build) -> None:
        crusher = build("F")
        assert crusher.drop_x == 1 * BLOCK_SIZE
        assert crusher.drop_y == 3 * BLOCK_SIZE

    def test_a_boss_is_built_with_its_own_defaults(self, level, controller,
                                                   sprite_master, image_master,
                                                   enemy_audios, block_audios,
                                                   message_audios) -> None:
        data = {"path": None, "hp": 500, "sprite": "TestAgent", "name": "Warden"}
        boss = build_entity("BOSS", data, "W", level, controller, 1, 1, BLOCK_SIZE,
                            OBJECT_DICT, sprite_master, image_master, enemy_audios,
                            block_audios, message_audios)
        assert isinstance(boss, Boss)
        assert boss.show_health_bar is True

    @pytest.mark.parametrize("entity_type, expected, data", [
        ("ACHIEVEMENTTRIGGER",   AchievementTrigger,    {"width": 1, "height": 1, "input": "ACH"}),
        ("CAMERATOPLAYERTRIGGER", CameraToPlayerTrigger, {"width": 1, "height": 1, "input": None}),
        ("CINEMATICTRIGGER",     CinematicTrigger,      {"width": 1, "height": 1, "input": "intro"}),
        ("PROPERTYTRIGGER",      PropertyTrigger,       {"width": 1, "height": 1, "input": None}),
        ("REVERTTRIGGER",        RevertTrigger,         {"width": 1, "height": 1, "input": None}),
        ("SWAPLEVELTRIGGER",     SwapLevelTrigger,      {"width": 1, "height": 1, "input": None}),
        ("SOUNDTRIGGER",         SoundTrigger,          {"width": 1, "height": 1, "input": "beep.wav"}),
        ("OBJECTIVETRIGGER",     ObjectiveTrigger,      {"width": 1, "height": 1,
                                                         "input": {"target": "Packet", "value": True}}),
        ("DISCORDSTATUSTRIGGER", DiscordStatusTrigger,  {"width": 1, "height": 1,
                                                         "input": {"state": "s", "details": "d"}}),
    ])
    def test_every_trigger_type_is_reachable(self, level, controller, sprite_master,
                                             image_master, enemy_audios, block_audios,
                                             message_audios, entity_type, expected,
                                             data) -> None:
        built = build_entity(entity_type, data, "T", level, controller, 1, 1,
                             BLOCK_SIZE, OBJECT_DICT, sprite_master, image_master,
                             enemy_audios, block_audios, message_audios)
        assert isinstance(built, expected)

    def test_a_text_trigger_reads_its_file(self, level, controller, sprite_master,
                                           image_master, enemy_audios, block_audios,
                                           message_audios) -> None:
        data = {"width": 1, "height": 1, "input": {"file": "message.txt"}}
        built = build_entity("TEXTTRIGGER", data, "T", level, controller, 1, 1,
                             BLOCK_SIZE, OBJECT_DICT, sprite_master, image_master,
                             enemy_audios, block_audios, message_audios)
        assert isinstance(built, TextTrigger)
        assert built.value["text"] == ["First line.", "Second line."]


# --------------------------------------------------------------------------- #
# build_level
# --------------------------------------------------------------------------- #
class TestBuildLevel:
    @pytest.fixture
    def built(self, level, controller, window, sprite_master, image_master,
              player_audios, enemy_audios, block_audios, message_audios):
        layout  = load_levels("Levels")[LEVEL_NAME]
        loading = pygame.Surface((64, 64), pygame.SRCALPHA)
        result  = build_level(level, layout, sprite_master, image_master,
                              load_object_dicts("ReferenceDicts/GameObjects")[LEVEL_NAME],
                              player_audios, enemy_audios, block_audios, message_audios,
                              window, controller, None, BLOCK_SIZE, loading)
        keys = ("level_bounds", "player", "triggers", "blocks", "dynamic_blocks",
                "doors", "static_blocks", "hazards", "falling_hazards", "enemies",
                "objectives")
        return dict(zip(keys, result))

    def test_the_bounds_come_from_the_grid_dimensions(self, built) -> None:
        assert built["level_bounds"] == ((0, 0), (8 * BLOCK_SIZE, 6 * BLOCK_SIZE))

    def test_a_player_is_created_at_the_player_token(self, built) -> None:
        player = built["player"]
        assert isinstance(player, Player)
        # The P token sits at row 3, column 1 of the generated grid.
        assert player.rect.x == BLOCK_SIZE + (BLOCK_SIZE - player.rect.width) // 2

    def test_the_player_faces_right_by_default(self, built) -> None:
        assert built["player"].facing is MovementDirection.RIGHT

    def test_terrain_is_filed_into_the_static_grid(self, built) -> None:
        floor_row = built["static_blocks"][5]
        assert all(isinstance(cell, Block) for cell in floor_row)

    def test_empty_tiles_stay_empty(self, built) -> None:
        assert built["static_blocks"][0] == [None] * 8

    def test_movers_go_to_the_dynamic_list_as_well_as_the_block_list(self,
                                                                     built) -> None:
        movers = [b for b in built["dynamic_blocks"]
                  if isinstance(b, (MovingBlock, MovableBlock))]
        assert movers
        assert all(m in built["blocks"] for m in movers)

    def test_doors_are_indexed_by_column(self, built) -> None:
        assert built["doors"]
        for column, doors in built["doors"].items():
            for door in doors:
                assert door.rect.x == column * BLOCK_SIZE

    def test_hazards_are_collected(self, built) -> None:
        assert any(isinstance(h, Hazard) for h in built["hazards"])

    def test_falling_hazards_are_also_indexed_by_column(self, built) -> None:
        assert built["falling_hazards"]
        for column, hazards in built["falling_hazards"].items():
            for hazard in hazards:
                assert all(isinstance(h, FallingHazard) for h in hazards)

    def test_enemies_and_objectives_are_collected(self, built) -> None:
        assert any(isinstance(e, NonPlayer) for e in built["enemies"])
        assert any(isinstance(o, Objective) for o in built["objectives"])

    def test_triggers_are_collected(self, built) -> None:
        assert all(isinstance(t, Trigger) for t in built["triggers"])
        assert len(built["triggers"]) >= 2

    def test_a_block_under_a_solid_block_is_marked_stacked(self, built) -> None:
        # Row 5 of the generated grid sits directly under row 4, which holds a crate
        # rather than a plain Block, so only the columns under a "B" stack.
        assert isinstance(built["static_blocks"][5][0], Block)

    def test_the_loading_progress_text_is_shown_once_per_row_plus_links(
            self, built, display_texts) -> None:
        building = [c for c in display_texts if "Building level" in c.text]
        linking  = [c for c in display_texts if "Linking game objects" in c.text]
        assert len(building) == 6
        assert linking

    def test_progress_reaches_one_hundred_percent(self, built, display_texts) -> None:
        assert any(c.text.strip().endswith("100%") for c in display_texts)
