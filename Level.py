from os.path import join
from Block import Block, BreakableBlock, MovingBlock, MovableBlock, Hazard, MovingHazard, Door, FallingHazard
from Boss import Boss
from Cinematics import CinematicsManager
from Player import Player
from NonPlayer import NonPlayer
from Objective import Objective
from Trigger import Trigger, TriggerType
from ParticleEffect import *
from Helpers import load_path, validate_file_list, display_text, ASSETS_FOLDER, NORMAL_WHITE, RETRO_WHITE


class Level:
    BLOCK_SIZE = 96

    def __init__(self, name, levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, block_audios, message_audios, vfx_manager, win, controller, loading_screen):
        self.name = name.upper()
        self.display_name = self.name if meta_dict[name].get("name") is None else meta_dict[name]["name"]
        self.time = 0
        self.achievements = ({} if meta_dict[name].get("achievements") is None else meta_dict[name]["achievements"])
        self.block_size = Level.BLOCK_SIZE if meta_dict[name].get("block_size") is None or not meta_dict[name]["block_size"].isnumeric() else int(meta_dict[name]["block_size"])
        self.purge_queue = {"triggers": set(), "hazards": set(), "blocks": set(), "doors": set(), "enemies": set(), "objectives": set()}
        if controller.retro:
            self._retro = True
        else:
            self._retro = (False if meta_dict[name].get("retro") is None else bool(meta_dict[name]["retro"].upper() == "TRUE"))
        self.can_glitch = (False if meta_dict[name].get("can_glitch") is None else bool(meta_dict[name]["can_glitch"].upper() == "TRUE"))
        self.visual_effects_manager = vfx_manager
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
        if self._retro and meta_dict[name].get("retro_music") is not None:
            self.music = validate_file_list("Music", list(meta_dict[name]["retro_music"].split(' ')), "mp3")
        else:
            self.music = (None if meta_dict[name].get("music") is None else validate_file_list("Music", list(meta_dict[name]["music"].split(' ')), "mp3"))
        if self._retro and meta_dict[name].get("retro_cinematics") is not None:
            self.cinematics = CinematicsManager(meta_dict[name]["retro_cinematics"], controller)
        else:
            self.cinematics = (None if meta_dict[name].get("cinematics") is None else CinematicsManager(meta_dict[name]["cinematics"], controller))
        self.level_bounds, self._player, self.triggers, self.blocks, self.dynamic_blocks, self.doors, self.static_blocks, self.hazards, self.falling_hazards, self.enemies, self.objectives = self.build_level(self, levels[self.name], sprite_master, image_master, objects_dict[self.name], player_audios, enemy_audios, block_audios, message_audios, win, controller, None if meta_dict[name].get("player_sprite") is None or meta_dict[name]["player_sprite"].upper() == "NONE" else meta_dict[name]["player_sprite"], self.block_size, loading_screen)
        self.particle_effects: list[ParticleEffect] = []
        if meta_dict[name].get("particle_effect") is not None:
            self.particle_effects.append(self.gen_particle_effect(meta_dict[name]["particle_effect"].upper(), win))
        if self._retro:
            self.particle_effects.append(self.gen_particle_effect("FILM", win))
        if meta_dict[name].get("abilities") is not None:
            self.set_player_abilities(meta_dict[name]["abilities"])
        self._player.been_hit_this_level = False
        self._player.been_seen_this_level = False
        self._player.deaths_this_level = 0
        self._player.kills_this_level = 0
        self.target_time = (0 if meta_dict[name].get("target_time") is None else meta_dict[name]["target_time"])
        self.objectives_collected = []
        self.objectives_available = len(self.objectives)
        self.enemies_available = len(self.enemies)
        self.boss_hp_pct = None
        self.hot_swap_level = (None if meta_dict[name].get("hot_swap_level") is None or meta_dict.get(meta_dict[name]["hot_swap_level"]) is None else Level(meta_dict[name]["hot_swap_level"], levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, block_audios, message_audios, vfx_manager, win, controller, loading_screen))

    @property
    def player(self) -> Player:
        return self._player

    @property
    def retro(self) -> bool:
        return self._retro

    def award_achievements(self, steamworks):
        unlocked_achievements = []
        if self.target_time is not None and self.target_time > 0 and self.get_formatted_time() <= self.target_time and self.achievements.get("target_time") is not None and self.achievements["target_time"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["target_time"])
        if 0 < self.objectives_available == len(self.objectives_collected) and self.achievements.get("all_objectives") is not None and self.achievements["all_objectives"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["all_objectives"])
        if self.player.kills_this_level == 0 and self.achievements.get("no_kills") is not None and self.achievements["no_kills"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["no_kills"])
        elif self.player.kills_this_level == self.enemies_available and self.achievements.get("all_kills") is not None and self.achievements["all_kills"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["all_kills"])
        if self.player.deaths_this_level == 0 and self.achievements.get("no_death") is not None and self.achievements["no_death"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["no_death"])
        if not self.player.been_hit_this_level and self.achievements.get("no_hit") is not None and self.achievements["no_hit"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["no_hit"])
        if not self.player.been_seen_this_level and self.achievements.get("no_seen") is not None and self.achievements["no_seen"].upper() != "NONE":
            unlocked_achievements.append(self.achievements["no_seen"])

        if len(unlocked_achievements) > 0 and steamworks is not None:
            for achievement in unlocked_achievements:
                if not steamworks.UserStats.GetAchievement(achievement):
                    steamworks.UserStats.SetAchievement(achievement)
            return True
        else:
            return False

    def get_formatted_time(self) -> str:
        minutes = self.time // 60000
        seconds = (self.time - (minutes * 60000)) // 1000
        milliseconds = self.time - ((minutes * 60000) + (seconds * 1000))
        return f'{"0" if minutes < 10 else ""}{minutes}:{"0" if seconds < 10 else ""}{seconds}.{"0" if milliseconds < 100 else ""}{"0" if milliseconds < 10 else ""}{milliseconds}'

    def get_recap_text(self) -> list:
        text = [f'Mission time: {self.get_formatted_time()}.',
                f'Packets collected: {len(self.objectives_collected)} of {self.objectives_available} ({100 * len(self.objectives_collected) // self.objectives_available}%).']
        if self.player.kills_this_level == 0:
            text.append('Nonlethal: You didn\'t dispatch any enemies.')
        else:
            text.append(f'Enemies dispatched: {self.player.kills_this_level} of {self.enemies_available} ({100 * self.player.kills_this_level // self.enemies_available} %).')
        if self.player.deaths_this_level == 0:
            text.append('Survivor: You never died.')
        else:
            text.append(f'Deaths: {self.player.deaths_this_level}.')
        if not self.player.been_hit_this_level:
            text.append('Untouchable: You never got hit.')
        if not self.player.been_seen_this_level:
            text.append('Shadow: You were never even seen!')
        return text

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

    def get_entities(self) -> list:
        return self.triggers + self.blocks + self.hazards + self.enemies + self.objectives

    def get_entities_in_range(self, point, dist_x=(1, 1), dist_y=(1, 1), blocks_only=False, include_doors=True) -> list:
        x = int(point[0] / self.block_size)
        y = int(point[1] / self.block_size)
        # this sum thing below is a hack to turn a 2D list into a 1D list since it applies the + operator to the second (optional) [] argument (e.g. an empty list), thereby concatenating all the elements
        in_range = [block for block in sum([row[max(x - (dist_x[0] - 1), 0):min(x + dist_x[1] + 1, len(row))] for row in self.static_blocks[max(y - (dist_y[0] - 1), 0):min(y + dist_y[1] + 1, len(self.static_blocks))]], []) if block is not None]

        if include_doors:
            for i in range(dist_x[0] - 1, dist_x[1] + 1):
                if self.doors.get(x + i) is not None:
                    in_range += self.doors[x + i]

        if not blocks_only:
            for ent in self.triggers + self.dynamic_blocks + self.hazards + self.enemies + self.objectives:
                if ent.rect.x - (self.block_size * dist_x[0]) <= point[0] <= ent.rect.x + (self.block_size * dist_x[1]) and ent.rect.y - (self.block_size * dist_y[0]) <= point[1] <= ent.rect.y + (self.block_size * dist_y[1]):
                    in_range.append(ent)

        return in_range

    def queue_purge(self, ent) -> None:
        if isinstance(ent, Trigger):
            self.purge_queue["triggers"].add(ent)
        if isinstance(ent, Hazard):
            self.purge_queue["hazards"].add(ent)
        elif isinstance(ent, Block):
            self.purge_queue["blocks"].add(ent)
        elif isinstance(ent, NonPlayer):
            self.purge_queue["enemies"].add(ent)
        elif isinstance(ent, Objective):
            self.purge_queue["objectives"].add(ent)

    def purge(self) -> None:
        if bool(self.purge_queue["triggers"]):
            self.triggers = [ent for ent in self.triggers if ent not in self.purge_queue["triggers"]]
            self.purge_queue["triggers"].clear()
        if bool(self.purge_queue["hazards"]):
            self.hazards = [ent for ent in self.hazards if ent not in self.purge_queue["hazards"]]
            for ent in self.purge_queue["hazards"]:
                if isinstance(ent, FallingHazard):
                    for x in list(self.falling_hazards.keys()):
                        for falling_hazard in self.falling_hazards[x]:
                            if falling_hazard == ent:
                                if len(self.falling_hazards[x]) == 1:
                                    self.falling_hazards.pop(x)
                                else:
                                    self.falling_hazards[x].remove(falling_hazard)
            self.purge_queue["hazards"].clear()
        if bool(self.purge_queue["blocks"]):
            self.blocks = [ent for ent in self.blocks if ent not in self.purge_queue["blocks"]]
            self.dynamic_blocks = [ent for ent in self.dynamic_blocks if ent not in self.purge_queue["blocks"]]
            for i in range(len(self.static_blocks)):
                self.static_blocks[i] = [ent for ent in self.static_blocks[i] if ent not in self.purge_queue["blocks"]]
            self.purge_queue["blocks"].clear()
        if bool(self.purge_queue["enemies"]):
            self.enemies = [ent for ent in self.enemies if ent not in self.purge_queue["enemies"]]
            self.purge_queue["enemies"].clear()
        if bool(self.purge_queue["objectives"]):
            self.objectives = [ent for ent in self.objectives if ent not in self.purge_queue["objectives"]]
            self.purge_queue["objectives"].clear()

    #NOTE: having weather with lots of particles + lots of enemies + bullets will decrease the frame rate
    def gen_particle_effect(self, name, win) -> ParticleEffect | None:
        if name is None:
            return None
        else:
            if name == "RAIN":
                return Rain(self)
            elif name == "SNOW":
                return Snow(self)
            elif "FILM" in name or "GRAIN" in name:
                return FilmGrain(self, win)
            else:
                return None

    def gen_image(self) -> None:
        img = pygame.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        for ent in self.get_entities() + [self.player]:
            img.blit(ent.sprite, (ent.rect.x, ent.rect.y))
        pygame.image.save(img, join(ASSETS_FOLDER, "Misc", self.name + ".png"))

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
        pygame.image.save(img, join(ASSETS_FOLDER, "Misc", self.name + "_bg.png"))

    def __get_static_block_slice__(self, win, offset_x, offset_y) -> list:
        return [row[int(offset_x // self.block_size):int((offset_x + (1.5 * win.get_width())) // self.block_size)] for row in self.static_blocks[int(offset_y // self.block_size):int((offset_y + (1.5 * win.get_height())) // self.block_size)]]

    def draw(self, win, offset_x, offset_y, master_volume) -> None:
        self.visual_effects_manager.draw(win, (offset_x, offset_y))

        above_player = []

        for ent in self.triggers + self.__get_static_block_slice__(win, offset_x, offset_y) + self.dynamic_blocks + list(self.doors.values()) + self.hazards + self.enemies + self.objectives:
            if isinstance(ent, list):
                for ent_lower in ent:
                    if ent_lower is not None:
                        if ent_lower.is_blocking:
                            ent_lower.draw(win, offset_x, offset_y, master_volume)
                        else:
                            above_player.append(ent_lower)
            else:
                if ent.is_blocking:
                    ent.draw(win, offset_x, offset_y, master_volume)
                else:
                    above_player.append(ent)

        self.player.draw(win, offset_x, offset_y, master_volume)

        for ent in above_player:
            ent.draw(win, offset_x, offset_y, master_volume)

        for effect in self.particle_effects:
            effect.draw(win, offset_x, offset_y, master_volume)

    @staticmethod
    def build_level(level, layout, sprite_master, image_master, objects_dict, player_audios, enemy_audios, block_audios, message_audios, win, controller, player_sprite, block_size, loading_screen) -> tuple:
        width = len(layout[-1]) * block_size
        height = len(layout) * block_size
        level_bounds = ((0, 0), (width, height))
        player_start = (0, 0)

        blocks = []
        doors = {}
        dynamic_blocks = []
        static_blocks = []
        triggers = []
        enemies = []
        hazards = []
        falling_hazards = {}
        objectives = []
        bar_colour = RETRO_WHITE if level.retro else NORMAL_WHITE

        def __convert_coords__(coord: int) -> int:
            if coord < block_size:
                return coord * block_size
            else:
                return coord

        for i in range(len(layout)):
            win.fill((0, 0, 0))
            bar = pygame.Surface((int(win.get_width() * ((i + 1) / len(layout))), 10), pygame.SRCALPHA)
            bar.fill(bar_colour)
            win.blit(bar, (0, win.get_height() - 12))
            pct = 100 * (i + 1)//len(layout)
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text(f'Building level... {" " if pct < 100 else ""}{" " if pct < 10 else ""}{pct}%', controller, min_pause_time=0, should_sleep=False, retro=level.retro)
            static_blocks.append([])
            for j in range(len(layout[i])):
                static_blocks[-1].append(None)
                for element in [str(i) for i in layout[i][j].split(' ')]:
                    if len(element) > 0 and objects_dict.get(element) is not None:
                        entry = objects_dict[element]
                        data = entry["data"]
                        match entry["type"].upper():
                            case "PLAYER":
                                player_start = ((j * block_size), (i * block_size))
                            case "OBJECTIVE":
                                objectives.append(Objective(level, controller, j * block_size, i * block_size, block_size, block_size, sprite_master, block_audios, is_active=bool(data.get("is_active") is not None and data["is_active"].upper() == "TRUE"), sprite=(None if data.get("sprite") is None else data["sprite"]), sound=("objective" if data.get("sound") is None else data["sound"].lower()), is_blocking=bool(data.get("is_blocking") is not None and data["is_blocking"].upper() == "TRUE"), achievement=(None if data.get("achievement") is None else data["achievement"]),  name=(element if data.get("name") is None else data["name"])))
                            case "BLOCK":
                                if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                                    is_stacked = True
                                else:
                                    is_stacked = False
                                block = Block(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                                blocks.append(block)
                                static_blocks[-1][-1] = block
                            case "BREAKABLEBLOCK":
                                if i > 0 and len(str(layout[i - 1][j])) > 0 and objects_dict.get(str(layout[i - 1][j])) is not None and objects_dict[str(layout[i - 1][j])]["type"] in ["Block"]:
                                    is_stacked = True
                                else:
                                    is_stacked = False
                                block = BreakableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), coord_x2=__convert_coords__(data["coord_x2"]), coord_y2=__convert_coords__(data["coord_y2"]), name=(element if data.get("name") is None else data["name"]))
                                blocks.append(block)
                                static_blocks[-1][-1] = block
                            case "MOVINGBLOCK":
                                if data["path"].upper() == "NONE":
                                    path = None
                                else:
                                    path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                                is_stacked = False
                                block = MovingBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, hold_for_collision=(False if data.get("hold_for_collision") is None or data["hold_for_collision"].upper() != "TRUE" else True), speed=data["speed"], path=path, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=bool(data.get("is_blocking") is None or data["is_blocking"].upper() == "TRUE"), name=(element if data.get("name") is None else data["name"]))
                                blocks.append(block)
                                dynamic_blocks.append(block)
                            case "DOOR":
                                is_stacked = True
                                block = Door(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=bool(data.get("is_locked") is not None and data["is_locked"].upper() == "TRUE"), coord_x=(0 if data.get("coord_x") is None else __convert_coords__(data["coord_x"])), coord_y=(0 if data.get("coord_y") is None else __convert_coords__(data["coord_y"])), locked_coord_x=(None if data.get("locked_coord_x") is None else __convert_coords__(data["locked_coord_x"])), locked_coord_y=(None if data.get("locked_coord_y") is None else __convert_coords__(data["locked_coord_y"])), unlocked_coord_x=(None if data.get("unlocked_coord_x") is None else __convert_coords__(data["unlocked_coord_x"])), unlocked_coord_y=(None if data.get("unlocked_coord_y") is None else __convert_coords__(data["unlocked_coord_y"])), name=(element if data.get("name") is None else data["name"]))
                                blocks.append(block)
                                if doors.get(j) is None:
                                    doors[j] = [block]
                                else:
                                    doors[j].append(block)
                            case "MOVABLEBLOCK":
                                is_stacked = False
                                block = MovableBlock(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                                blocks.append(block)
                                dynamic_blocks.append(block)
                            case "HAZARD":
                                hazards.append(Hazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"])))
                            case "MOVINGHAZARD":
                                if data["path"].upper() == "NONE":
                                    path = None
                                else:
                                    path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                                is_stacked = False
                                hazards.append(MovingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"])))
                            case "FALLINGHAZARD":
                                falling_hazard = FallingHazard(level, controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                                hazards.append(falling_hazard)
                                if falling_hazards.get(j) is None:
                                    falling_hazards[j] = [falling_hazard]
                                else:
                                    falling_hazards[j].append(falling_hazard)
                            case "ENEMY":
                                if data["path"].upper() == "NONE":
                                    path = None
                                else:
                                    path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                                enemies.append(NonPlayer(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, path=path, kill_at_end=bool(data.get("kill_at_end") is not None and data["kill_at_end"].upper() == "TRUE"), is_hostile=bool(data.get("is_hostile") is None or data["is_hostile"].upper() != "FALSE"), collision_message=(None if data.get("collision_message") is None else data["collision_message"]), hp=data["hp"], can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"])))
                            case "BOSS":
                                if data["path"].upper() == "NONE":
                                    path = None
                                else:
                                    path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                                enemies.append(Boss(level, controller, j * block_size, i * block_size, sprite_master, enemy_audios, controller.difficulty, block_size, music=(None if data.get("music") is None or data["music"].upper() == "NONE" else data["music"]), death_triggers=(None if data.get("death_triggers") is None else data["death_triggers"]), path=path, hp=data["hp"], show_health_bar=(True if data.get("show_health_bar") is None or data["show_health_bar"].upper() != "FALSE" else False), can_shoot=bool(data.get("can_shoot") is not None and data["can_shoot"].upper() == "TRUE"), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None or data["proj_sprite"].upper() == "NONE" else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"])))
                            case "TRIGGER":
                                triggers.append(Trigger(level, controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, win, objects_dict, sprite_master, enemy_audios, block_audios, message_audios, image_master, block_size, fire_once=bool(data.get("fire_once") is not None and data["fire_once"].upper() == "TRUE"), type=(TriggerType(data["type"]) if isinstance(data["type"], int) else TriggerType.convert_string(data["type"])), input=(None if data.get("input") is None else data["input"]), name=(element if data.get("name") is None else data["name"])))
                            case _:
                                pass

        player = Player(level, controller, player_start[0], player_start[1], sprite_master, player_audios, controller.difficulty, block_size, sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[0]), retro_sprite=(player_sprite if player_sprite is not None else controller.player_sprite_selected[1]))

        return level_bounds, player, triggers, blocks, dynamic_blocks, doors, static_blocks, hazards, falling_hazards, enemies, objectives
