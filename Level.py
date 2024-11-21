from os.path import join
import pygame
from Block import Block, BreakableBlock, MovingBlock, MovableBlock, Hazard, MovingHazard, Door, FallingHazard
from Boss import Boss
from Player import Player
from Enemy import Enemy
from Trigger import Trigger, TriggerType
from WeatherEffects import Rain, Snow
from Helpers import load_path, validate_file_list


class Level:
    BLOCK_SIZE = 96

    def __init__(self, name, levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, win, controller, block_size=BLOCK_SIZE):
        self.name = name.upper()
        self.block_size = block_size if meta_dict[name].get("block_size") is None or not meta_dict[name]["block_size"].isnumeric() else int(meta_dict[name]["block_size"])
        self.time = 0
        self.purge_queue = {"triggers": set(), "hazards": set(), "blocks": set(), "doors": set(), "enemies": set()}
        self.grayscale = (False if meta_dict[name].get("grayscale") is None else bool(meta_dict[name]["grayscale"].upper() == "TRUE"))
        self.can_glitch = (False if meta_dict[name].get("can_glitch") is None else bool(meta_dict[name]["can_glitch"].upper() == "TRUE"))
        self.background = (None if meta_dict[name].get("background") is None else meta_dict[name]["background"])
        self.foreground = (None if meta_dict[name].get("foreground") is None else meta_dict[name]["foreground"])
        self.start_screen = (None if meta_dict[name].get("start_screen") is None else meta_dict[name]["start_screen"])
        self.end_screen = (None if meta_dict[name].get("end_screen") is None else meta_dict[name]["end_screen"])
        self.start_message = (None if meta_dict[name].get("start_message") is None else meta_dict[name]["start_message"])
        self.end_message = (None if meta_dict[name].get("end_message") is None else meta_dict[name]["end_message"])
        self.music = (None if meta_dict[name].get("music") is None else validate_file_list("Music", list(meta_dict[name]["music"].split(' ')), "mp3"))
        self.level_bounds, self.player, self.triggers, self.blocks, self.dynamic_blocks, self.doors, self.static_blocks, self.hazards, self.enemies = build_level(self, levels[self.name], sprite_master, image_master, objects_dict, player_audios, enemy_audios, win, controller, None if meta_dict[name].get("player_sprite") is None or meta_dict[name]["player_sprite"].upper() == "NONE" else meta_dict[name]["player_sprite"], self.block_size)
        self.weather = (None if meta_dict[name].get("weather") is None else self.get_weather(meta_dict[name]["weather"].upper()))

    def get_player(self):
        return self.player

    def get_objects(self):
        return self.triggers + self.blocks + self.hazards + self.enemies

    def get_objects_in_range(self, point, dist=1, blocks_only=False):
        x = int(point[0] / self.block_size)
        y = int(point[1] / self.block_size)
        # this sum thing below is a hack to turn a 2D list into a 1D list since it applies the + operator to the second (optional) [] argument (e.g. an empty list), thereby concatenating all the elements
        in_range = [block for block in sum([row[max(x - (dist - 1), 0):min(x + dist + 1, len(row))] for row in self.static_blocks[max(y - (dist - 1), 0):min(y + dist + 1, len(self.static_blocks))]], []) if block is not None]
        for i in range(dist - 1, dist + 1):
            if self.doors.get(x + i) is not None:
                in_range += self.doors[x + i]

        if not blocks_only:
            for obj in self.triggers + self.dynamic_blocks + self.hazards + self.enemies:
                if obj.rect.x - (self.block_size * dist) <= point[0] <= obj.rect.x + (self.block_size * dist) and obj.rect.y - (self.block_size * dist) <= point[1] <= obj.rect.y + (self.block_size * dist):
                    in_range.append(obj)

        return in_range

    def queue_purge(self, obj):
        if isinstance(obj, Trigger):
            self.purge_queue["triggers"].add(obj)
        if isinstance(obj, Hazard):
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
            self.dynamic_blocks = [obj for obj in self.dynamic_blocks if obj not in self.purge_queue["blocks"]]
            for i in range(len(self.static_blocks)):
                self.static_blocks[i] = [obj for obj in self.static_blocks[i] if obj not in self.purge_queue["blocks"]]
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

    def save_image(self):
        img = pygame.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        for obj in self.get_objects() + [self.get_player()]:
            img.blit(obj.sprite, (obj.rect.x, obj.rect.y))
        pygame.image.save(img, join("Assets", "Levels", self.name + ".png"))

    def __get_static_block_slice__(self, win, offset_x, offset_y):
        return [row[int(offset_x // self.block_size):int((offset_x + (1.5 * win.get_width())) // self.block_size)] for row in self.static_blocks[int(offset_y // self.block_size):int((offset_y + (1.5 * win.get_height())) // self.block_size)]]

    def output(self, win, offset_x, offset_y, master_volume, fps):
        for obj in self.triggers + self.__get_static_block_slice__(win, offset_x, offset_y) + self.dynamic_blocks + list(self.doors.values()) + self.hazards + self.enemies:
            if isinstance(obj, list):
                for obj_lower in obj:
                    if obj_lower is not None:
                        obj_lower.output(win, offset_x, offset_y, master_volume, fps)
            else:
                obj.output(win, offset_x, offset_y, master_volume, fps)

        self.player.output(win, offset_x, offset_y, master_volume, fps)

        if self.weather is not None:
            self.weather.draw(win, offset_x, offset_y)


def build_level(level, layout, sprite_master, image_master, objects_dict, player_audios, enemy_audios, win, controller, player_sprite, block_size):
    width = len(layout[-1]) * block_size
    height = len(layout) * block_size
    level_bounds = [(0, 0), (width, height)]
    player_start = (0, 0)

    blocks = []
    doors = {}
    dynamic_blocks = []
    static_blocks = []
    triggers = []
    enemies = []
    hazards = []
    for i in range(len(layout)):
        static_blocks.append([])
        for j in range(len(layout[i])):
            static_blocks[-1].append(None)
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
                        block = Block(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                        blocks.append(block)
                        static_blocks[-1][-1] = block
                    case "BREAKABLEBLOCK":
                        if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                            is_stacked = True
                        else:
                            is_stacked = False
                        block = BreakableBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"], coord_x2=data["coord_x2"], coord_y2=data["coord_y2"])
                        blocks.append(block)
                        static_blocks[-1][-1] = block
                    case "MOVINGBLOCK":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        is_stacked = False
                        block = MovingBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"])
                        blocks.append(block)
                        dynamic_blocks.append(block)
                    case "DOOR":
                        is_stacked = False
                        block = Door(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=bool(data["is_locked"].upper() == "TRUE"), coord_x=data["coord_x"], coord_y=data["coord_y"])
                        blocks.append(block)
                        if doors.get(j) is None:
                            doors[j] = [block]
                        else:
                            doors[j].append(block)
                    case "MOVABLEBLOCK":
                        is_stacked = False
                        block = MovableBlock(level, j * block_size, i * block_size, block_size, block_size, image_master, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"])
                        blocks.append(block)
                        dynamic_blocks.append(block)
                    case "HAZARD":
                        hazards.append(Hazard(level, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, controller.difficulty, hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "MOVINGHAZARD":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        is_stacked = False
                        hazards.append(MovingHazard(level, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "FALLINGHAZARD":
                        hazards.append(FallingHazard(level, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), hit_sides=data["hit_sides"].upper(), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"]))
                    case "ENEMY":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        enemies.append(Enemy(level, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"])))
                    case "BOSS":
                        if data["path"].upper() == "NONE":
                            path = None
                        else:
                            path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                        enemies.append(Boss(level, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, music=(None if data.get("music") is None or data["music"].upper() == "NONE" else data["music"]), path=path, hp=data["hp"], can_shoot=bool(data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data["proj_sprite"].upper() == "NONE" else data["proj_sprite"])))
                    case "TRIGGER":
                        triggers.append(Trigger(level, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, win, controller, objects_dict, sprite_master, enemy_audios, image_master, block_size, fire_once=bool(data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=element))
                    case _:
                        pass

    player = Player(level, player_start[0], player_start[1], sprite_master, player_audios, controller.difficulty, block_size, sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[0]), retro_sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[1]))

    return level_bounds, player, triggers, blocks, dynamic_blocks, doors, static_blocks, hazards, enemies
