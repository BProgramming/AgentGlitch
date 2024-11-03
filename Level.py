from os.path import join

import pygame

from Block import Block, BreakableBlock, MovingBlock, MovableBlock, Hazard, MovingHazard
from Player import Player
from Enemy import Enemy
from Trigger import Trigger, TriggerType
from WeatherEffects import Rain, Snow


class Level:
    BLOCK_SIZE = 96

    def __init__(self, name, levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, win, controller, block_size=BLOCK_SIZE):
        self.name = name.upper()
        self.time = 0
        self.purge_queue = {"triggers": set(), "hazards": set(), "blocks": set(), "enemies": set()}
        self.grayscale = (False if meta_dict[name].get("grayscale") is None else bool(meta_dict[name]["grayscale"].upper() == "TRUE"))
        self.can_glitch = (False if meta_dict[name].get("can_glitch") is None else bool(meta_dict[name]["can_glitch"].upper() == "TRUE"))
        self.background = (None if meta_dict[name].get("background") is None else meta_dict[name]["background"])
        self.foreground = (None if meta_dict[name].get("foreground") is None else meta_dict[name]["foreground"])
        self.start_screen = (None if meta_dict[name].get("start_screen") is None else meta_dict[name]["start_screen"])
        self.end_screen = (None if meta_dict[name].get("end_screen") is None else meta_dict[name]["end_screen"])
        self.start_message = (None if meta_dict[name].get("start_message") is None else meta_dict[name]["start_message"])
        self.end_message = (None if meta_dict[name].get("end_message") is None else meta_dict[name]["end_message"])
        self.music = (None if meta_dict[name].get("music") is None else meta_dict[name]["music"])
        self.level_bounds, self.player, self.triggers, self.hazards, self.blocks, self.enemies = build_level(self, levels[self.name], sprite_master, image_master, objects_dict, player_audios, enemy_audios, win, controller, None if meta_dict[name].get("player_sprite") is None or meta_dict[name]["player_sprite"].upper() == "NONE" else meta_dict[name]["player_sprite"], block_size if meta_dict[name].get("block_size") is None or not meta_dict[name]["block_size"].isnumeric() else int(meta_dict[name]["block_size"]))
        self.weather = (None if meta_dict[name].get("weather") is None else self.get_weather(meta_dict[name]["weather"].upper()))

    def get_player(self):
        return self.player

    def get_objects(self):
        return self.triggers + self.hazards + self.blocks + self.enemies

    def queue_purge(self, obj):
        if isinstance(obj, Trigger):
            self.purge_queue["triggers"].add(obj)
        elif isinstance(obj, Hazard):
            self.purge_queue["hazards"].add(obj)
        elif isinstance(obj, Block):
            self.purge_queue["blocks"].add(obj)
        elif isinstance(obj, Enemy):
            self.purge_queue["enemies"].add(obj)

    def purge(self):
        if bool(self.purge_queue["triggers"]):
            self.triggers = [obj for obj in self.triggers if obj not in self.purge_queue["triggers"]]
            self.purge_queue["triggers"].clear()
        if bool(self.purge_queue["hazards"]):
            self.hazards = [obj for obj in self.hazards if obj not in self.purge_queue["hazards"]]
            self.purge_queue["hazards"].clear()
        if bool(self.purge_queue["blocks"]):
            self.blocks = [obj for obj in self.blocks if obj not in self.purge_queue["blocks"]]
            self.purge_queue["blocks"].clear()
        if bool(self.purge_queue["enemies"]):
            self.enemies = [obj for obj in self.enemies if obj not in self.purge_queue["enemies"]]
            self.purge_queue["enemies"].clear()

    #NOTE: having weather with lots of particles + lots of enemies + bullets will decrease the frame rate
    def get_weather(self, name):
        if name is None:
            return None
        else:
            if name == "RAIN":
                return Rain(self)
            elif name == "SNOW":
                return Snow(self)
            else:
                return None

    def draw(self):
        img = pygame.surface.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        for obj in self.get_objects() + [self.get_player()]:
            img.blit(obj.sprite, (obj.rect.x, obj.rect.y))
        pygame.image.save(img, join("Assets", "Levels", self.name + ".png"))


def build_level(level, layout, sprite_master, image_master, objects_dict, player_audios, enemy_audios, win, controller, player_sprite, block_size):
    width = len(layout[-1]) * block_size
    height = len(layout) * block_size
    level_bounds = [(0, 0), (width, height)]
    player_start = (0, 0)

    blocks = []
    triggers = []
    enemies = []
    hazards = []
    for i in range(len(layout)):
        for j in range(len(layout[i])):
            element = str(layout[i][j])
            if len(element) > 0 and objects_dict.get(element) is not None:
                entry = objects_dict[element]
                data = entry["data"]
                match entry["type"].upper():
                    case "PLAYER":
                        player_start = ((j * block_size), (i * block_size))
                    case "BLOCK":
                        if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                            is_stacked = True
                        else:
                            is_stacked = False
                        blocks.append(Block(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "BREAKABLEBLOCK":
                        if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                            is_stacked = True
                        else:
                            is_stacked = False
                        blocks.append(BreakableBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVINGBLOCK":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        blocks.append(MovingBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVABLEBLOCK":
                        is_stacked = False
                        blocks.append(MovableBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "HAZARD":
                        hazards.append(Hazard(level, j * block_size, i * block_size, block_size, data["height"], image_master, controller.difficulty, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVINGHAZARD":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        is_stacked = False
                        hazards.append(MovingHazard(level, j * block_size, i * block_size, block_size, data["height"], image_master, controller.difficulty, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "ENEMY":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path_in = list(map(int, data["path"].split(' ')))
                            path = []
                            for k in range(0, len(path_in), 2):
                                path.append(((path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size))
                        enemies.append(Enemy(level, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"])))
                    case "TRIGGER":
                        triggers.append(Trigger(level, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, win, controller, objects_dict, sprite_master, enemy_audios, image_master, block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=element))
                    case _:
                        pass

    player = Player(level, player_start[0], player_start[1], sprite_master, player_audios, controller.difficulty, sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected))

    return level_bounds, player, triggers, hazards, blocks, enemies
