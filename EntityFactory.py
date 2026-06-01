from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
from Block import (
    Block,
    BreakableBlock,
    MovingBlock,
    MovableBlock,
    Door,
    Hazard,
    MovingHazard,
    FallingHazard,
)
from Boss import Boss
from Player import Player
from NonPlayer import NonPlayer
from Objective import Objective
from Trigger import (
    Trigger,
    TextTrigger,
    SoundTrigger,
    SpawnTrigger,
    RevertTrigger,
    SaveTrigger,
    ChangeLevelTrigger,
    PropertyTrigger,
    CinematicTrigger,
    AchievementTrigger,
    ObjectiveTrigger,
    SwapLevelTrigger,
    CameraToPointTrigger,
    CameraToPlayerTrigger,
    DiscordStatusTrigger,
)
from Entity import Entity
from Helpers import (
    load_path,
    display_text,
    MovementDirection,
    NORMAL_WHITE,
    RETRO_WHITE,
)

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


def convert_coords(
        coord:      int,
        block_size: int,
) -> int:
    """Scale small tile coordinates up to pixel coordinates."""
    actual_size = block_size // 2
    if coord < actual_size:
        return coord * actual_size
    else:
        return coord


def build_entity(
        entity_type:    str,
        data:           dict,
        element:        str,
        level:          Level,
        controller:     Controller,
        i:              int,
        j:              int,
        block_size:     int,
        objects_dict:   dict,
        sprite_master:  dict,
        image_master:   dict,
        enemy_audios:   dict,
        block_audios:   dict,
        message_audios: dict,
        is_stacked:     bool = False,
) -> Entity | None:
    """Construct and return a single entity from its (uppercased) type and data dict."""
    name = element if data.get("name") is None else data["name"]
    match entity_type:
        case "OBJECTIVE":
            return Objective(level, controller, j * block_size, i * block_size, block_size, block_size, sprite_master, block_audios, is_active=(False if data.get("is_active") is None else data["is_active"]), sprite=(None if data.get("sprite") is None else data["sprite"]), sound=("objective" if data.get("sound") is None else data["sound"].lower()), text=(None if data.get("text") is None else data["text"]), trigger=(None if data.get("trigger") is None else data["trigger"]), is_blocking=(False if data.get("is_blocking") is None else data["is_blocking"]), achievement=(None if data.get("achievement") is None else data["achievement"]), name=name)
        case "BLOCK":
            return Block(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), is_blocking=(True if data.get("is_blocking") is None else data["is_blocking"]), name=name)
        case "BREAKABLEBLOCK":
            return BreakableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), coord_x2=convert_coords(data["coord_x2"], block_size), coord_y2=convert_coords(data["coord_y2"], block_size), name=name)
        case "MOVINGBLOCK":
            path = None if data["path"] is None else load_path(data["path"], i, j, block_size)
            return MovingBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, is_enabled=(True if data.get("is_enabled") is None else data["is_enabled"]), hold_for_collision=(False if data.get("hold_for_collision") is None else data["hold_for_collision"]), speed=data["speed"], path=path, coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), is_blocking=(True if data.get("is_blocking") is None else data["is_blocking"]), name=name)
        case "DOOR":
            return Door(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=(False if data.get("is_locked") is None else data["is_locked"]), coord_x=(0 if data.get("coord_x") is None else convert_coords(data["coord_x"], block_size)), coord_y=(0 if data.get("coord_y") is None else convert_coords(data["coord_y"], block_size)), locked_coord_x=(None if data.get("locked_coord_x") is None else convert_coords(data["locked_coord_x"], block_size)), locked_coord_y=(None if data.get("locked_coord_y") is None else convert_coords(data["locked_coord_y"], block_size)), unlocked_coord_x=(None if data.get("unlocked_coord_x") is None else convert_coords(data["unlocked_coord_x"], block_size)), unlocked_coord_y=(None if data.get("unlocked_coord_y") is None else convert_coords(data["unlocked_coord_y"], block_size)), name=name)
        case "MOVABLEBLOCK":
            return MovableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), name=name)
        case "HAZARD":
            return Hazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), name=name)
        case "MOVINGHAZARD":
            path = None if data["path"] is None else load_path(data["path"], i, j, block_size)
            return MovingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), name=name)
        case "FALLINGHAZARD":
            return FallingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=convert_coords(data["coord_x"], block_size), coord_y=convert_coords(data["coord_y"], block_size), name=name)
        case "ENEMY":
            path = None if data["path"] is None else load_path(data["path"], i, j, block_size)
            return NonPlayer(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, path=path, kill_at_end=(False if data.get("kill_at_end") is None else data["kill_at_end"]), is_hostile=(True if data.get("is_hostile") is None else data["is_hostile"]), collision_message=(None if data.get("collision_message") is None else data["collision_message"]), bark=(None if data.get("bark") is None else data["bark"]), hp=data["hp"], can_shoot=(False if data.get("can_shoot") is None else data["can_shoot"]), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None else data["proj_sprite"]), name=name)
        case "BOSS":
            path = None if data["path"] is None else load_path(data["path"], i, j, block_size)
            return Boss(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, music=(None if data.get("music") is None else data["music"]), trigger=(None if data.get("trigger") is None else data["trigger"]), path=path, hp=data["hp"], show_health_bar=(True if data.get("show_health_bar") is None else data["show_health_bar"]), can_shoot=(False if data.get("can_shoot") is None else data["can_shoot"]), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None else data["proj_sprite"]), name=name)
        case "TRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return Trigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "TEXTTRIGGER":
            packed_input = {"ref": message_audios, "input": (None if data.get("input") is None else data["input"])}
            return TextTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "SOUNDTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return SoundTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "SPAWNTRIGGER":
            all_refs     = {"objects_dict": objects_dict, "sprite_master": sprite_master, "enemy_audios": enemy_audios, "block_audios": block_audios, "message_audios": message_audios, "image_master": image_master, "block_size": block_size}
            packed_input = {"ref": all_refs, "input": (None if data.get("input") is None else data["input"])}
            return SpawnTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "REVERTTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return RevertTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "SAVETRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return SaveTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "CHANGELEVELTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return ChangeLevelTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "PROPERTYTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return PropertyTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "CINEMATICTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return CinematicTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "ACHIEVEMENTTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return AchievementTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "OBJECTIVETRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return ObjectiveTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "SWAPLEVELTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return SwapLevelTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "CAMERATOPOINTTRIGGER":
            packed_input = {"ref": block_size, "input": (None if data.get("input") is None else data["input"])}
            return CameraToPointTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "CAMERATOPLAYERTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return CameraToPlayerTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case "DISCORDSTATUSTRIGGER":
            packed_input = (None if data.get("input") is None else data["input"])
            return DiscordStatusTrigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=name)
        case _:
            return None


def build_level(
        level:          Level,
        layout:         list,
        sprite_master:  dict,
        image_master:   dict,
        objects_dict:   dict,
        player_audios:  dict,
        enemy_audios:   dict,
        block_audios:   dict,
        message_audios: dict,
        win:            pygame.Surface,
        controller:     Controller,
        player_sprite:  str | None,
        block_size:     int,
        loading_screen: pygame.Surface,
) -> tuple:
    """Parse the layout grid into all level entities and return them as a tuple."""
    width            = len(layout[-1]) * block_size
    height           = len(layout) * block_size
    level_bounds     = ((0, 0), (width, height))
    player_start     = (0, 0)
    player_face_left = False

    blocks          = []
    doors           = {}
    dynamic_blocks  = []
    static_blocks   = []
    triggers        = []
    enemies         = []
    hazards         = []
    falling_hazards = {}
    objectives      = []
    bar_colour      = RETRO_WHITE if level.retro else NORMAL_WHITE

    for i in range(len(layout)):
        win.fill((0, 0, 0))
        win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
        bar = pygame.Surface((int(win.get_width() * ((i + 1) / len(layout))), 10), pygame.SRCALPHA)
        bar.fill(bar_colour)
        win.blit(bar, (0, win.get_height() - 12))
        pct = 100 * (i + 1) // len(layout)
        display_text(f'Building level... {" " if pct < 100 else ""}{" " if pct < 10 else ""}{pct}%', controller, min_pause_time=0, should_sleep=False, retro=level.retro, background=True)
        static_blocks.append([])
        for j in range(len(layout[i])):
            static_blocks[-1].append(None)
            for element in [str(token) for token in layout[i][j].split(" ")]:
                if len(element) > 0 and objects_dict.get(element) is not None:
                    entry = objects_dict[element]
                    if entry.get("data") is None or entry.get("type") is None:
                        continue
                    data        = entry["data"]
                    entity_type = entry["type"].upper()

                    # PLAYER is positional-only: it records a spawn point rather than an entity.
                    if entity_type == "PLAYER":
                        player_start     = ((j * block_size), (i * block_size))
                        player_face_left = False if data.get("face_left") is None else data["face_left"]
                        continue

                    # Stacking is read from the layout: a block is "stacked" when the tile directly
                    # above it is a blocking Block. Doors are always stacked; everything else is not.
                    is_stacked = False
                    if entity_type in ("BLOCK", "BREAKABLEBLOCK"):
                        if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"] and (objects_dict[str(layout[i - 1][j])].get("is_blocking") is not None and objects_dict[str(layout[i - 1][j])]["is_blocking"]):
                            is_stacked = True
                    elif entity_type == "DOOR":
                        is_stacked = True

                    built = build_entity(entity_type, data, element, level, controller, i, j, block_size, objects_dict, sprite_master, image_master, enemy_audios, block_audios, message_audios, is_stacked=is_stacked)
                    if built is None:
                        continue

                    # File the constructed entity into the appropriate collection(s).
                    if entity_type in ("BLOCK", "BREAKABLEBLOCK"):
                        blocks.append(built)
                        static_blocks[-1][-1] = built
                    elif entity_type in ("MOVINGBLOCK", "MOVABLEBLOCK"):
                        blocks.append(built)
                        dynamic_blocks.append(built)
                    elif entity_type == "DOOR":
                        blocks.append(built)
                        if doors.get(j) is None:
                            doors[j] = [built]
                        else:
                            doors[j].append(built)
                    elif entity_type in ("HAZARD", "MOVINGHAZARD"):
                        hazards.append(built)
                    elif entity_type == "FALLINGHAZARD":
                        hazards.append(built)
                        if falling_hazards.get(j) is None:
                            falling_hazards[j] = [built]
                        else:
                            falling_hazards[j].append(built)
                    elif entity_type in ("ENEMY", "BOSS"):
                        enemies.append(built)
                    elif entity_type == "OBJECTIVE":
                        objectives.append(built)
                    elif isinstance(built, Trigger):
                        triggers.append(built)

    if player_sprite is not None:
        selected_sprite = selected_retro_sprite = f"{player_sprite}Player{controller.player_sprite_selected}"
    else:
        selected_sprite       = f"Player{controller.player_sprite_selected}"
        selected_retro_sprite = f"RetroPlayer{controller.player_sprite_selected}"
    player = Player(level, controller, player_start[0], player_start[1], sprite_master, player_audios, controller.difficulty, block_size, sprite=selected_sprite, retro_sprite=selected_retro_sprite)
    if player_face_left:
        player.direction = player.facing = MovementDirection.LEFT

    to_link = [ent for ent in [player] + blocks + hazards + enemies + objectives if hasattr(ent, "trigger")]
    for i, ent in enumerate(to_link):
        win.fill((0, 0, 0))
        win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
        bar = pygame.Surface((int(win.get_width() * ((i + 1) / len(to_link))), 10), pygame.SRCALPHA)
        bar.fill(bar_colour)
        win.blit(bar, (0, win.get_height() - 12))
        pct = 100 * (i + 1) // len(to_link)
        display_text(f'Linking game objects... {" " if pct < 100 else ""}{" " if pct < 10 else ""}{pct}%', controller, min_pause_time=0, should_sleep=False, retro=level.retro, background=True)
        ent.link_triggers(triggers)

    return level_bounds, player, triggers, blocks, dynamic_blocks, doors, static_blocks, hazards, falling_hazards, enemies, objectives
