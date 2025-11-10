import time
import pygame
from enum import Enum
from os.path import join, isfile
from Helpers import display_text, load_text_from_file, load_path, set_property, ASSETS_FOLDER
from Entity import Entity
from Block import Block, BreakableBlock, MovableBlock, Hazard, MovingBlock, MovingHazard, Door, FallingHazard
from Objective import Objective
from NonPlayer import NonPlayer
from Boss import Boss

class TriggerType(Enum):
    NONE = 0
    TEXT = 1
    SOUND = 2
    SPAWN = 3
    REVERT = 4
    SAVE = 5
    CHANGE_LEVEL = 6
    SET_PROPERTY = 7
    CINEMATIC = 8
    SET_ACHIEVEMENT = 9
    SET_OBJECTIVE = 10
    HOT_SWAP_LEVEL = 11
    SCROLL_CAMERA_TO_POINT = 12
    SCROLL_CAMERA_TO_PLAYER = 13
    SET_DISCORD_STATUS = 14

    @classmethod
    def convert_string(cls, string: str) -> 'TriggerType':
        try:
            return TriggerType[string.upper()]
        except KeyError:
            return TriggerType.NONE

class Trigger(Entity):
    def __init__(self, level, controller, x, y, width, height, win, objects_dict, sprite_master, enemy_audios, block_audios, message_audios, image_master, block_size, fire_once=False, type=None, input=None, name="Trigger"):
        super().__init__(level, controller, x, y, width, height, name=name)
        self.win = win
        self.fire_once = fire_once
        self.has_fired = False
        self.type = type
        if type is not None and type != TriggerType.NONE:
            self.value = self.__load_input__(input, objects_dict, sprite_master, enemy_audios, block_audios, message_audios, image_master, block_size)
        else:
            self.value = None

    def save(self) -> dict | None:
        if self.has_fired:
            return {self.name: {"has_fired": self.has_fired}}
        else:
            return None

    def load(self, ent) -> None:
        self.has_fired = ent["has_fired"]

    # THIS CAN RETURN SO MANY DIFFERENT THINGS, SO IT DOESN'T HAVE A TYPE HINT. #
    def __load_input__(self, input, objects_dict, sprite_master, enemy_audios, block_audios, message_audios, image_master, block_size):
        if (input is None and self.type != TriggerType.HOT_SWAP_LEVEL) or self.type is None or self.type == TriggerType.NONE:
            return None
        match self.type:
            case TriggerType.TEXT:
                if type(input) == dict and input.get("text") is not None and input.get("audio") is not None:
                    return {"text": load_text_from_file(input["text"]), "audio": message_audios[input["audio"]]}
                else:
                    return load_text_from_file(input)
            case TriggerType.CHANGE_LEVEL:
                return input.upper()
            case TriggerType.SOUND:
                path = join(ASSETS_FOLDER, "SoundEffects", "triggers", input)
                if not isfile(path) or len(input) < 4 or (input[-4:] != ".wav" and input[-4:] != ".mp3"):
                    return None
                else:
                    return pygame.mixer.Sound(path)
            case TriggerType.SPAWN:
                element = input["name"]
                if len(element) > 0 and objects_dict.get(element) is not None:
                    j, i = tuple(map(int, input["coords"].split(' ')))
                    entry = objects_dict[element]
                    data = entry["data"]

                    def __convert_coords__(coord: int) -> int:
                        actual_size = block_size // 2
                        if coord < actual_size:
                            return coord * actual_size
                        else:
                            return coord

                    match entry["type"].upper():
                        case "OBJECTIVE":
                            return Objective(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, sprite_master, block_audios, is_active=bool(data.get("is_active") is not None and data["is_active"].upper() == "TRUE"), sprite=(None if data.get("sprite") is None else data["sprite"]), sound=("objective" if data.get("sound") is None else data["sound"].lower()), text=(None if data.get("text") is None else data["text"]), trigger=(None if data.get("trigger") is None else data["trigger"]), is_blocking=bool(data.get("is_blocking") is not None and data["is_blocking"].upper() == "TRUE"), achievement=(None if data.get("achievement") is None else data["achievement"]), name=(element if data.get("name") is None else data["name"]))
                        case "BLOCK":
                            is_stacked = False
                            return Block(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                        case "BREAKABLEBLOCK":
                            is_stacked = False
                            return BreakableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), coord_x2=__convert_coords__(data["coord_x2"]), coord_y2=__convert_coords__(data["coord_y2"]), name=(element if data.get("name") is None else data["name"]))
                        case "MOVINGBLOCK":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                            is_stacked = False
                            return MovingBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, is_enabled=(True if data.get("is_enabled") is None or data["is_enabled"].upper() != "FALSE" else False), hold_for_collision=(False if data.get("hold_for_collision") is None or data["hold_for_collision"].upper() != "TRUE" else True), speed=data["speed"], path=path, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                        case "DOOR":
                            is_stacked = False
                            return Door(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=bool(data.get("is_locked") is not None and data["is_locked"].upper() == "TRUE"), coord_x=(0 if data.get("coord_x") is None else __convert_coords__(data["coord_x"])), coord_y=(0 if data.get("coord_y") is None else __convert_coords__(data["coord_y"])), locked_coord_x=(None if data.get("locked_coord_x") is None else __convert_coords__(data["locked_coord_x"])), locked_coord_y=(None if data.get("locked_coord_y") is None else __convert_coords__(data["locked_coord_y"])), unlocked_coord_x=(None if data.get("unlocked_coord_x") is None else __convert_coords__(data["unlocked_coord_x"])), unlocked_coord_y=(None if data.get("unlocked_coord_y") is None else __convert_coords__(data["unlocked_coord_y"])), name=(element if data.get("name") is None else data["name"]))
                        case "MOVABLEBLOCK":
                            is_stacked = False
                            return MovableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]))
                        case "HAZARD":
                            return Hazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                        case "MOVINGHAZARD":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                            is_stacked = False
                            return MovingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                        case "FALLINGHAZARD":
                            return FallingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                        case "ENEMY":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                            return NonPlayer(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, path=path, kill_at_end=bool(data.get("kill_at_end") is not None and data["kill_at_end"].upper() == "TRUE"), is_hostile=bool(data.get("is_hostile") is None or data["is_hostile"].upper() != "FALSE"), collision_message=(None if data.get("collision_message") is None else data["collision_message"]), bark=(None if data.get("bark") is None else data["bark"]), hp=data["hp"], can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"]))
                        case "BOSS":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                            return Boss(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, music=(None if data.get("music") is None or data["music"].upper() == "NONE" else data["music"]), trigger=(None if data.get("trigger") is None else data["trigger"]), path=path, hp=data["hp"], show_health_bar=(True if data.get("show_health_bar") is None or data["show_health_bar"].upper() != "FALSE" else False), can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"]))
                        case "TRIGGER":
                            return Trigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, self.win, objects_dict, sprite_master, enemy_audios, block_audios, message_audios, image_master, block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), type=(TriggerType(data["type"]) if isinstance(data["type"], int) else TriggerType.convert_string(data["type"])), input=(None if data.get("input") is None else data["input"]), name=(element if data.get("name") is None else data["name"]))
                        case _:
                            pass
                return None
            case TriggerType.SET_PROPERTY:
                if input.get("target") is None or input.get("property") is None or input.get("value") is None:
                    return None
                else:
                    return input
            case TriggerType.SET_OBJECTIVE:
                if input.get("target") is None or input.get("value") is None:
                    return None
                else:
                    return {"target": input["target"], "value": bool(input["value"].upper() == "TRUE")}
            case TriggerType.CINEMATIC:
                return input
            case TriggerType.SET_ACHIEVEMENT:
                return input
            case TriggerType.HOT_SWAP_LEVEL:
                return True
            case TriggerType.SCROLL_CAMERA_TO_POINT:
                txt = input["coords"].split(' ')
                return {"coords": (int(txt[0]) * block_size, int(txt[1]) * block_size), "time": (0.0 if input.get("time") is None else input["time"])}
            case TriggerType.SCROLL_CAMERA_TO_PLAYER:
                return None
            case TriggerType.SET_DISCORD_STATUS:
                return {"state": "" if input.get("state") is None else input["state"], "details": "" if input.get("details") is None else input["details"]}
        return None

    def collide(self, ent: Entity | None) -> list:
        start = time.perf_counter_ns()

        next_level = None
        if ((self.fire_once or self.type == TriggerType.CINEMATIC) and self.has_fired) or self.type is None or self.value is None:
            return [0, next_level]
        self.has_fired = True

        match self.type:
            case TriggerType.TEXT:
                if type(self.value) == dict and self.value.get("text") is not None and self.value.get("audio") is not None:
                    display_text(self.value["text"], self.controller, audio=self.value["audio"], should_type_text=True, retro=self.level.retro)
                else:
                    display_text(self.value, self.controller, should_type_text=True, retro=self.level.retro)
            case TriggerType.SOUND:
                if self.value is not None:
                    pygame.mixer.find_channel(force=True).play(self.value)
            case TriggerType.SPAWN:
                if self.value is not None:
                    if isinstance(self.value, Trigger):
                        self.level.triggers.append(self.value)
                    elif isinstance(self.value, NonPlayer):
                        self.level.enemies.append(self.value)
                    elif isinstance(self.value, Hazard):
                        self.level.hazards.append(self.value)
                    elif isinstance(self.value, Block):
                        self.level.blocks.append(self.value)
            case TriggerType.REVERT:
                self.level.player.revert()
            case TriggerType.SAVE:
                self.level.player.save()
            case TriggerType.CHANGE_LEVEL:
                next_level = self.value
            case TriggerType.SET_PROPERTY:
                set_property(self, self.value)
            case TriggerType.SET_OBJECTIVE:
                text = None
                for objective in self.level.objectives:
                    if self.value["target"] == objective.name:
                        objective.is_active = self.value["value"]
                        if text is None and objective.text is not None:
                            text = objective.text
                self.controller.activate_objective(text)
            case TriggerType.CINEMATIC:
                if self.level.cinematics is not None and self.level.cinematics.get(self.value) is not None:
                    self.level.cinematics.queue(self.value)
            case TriggerType.SET_ACHIEVEMENT:
                if self.controller.steamworks is not None and not self.controller.steamworks.UserStats.GetAchievement(self.value):
                    self.controller.steamworks.UserStats.SetAchievement(self.value)
                    self.controller.should_store_steam_stats = True
            case TriggerType.HOT_SWAP_LEVEL:
                self.controller.should_hot_swap_level = True
            case TriggerType.SCROLL_CAMERA_TO_POINT:
                self.controller.should_scroll_to_point = self.value
            case TriggerType.SCROLL_CAMERA_TO_PLAYER:
                self.controller.should_scroll_to_point = None
            case TriggerType.SET_DISCORD_STATUS:
                self.controller.discord.set_status(details=self.value["details"], state=self.value["state"])
        return [(time.perf_counter_ns() - start) // 1000000, next_level]

    def draw(self, win, offset_x, offset_y, master_volume) -> None:
        pass
