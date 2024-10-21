import time
import pygame
from enum import Enum
from os.path import join, isfile
from Helpers import display_text
from Object import Object
from Block import Block, BreakableBlock, MovableBlock, Hazard, MovingBlock, MovingHazard
from Enemy import Enemy


class TriggerType(Enum):
    TEXT = 1
    SOUND = 2
    SPAWN = 3
    REVERT = 4
    SAVE = 5
    END = 6
    SET_PROPERTY = 7


class Trigger(Object):
    def __init__(self, x, y, width, height, win, controller, spawn_dict, level_bounds, sprite_master, enemy_audios, image_master, block_size, fire_once=False, type=None, input=None, name="Trigger"):
        super().__init__(x, y, width, height, name=name)
        self.win = win
        self.controller = controller
        self.fire_once = fire_once
        self.has_fired = False
        self.type = type
        self.output = self.load_input(input, spawn_dict, level_bounds, sprite_master, enemy_audios, image_master, block_size)
        self.player = None
        self.triggers = None
        self.enemies = None
        self.blocks = None
        self.hazards = None

    def save(self):
        if self.has_fired:
            return {self.name: {"has_fired": self.has_fired}}
        else:
            return None

    def load(self, obj):
        self.has_fired = obj["has_fired"]

    def load_input(self, input, objects_dict, level_bounds, sprite_master, enemy_audios, image_master, block_size):
        if input is None or self.type is None:
            return None
        elif self.type == TriggerType.TEXT or self.type == TriggerType.END:
            path = join("Assets", "Text", input)
            if not isfile(path) or len(input) < 4 or input[-4:] != ".txt":
                text = ["Error: text file " + path + " not found."]
            else:
                text = []
                with open(path, "r") as file:
                    for line in file:
                        text.append(line.replace("\n", ""))
            return text
        elif self.type == TriggerType.SOUND:
            path = join("Assets", "TriggerAudio", input)
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
                        return Block(j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "BREAKABLEBLOCK":
                        is_stacked = False
                        return BreakableBlock(j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "MOVINGBLOCK":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        return MovingBlock(j * block_size, i * block_size, level_bounds, block_size, block_size, image_master, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "MOVABLEBLOCK":
                        is_stacked = False
                        return MovableBlock(j * block_size, i * block_size, level_bounds, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "HAZARD":
                        return Hazard(j * block_size, i * block_size, block_size, data["height"], image_master, self.controller.difficulty, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "MOVINGHAZARD":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        return MovingHazard(j * block_size, i * block_size, level_bounds, block_size, data["height"], image_master, self.controller.difficulty, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"])
                    case "ENEMY":
                        path_in = list(map(int, data["path"].split(' ')))
                        path = []
                        for k in range(0, len(path_in), 2):
                            path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        return Enemy(j * block_size, i * block_size, level_bounds, sprite_master, enemy_audios, self.controller.difficulty, path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]))
                    case "TRIGGER":
                        return Trigger(j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, self.win, self.controller, objects_dict, level_bounds, sprite_master, enemy_audios, image_master, block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=element)
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

    def collide(self, player):
        start = time.perf_counter_ns()

        end_level = False
        if (self.fire_once and self.has_fired) or self.type is None or self.output is None:
            return [0, end_level]
        self.has_fired = True

        if self.type == TriggerType.TEXT:
            display_text(self.output, self.win, self.controller)
        elif self.type == TriggerType.SOUND:
            if self.output is not None:
                pygame.mixer.find_channel(force=True).play(self.output)
        elif self.type == TriggerType.SPAWN:
            if self.output is not None:
                if isinstance(self.output, Trigger):
                    self.triggers.append(self.output)
                elif isinstance(self.output, Enemy):
                    self.output.player = self.player
                    self.enemies.append(self.output)
                elif isinstance(self.output, Hazard):
                    self.hazards.append(self.output)
                elif isinstance(self.output, Block):
                    self.blocks.append(self.output)
        elif self.type == TriggerType.REVERT:
            player.revert()
        elif self.type == TriggerType.SAVE:
            player.save()
        elif self.type == TriggerType.END:
            display_text(self.output, self.win, self.controller)
            end_level = True
        elif self.type == TriggerType.SET_PROPERTY:
            if self.output is not None:
                target, property, value = self.output["target"], self.output["property"], self.output["value"]
                if len(target) == len(property) == len(value):
                    for i in range(len(target)):
                        if value[i].upper() in ("TRUE", "FALSE"):
                            value[i] = bool(value[i])
                        elif value[i].isnumeric():
                            value[i] = float(value[i])
                            if value[i] == int(value[i]):
                                value[i] = int(value[i])
                        for obj in [self.player] + self.triggers + self.enemies + self.blocks + self.hazards:
                            if obj.name[:len(target[i])].upper() == target[i].upper() and hasattr(obj, property[i]):
                                setattr(obj, property[i], value[i])

        return [(time.perf_counter_ns() - start) // 1000000, end_level]

