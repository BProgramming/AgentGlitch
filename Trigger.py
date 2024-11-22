import time
import pygame
from enum import Enum
from os.path import join, isfile
from Helpers import display_text, load_text_from_file, load_path
from Object import Object
from Block import Block, BreakableBlock, MovableBlock, Hazard, MovingBlock, MovingHazard, Door, FallingHazard
from Enemy import Enemy
from Boss import Boss


class TriggerType(Enum):
    TEXT = 1
    SOUND = 2
    SPAWN = 3
    REVERT = 4
    SAVE = 5
    CHANGE_LEVEL = 6
    SET_PROPERTY = 7


class Trigger(Object):
    def __init__(self, level, controller, x, y, width, height, win, objects_dict, sprite_master, enemy_audios, block_audios, image_master, block_size, fire_once=False, type=None, input=None, name="Trigger"):
        super().__init__(level, controller, x, y, width, height, name=name)
        self.win = win
        self.fire_once = fire_once
        self.has_fired = False
        self.type = type
        self.value = self.load_input(input, objects_dict, sprite_master, enemy_audios, block_audios, image_master, block_size)

    def save(self):
        if self.has_fired:
            return {self.name: {"has_fired": self.has_fired}}
        else:
            return None

    def load(self, obj):
        self.has_fired = obj["has_fired"]

    def load_input(self, input, objects_dict, sprite_master, enemy_audios, block_audios, image_master, block_size):
        if input is None or self.type is None:
            return None
        elif self.type == TriggerType.TEXT:
            return load_text_from_file(input)
        elif self.type == TriggerType.CHANGE_LEVEL:
            return input.upper()
        elif self.type == TriggerType.SOUND:
            path = join("Assets", "SoundEffects", "triggers", input)
            if not isfile(path) or len(input) < 4 or (input[-4:] != ".wav" and input[-4:] != ".mp3"):
                return None
            else:
                return pygame.mixer.Sound(path)
        elif self.type == TriggerType.SPAWN:
            element = input["name"]
            if len(element) > 0 and objects_dict.get(element) is not None:
                j, i = tuple(map(int, input["coords"].split(' ')))
                entry = objects_dict[element]
                data = entry["data"]
                match entry["type"].upper():
                    case "BLOCK":
                        is_stacked = False
                        return Block(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "BREAKABLEBLOCK":
                        is_stacked = False
                        return BreakableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"], coord_x2=data["coord_x2"], coord_y2=data["coord_y2"])
                    case "MOVINGBLOCK":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        is_stacked = False
                        return MovingBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master,block_audios,  is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "DOOR":
                        is_stacked = False
                        return Door(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=bool(data["is_locked"].upper() == "TRUE"), coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "MOVABLEBLOCK":
                        is_stacked = False
                        return MovableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "HAZARD":
                        return Hazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "MOVINGHAZARD":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        is_stacked = False
                        return MovingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "FALLINGHAZARD":
                        return FallingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "ENEMY":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        return Enemy(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]))
                    case "BOSS":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        return Boss(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, music=(None if data.get("music") is None or data["music"].upper() == "NONE" else data["music"]), path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=( None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=data["sprite"])
                    case "TRIGGER":
                        return Trigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, self.win, objects_dict, sprite_master, enemy_audios, block_audios, image_master, block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=element)
                    case _:
                        pass
            return None
        elif self.type == TriggerType.SET_PROPERTY:
            if input.get("target") is None or input.get("property") is None or input.get("value") is None:
                return None
            else:
                return input
        else:
            return None

    def collide(self):
        start = time.perf_counter_ns()

        next_level = None
        if (self.fire_once and self.has_fired) or self.type is None or self.value is None:
            return [0, next_level]
        self.has_fired = True

        if self.type == TriggerType.TEXT:
            display_text(self.value, self.win, self.controller)
        elif self.type == TriggerType.SOUND:
            if self.value is not None:
                pygame.mixer.find_channel(force=True).play(self.value)
        elif self.type == TriggerType.SPAWN:
            if self.value is not None:
                if isinstance(self.value, Trigger):
                    self.level.triggers.append(self.value)
                elif isinstance(self.value, Enemy):
                    self.level.enemies.append(self.value)
                elif isinstance(self.value, Hazard):
                    self.level.hazards.append(self.value)
                elif isinstance(self.value, Block):
                    self.level.blocks.append(self.value)
        elif self.type == TriggerType.REVERT:
            self.level.get_player().revert()
        elif self.type == TriggerType.SAVE:
            self.level.get_player().save()
        elif self.type == TriggerType.CHANGE_LEVEL:
            next_level = self.value
        elif self.type == TriggerType.SET_PROPERTY:
            if self.value is not None:
                target, property, value = self.value["target"], self.value["property"], self.value["value"]
                if len(target) == len(property) == len(value):
                    for i in range(len(target)):
                        if isinstance(value[i], bool) or value[i].upper() in ("TRUE", "FALSE"):
                            value[i] = bool(value[i])
                        elif value[i].isnumeric():
                            value[i] = float(value[i])
                            if value[i] == int(value[i]):
                                value[i] = int(value[i])
                        for obj in [self.level.get_player()] + self.level.get_objects():
                            if obj.name[:len(target[i])].upper() == target[i].upper() and hasattr(obj, property[i]):
                                setattr(obj, property[i], value[i])
                                if self.controller.player_abilities.get(property[i]) is not None:
                                    self.controller.player_abilities[property[i]] = value[i]

        return [(time.perf_counter_ns() - start) // 1000000, next_level]

    def output(self, win, offset_x, offset_y, master_volume, fps):
        pass

