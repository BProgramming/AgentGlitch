"""End-to-end tests: build a real ``Level`` from generated .agl/.agd data and run it.

Everything else in the suite works on injected state.  These build the genuine article
-- ``Level.__init__`` parses the grid, ``EntityFactory`` constructs every entity, and
the resulting world is then stepped, saved, reloaded and drawn.  If an entity class
and the factory disagree about a constructor argument, this is where it shows up.
"""

from __future__ import annotations

import pygame
import pytest

import SaveLoad
from Block import Block, Hazard
from Camera import Camera
from HUD import HUD
from Level import Level
from NonPlayer import NonPlayer
from Objective import Objective
from Player import Player
from Trigger import Trigger
from support.assets import LEVEL_NAME, META_DICT
from support.doubles import RecordingVFXManager, StubController

pytestmark = pytest.mark.integration


@pytest.fixture
def game_world(window, sprite_master, image_master, player_audios, enemy_audios,
               block_audios, message_audios):
    """A real Level, wired to a controller, HUD and camera, ready to be stepped."""
    from Helpers import load_levels, load_object_dicts

    controller = StubController(win = window)
    vfx        = RecordingVFXManager()
    loading    = pygame.Surface((64, 64), pygame.SRCALPHA)

    level = Level(
        LEVEL_NAME,
        load_levels("Levels"),
        META_DICT,
        load_object_dicts("ReferenceDicts/GameObjects"),
        sprite_master,
        image_master,
        player_audios,
        enemy_audios,
        block_audios,
        message_audios,
        vfx,
        window,
        controller,
        loading,
    )
    controller.level = level

    hud    = HUD(level.player, window)
    camera = Camera(window)
    camera.prepare(level, hud)
    controller.hud = hud

    return {"level": level, "controller": controller, "hud": hud,
            "camera": camera, "vfx": vfx}


@pytest.fixture
def level(game_world) -> Level:
    return game_world["level"]


class TestLevelBuild:
    def test_the_display_name_comes_from_the_metadata(self, level: Level) -> None:
        assert level.name == LEVEL_NAME
        assert level.display_name == "Test Level"

    def test_the_block_size_is_read_from_the_metadata(self, level: Level) -> None:
        assert level.block_size == 96

    def test_the_bounds_match_the_grid(self, level: Level) -> None:
        assert level.level_bounds == ((0, 0), (8 * 96, 6 * 96))

    def test_every_entity_family_is_populated(self, level: Level) -> None:
        assert isinstance(level.player, Player)
        assert any(isinstance(e, NonPlayer) for e in level.enemies)
        assert any(isinstance(o, Objective) for o in level.objectives)
        assert any(isinstance(h, Hazard) for h in level.hazards)
        assert any(isinstance(b, Block) for b in level.blocks)
        assert all(isinstance(t, Trigger) for t in level.triggers)

    def test_the_census_counters_match_the_lists(self, level: Level) -> None:
        assert level.objectives_available == len(level.objectives)
        assert level.enemies_available == len(level.enemies)

    def test_the_music_playlist_is_resolved_from_the_metadata(self,
                                                              level: Level) -> None:
        assert [p.name for p in level.music] == ["track_one.mp3", "track_two.mp3"]

    def test_the_achievement_table_is_carried_over(self, level: Level) -> None:
        assert level.achievements["no_seen"] == "ACH_SHADOW"

    def test_the_target_time_and_default_objective_are_carried_over(self,
                                                                    level: Level) -> None:
        assert level.target_time == 120
        assert level.default_objective == "Find the exit"

    def test_the_level_starts_in_colour(self, level: Level) -> None:
        assert level.retro is False

    def test_a_retro_level_builds_in_retro(self, window, sprite_master, image_master,
                                           player_audios, enemy_audios, block_audios,
                                           message_audios) -> None:
        from Helpers import load_levels, load_object_dicts

        controller = StubController(win = window)
        level = Level("RETROLEVEL", load_levels("Levels"), META_DICT,
                      load_object_dicts("ReferenceDicts/GameObjects"), sprite_master,
                      image_master, player_audios, enemy_audios, block_audios,
                      message_audios, RecordingVFXManager(), window, controller,
                      pygame.Surface((16, 16), pygame.SRCALPHA))
        assert level.retro is True
        assert level.player.is_retro is True

    def test_entities_with_trigger_references_are_linked_to_objects(self,
                                                                    level: Level) -> None:
        for entity in level.entities:
            if isinstance(entity.trigger, list):
                assert all(isinstance(t, Trigger) for t in entity.trigger)


@pytest.mark.slow
class TestRunningFrames:
    def _step(self, world, frames: int = 30, dtime: float = 1 / 150) -> None:
        level = world["level"]
        for _ in range(frames):
            level.time += dtime
            for entity in level.entities:
                if hasattr(entity, "patrol"):
                    entity.patrol(dtime)
                entity.loop(dtime)
                if isinstance(entity, NonPlayer) and entity.queued_message is not None:
                    entity.play_queued_message()
            for block in level.dynamic_blocks:
                if hasattr(block, "patrol"):
                    block.patrol(dtime)
            level.purge()
            world["camera"].scroll_to_player(dtime)

    def test_a_short_run_does_not_raise(self, game_world) -> None:
        self._step(game_world)

    def test_the_clock_advances(self, game_world) -> None:
        self._step(game_world)
        assert game_world["level"].time > 0
        assert game_world["level"].formatted_time != "00:00.0"

    def test_the_player_falls_onto_the_floor_and_stays_in_bounds(self,
                                                                 game_world) -> None:
        level = game_world["level"]
        self._step(game_world, frames = 120, dtime = 1 / 60)
        assert level.player.rect.bottom <= level.level_bounds[1][1] + 200

    def test_the_camera_follows_the_player(self, game_world) -> None:
        self._step(game_world)
        camera = game_world["camera"]
        assert camera.focus_x == game_world["level"].player.rect.centerx

    def test_a_full_frame_can_be_drawn(self, game_world) -> None:
        self._step(game_world, frames = 5)
        game_world["camera"].draw(game_world["controller"].master_volume)

    def test_walking_right_moves_the_player(self, game_world) -> None:
        level = game_world["level"]
        start = level.player.rect.x
        for _ in range(30):
            level.player.move_right()
            level.player.loop(1 / 60)
        assert level.player.rect.x > start

    def test_killing_every_enemy_fills_the_kill_counter(self, game_world) -> None:
        level = game_world["level"]
        for enemy in list(level.enemies):
            enemy.die()
        assert level.player.kills_this_level == level.enemies_available


class TestSaveRoundTrip:
    def test_a_built_level_saves_and_reloads(self, game_world, game_data_dir) -> None:
        level      = game_world["level"]
        controller = game_world["controller"]

        objective = level.objectives[0]
        objective.hp = 0
        level.time = 42.5

        SaveLoad.save(level, game_world["hud"], controller)
        assert (game_data_dir / "save.p").is_file()

        level.time = 0
        assert SaveLoad.load_part2(SaveLoad.load_part1(), level, controller) is True
        assert level.time == 42.5

    def test_reloading_removes_entities_the_save_does_not_mention(self, game_world,
                                                                  game_data_dir) -> None:
        level      = game_world["level"]
        controller = game_world["controller"]
        assert level.enemies

        SaveLoad.save(level, None, controller)
        data = SaveLoad.load_part1()
        for enemy in level.enemies:
            data.pop(enemy.name, None)

        SaveLoad.load_part2(data, level, controller)
        assert level.enemies == []

    def test_the_hud_can_render_the_reloaded_level(self, game_world) -> None:
        SaveLoad.save(game_world["level"], game_world["hud"], game_world["controller"])
        game_world["hud"].draw(game_world["level"].formatted_time)


class TestDebugDumps:
    def test_the_whole_level_can_be_rendered_to_an_image(self, game_world,
                                                         assets_root) -> None:
        game_world["level"].gen_image()
        assert (assets_root / "Misc" / f"{LEVEL_NAME}.png").is_file()

    def test_a_schematic_background_can_be_rendered(self, game_world,
                                                    assets_root) -> None:
        game_world["level"].gen_background()
        assert (assets_root / "Misc" / f"{LEVEL_NAME}_bg.png").is_file()


def test_the_recap_reads_sensibly_for_a_fresh_level(game_world) -> None:
    text = game_world["level"].get_recap_text()
    assert text[0].startswith("Mission time:")
    assert "Nonlethal:" in " ".join(text)
    assert "Shadow:" in " ".join(text)
