import pygame
from os.path import join
from Block import Block, BreakableBlock, MovingBlock, MovableBlock, Hazard, MovingHazard, Door, FallingHazard
from Boss import Boss
from Cinematics import CinematicsManager
from Player import Player
from Enemy import Enemy
from Objectives import Objective
from Trigger import Trigger, TriggerType
from WeatherEffects import *
from Helpers import load_path, validate_file_list, display_text


class Level:
    BLOCK_SIZE = 96

    def __init__(self, name, levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, block_audios, win, controller, block_size=BLOCK_SIZE):
        self.name = name.upper()
        self.time = 0
        self.revert_counter = 0
        self.objectives_collected = []
        self.achievement = (None if meta_dict[name].get("achievement") is None else meta_dict[name]["achievement"])
        self.block_size = block_size if meta_dict[name].get("block_size") is None or not meta_dict[name]["block_size"].isnumeric() else int(meta_dict[name]["block_size"])
        self.purge_queue = {"triggers": set(), "hazards": set(), "blocks": set(), "doors": set(), "enemies": set(), "objectives": set()}
        self.grayscale = (False if meta_dict[name].get("grayscale") is None else bool(meta_dict[name]["grayscale"].upper() == "TRUE"))
        self.can_glitch = (False if meta_dict[name].get("can_glitch") is None else bool(meta_dict[name]["can_glitch"].upper() == "TRUE"))
        self.background = (None if meta_dict[name].get("background") is None else meta_dict[name]["background"])
        self.foreground = (None if meta_dict[name].get("foreground") is None else meta_dict[name]["foreground"])
        self.start_cinematic = (None if meta_dict[name].get("start_cinematic") is None else meta_dict[name]["start_cinematic"])
        self.end_cinematic = (None if meta_dict[name].get("end_cinematic") is None else meta_dict[name]["end_cinematic"])
        if type(self.start_cinematic) not in [list, tuple]:
            self.start_cinematic = [self.start_cinematic]
        if type(self.end_cinematic) not in [list, tuple]:
            self.end_cinematic = [self.end_cinematic]
        self.start_message = (None if meta_dict[name].get("start_message") is None else meta_dict[name]["start_message"])
        self.end_message = (None if meta_dict[name].get("end_message") is None else meta_dict[name]["end_message"])
        self.music = (None if meta_dict[name].get("music") is None else validate_file_list("Music", list(meta_dict[name]["music"].split(' ')), "mp3"))
        self.level_bounds, self.player, self.triggers, self.blocks, self.dynamic_blocks, self.doors, self.static_blocks, self.hazards, self.enemies, self.objectives = self.build_level(self, levels[self.name], sprite_master, image_master, objects_dict, player_audios, enemy_audios, block_audios, win, controller, None if meta_dict[name].get("player_sprite") is None or meta_dict[name]["player_sprite"].upper() == "NONE" else meta_dict[name]["player_sprite"], self.block_size)
        self.weather = (None if meta_dict[name].get("weather") is None else self.get_weather(meta_dict[name]["weather"].upper()))
        if meta_dict[name].get("abilities") is not None:
            self.set_player_abilities(meta_dict[name]["abilities"])
        self.cinematics = (None if meta_dict[name].get("cinematics") is None else CinematicsManager(meta_dict[name]["cinematics"], controller))

    def get_formatted_time(self) -> str:
        minutes = self.time // 60000
        seconds = (self.time - (minutes * 60000)) // 1000
        milliseconds = self.time - ((minutes * 60000) + (seconds * 1000))
        return ("0" if minutes < 10 else "") + str(minutes) + ":" + ("0" if seconds < 10 else "") + str(seconds) + "." + ("0" if milliseconds < 100 else "") + ("0" if milliseconds < 10 else "") + str(milliseconds)

    def get_recap_text(self) -> list:
        return ["Mission time: " + self.get_formatted_time() + ".",
                "Packets collected: " + str(len(self.objectives_collected)) + ".",
                "Deaths: " + str(self.revert_counter) + "."]

    def get_player(self) -> Player:
        return self.player

    def set_player_abilities(self, abilities) -> None:
        if abilities.get("can_open_doors") is not None:
            self.player.can_open_doors = bool(abilities["can_open_doors"].upper() == "TRUE")
        if abilities.get("can_move_blocks") is not None:
            self.player.can_move_blocks = bool(abilities["can_move_blocks"].upper() == "TRUE")
        if abilities.get("can_block") is not None:
            self.player.can_block = bool(abilities["can_block"].upper() == "TRUE")
        if abilities.get("can_wall_jump") is not None:
            self.player.can_wall_jump = bool(abilities["can_wall_jump"].upper() == "TRUE")
        if abilities.get("can_teleport") is not None:
            self.player.can_teleport = bool(abilities["can_teleport"].upper() == "TRUE")
        if abilities.get("can_bullet_time") is not None:
            self.player.can_bullet_time = bool(abilities["can_bullet_time"].upper() == "TRUE")
        if abilities.get("can_resize") is not None:
            self.player.can_resize = bool(abilities["can_resize"].upper() == "TRUE")
        if abilities.get("can_heal") is not None:
            self.player.can_heal = bool(abilities["can_heal"].upper() == "TRUE")

    def get_objects(self) -> list:
        return self.triggers + self.blocks + self.hazards + self.enemies + self.objectives

    def get_objects_in_range(self, point, dist=1, blocks_only=False) -> list:
        x = int(point[0] / self.block_size)
        y = int(point[1] / self.block_size)
        # this sum thing below is a hack to turn a 2D list into a 1D list since it applies the + operator to the second (optional) [] argument (e.g. an empty list), thereby concatenating all the elements
        in_range = [block for block in sum([row[max(x - (dist - 1), 0):min(x + dist + 1, len(row))] for row in self.static_blocks[max(y - (dist - 1), 0):min(y + dist + 1, len(self.static_blocks))]], []) if block is not None]
        for i in range(dist - 1, dist + 1):
            if self.doors.get(x + i) is not None:
                in_range += self.doors[x + i]

        if not blocks_only:
            for obj in self.triggers + self.dynamic_blocks + self.hazards + self.enemies + self.objectives:
                if obj.rect.x - (self.block_size * dist) <= point[0] <= obj.rect.x + (self.block_size * dist) and obj.rect.y - (self.block_size * dist) <= point[1] <= obj.rect.y + (self.block_size * dist):
                    in_range.append(obj)

        return in_range

    def queue_purge(self, obj) -> None:
        if isinstance(obj, Trigger):
            self.purge_queue["triggers"].add(obj)
        if isinstance(obj, Hazard):
            self.purge_queue["hazards"].add(obj)
        elif isinstance(obj, Block):
            self.purge_queue["blocks"].add(obj)
        elif isinstance(obj, Enemy):
            self.purge_queue["enemies"].add(obj)
        elif isinstance(obj, Objective):
            self.purge_queue["objectives"].add(obj)

    def purge(self) -> None:
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
        if bool(self.purge_queue["objectives"]):
            self.objectives = [obj for obj in self.objectives if obj not in self.purge_queue["objectives"]]
            self.purge_queue["objectives"].clear()

    #NOTE: having weather with lots of particles + lots of enemies + bullets will decrease the frame rate
    def get_weather(self, name) -> ParticleEffect | None:
        if name is None:
            return None
        else:
            if name == "RAIN":
                return Rain(self)
            elif name == "SNOW":
                return Snow(self)
            else:
                return None

    def gen_image(self) -> None:
        img = pygame.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        for obj in self.get_objects() + [self.get_player()]:
            img.blit(obj.sprite, (obj.rect.x, obj.rect.y))
        pygame.image.save(img, join("Assets", "Misc", self.name + ".png"))

    def gen_background(self) -> None:
        img = pygame.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        img.fill((255, 255, 255, 255))
        square = pygame.Surface((self.block_size, self.block_size), pygame.SRCALPHA)
        square.fill((0, 0, 0, 255))
        for row in self.static_blocks:
            for column in row:
                if column is not None:
                    img.blit(square, (column.rect.x, column.rect.y))
        square.fill((255, 0, 0, 255))
        for block in self.hazards + [door for doors in list(self.doors.values()) for door in doors]:
            img.blit(square, (block.rect.x, block.rect.y))
        pygame.image.save(img, join("Assets", "Misc", self.name + "_bg.png"))

    def __get_static_block_slice__(self, win, offset_x, offset_y) -> list:
        return [row[int(offset_x // self.block_size):int((offset_x + (1.5 * win.get_width())) // self.block_size)] for row in self.static_blocks[int(offset_y // self.block_size):int((offset_y + (1.5 * win.get_height())) // self.block_size)]]

    def output(self, win, offset_x, offset_y, master_volume, fps) -> None:
        above_player = []

        for obj in self.triggers + self.__get_static_block_slice__(win, offset_x, offset_y) + self.dynamic_blocks + list(self.doors.values()) + self.hazards + self.enemies + self.objectives:
            if isinstance(obj, list):
                for obj_lower in obj:
                    if obj_lower is not None:
                        if obj_lower.is_blocking:
                            obj_lower.output(win, offset_x, offset_y, master_volume, fps)
                        else:
                            above_player.append(obj_lower)
            else:
                if obj.is_blocking:
                    obj.output(win, offset_x, offset_y, master_volume, fps)
                else:
                    above_player.append(obj)

        self.player.output(win, offset_x, offset_y, master_volume, fps)

        for obj in above_player:
            obj.output(win, offset_x, offset_y, master_volume, fps)

        if self.weather is not None:
            self.weather.draw(win, offset_x, offset_y)

    @staticmethod
    def build_level(level, layout, sprite_master, image_master, objects_dict, player_audios, enemy_audios, block_audios, win, controller, player_sprite, block_size) -> tuple:
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
        objectives = []
        for i in range(len(layout)):
            win.fill((0, 0, 0))
            bar = pygame.Surface((int(win.get_width() * ((i + 1) / len(layout))), 10), pygame.SRCALPHA)
            bar.fill((255, 255, 255))
            win.blit(bar, (0, win.get_height() - 12))
            display_text("Building level." + ("." if i%3 <= 1 else " ") + ("." if i%3 <= 2 else " ") + "[" + str(i + 1) + "/" + str(len(layout)) + "]", win, controller, type=False, min_pause_time=0, should_sleep=False)
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
                        case "OBJECTIVE":
                            objectives.append(Objective(level, controller, j * block_size, i * block_size, block_size, block_size, sprite_master, block_audios, sprite=data["sprite"], sound=("objective" if data.get("sound") is None else data["sound"].lower()), is_blocking=bool(data.get("is_blocking") is not None and data["is_blocking"].upper() == "TRUE"), achievement=(None if data.get("achievement") is None else data["achievement"]),  name=(element if data.get("name") is None else data["name"])))
                        case "BLOCK":
                            if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                                is_stacked = True
                            else:
                                is_stacked = False
                            block = Block(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"], is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                            blocks.append(block)
                            static_blocks[-1][-1] = block
                        case "BREAKABLEBLOCK":
                            if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                                is_stacked = True
                            else:
                                is_stacked = False
                            block = BreakableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"], coord_x2=data["coord_x2"], coord_y2=data["coord_y2"], name=(element if data.get("name") is None else data["name"]))
                            blocks.append(block)
                            static_blocks[-1][-1] = block
                        case "MOVINGBLOCK":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                            is_stacked = False
                            block = MovingBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], path=path, coord_x=data["coord_x"], coord_y=data["coord_y"], is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                            blocks.append(block)
                            dynamic_blocks.append(block)
                        case "DOOR":
                            is_stacked = True
                            block = Door(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=bool(data.get("is_locked") is not None and data["is_locked"].upper() == "TRUE"), coord_x=data["coord_x"], coord_y=data["coord_y"], name=(element if data.get("name") is None else data["name"]))
                            blocks.append(block)
                            if doors.get(j) is None:
                                doors[j] = [block]
                            else:
                                doors[j].append(block)
                        case "MOVABLEBLOCK":
                            is_stacked = False
                            block = MovableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=data["coord_x"], coord_y=data["coord_y"], name=(element if data.get("name") is None else data["name"]))
                            blocks.append(block)
                            dynamic_blocks.append(block)
                        case "HAZARD":
                            hazards.append(Hazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"], name=(element if data.get("name") is None else data["name"])))
                        case "MOVINGHAZARD":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                            is_stacked = False
                            hazards.append(MovingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"], name=(element if data.get("name") is None else data["name"])))
                        case "FALLINGHAZARD":
                            hazards.append(FallingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=data["coord_x"], coord_y=data["coord_y"], name=(element if data.get("name") is None else data["name"])))
                        case "ENEMY":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                            enemies.append(Enemy(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, path=path, hp=data["hp"], can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"])))
                        case "BOSS":
                            if data["path"].upper() == "NONE":
                                path = None
                            else:
                                path = load_path(list(map(int, data["path"].split(' '))), i, j, block_size)
                            enemies.append(Boss(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, music=(None if data.get("music") is None or data["music"].upper() == "NONE" else data["music"]), death_triggers=(None if data.get("death_triggers") is None else data["death_triggers"]), path=path, hp=data["hp"], can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"])))
                        case "TRIGGER":
                            triggers.append(Trigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, win, objects_dict, sprite_master, enemy_audios, block_audios, image_master, block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), type=TriggerType(data["type"]), input=data["input"], name=(element if data.get("name") is None else data["name"])))
                        case _:
                            pass

        player = Player(level, controller, player_start[0], player_start[1], sprite_master, player_audios, controller.difficulty, block_size, sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[0]), retro_sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[1]))

        return level_bounds, player, triggers, blocks, dynamic_blocks, doors, static_blocks, hazards, enemies, objectives
