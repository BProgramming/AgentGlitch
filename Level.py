from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

from Block import (
    Block,
    Hazard,
    FallingHazard,
)
from Cinematic import CinematicsManager
from NonPlayer import NonPlayer
from Objective import Objective
from Trigger import Trigger
from ParticleEffect import (
    ParticleEffect,
    Rain,
    Snow,
    FilmGrain,
)
from Helpers import (
    validate_file_list,
    ASSETS_FOLDER,
)
from EntityFactory import build_level

if TYPE_CHECKING:
    from Controller import Controller
    from Player import Player
    from steamworks import STEAMWORKS
    from SimpleVFX.SimpleVFX import VisualEffectsManager


class Level:
    BLOCK_SIZE = 96

    def __init__(
            self:           Level,
            name:           str,
            levels:         dict,
            meta_dict:      dict,
            objects_dict:   dict,
            sprite_master:  dict,
            image_master:   dict,
            player_audios:  dict,
            enemy_audios:   dict,
            block_audios:   dict,
            message_audios: dict,
            vfx_manager:    VisualEffectsManager,
            win:            pygame.Surface,
            controller:     Controller,
            loading_screen: pygame.Surface,
    ) -> None:
        """Build a level from its layout and metadata: entities, music, cinematics, and effects."""
        self.name         = name.upper()
        self.display_name = self.name if meta_dict[name].get("name") is None else meta_dict[name]["name"]
        self.time         = 0
        self.achievements = ({} if meta_dict[name].get("achievements") is None else meta_dict[name]["achievements"])
        self.block_size   = Level.BLOCK_SIZE if meta_dict[name].get("block_size") is None or not meta_dict[name]["block_size"].isnumeric() else int(meta_dict[name]["block_size"])
        self.purge_queue  = {"triggers": set(), "hazards": set(), "blocks": set(), "doors": set(), "enemies": set(), "objectives": set()}
        if controller.retro:
            self._retro = True
        else:
            self._retro = (False if meta_dict[name].get("retro") is None else meta_dict[name]["retro"])
        self.can_glitch             = (False if meta_dict[name].get("can_glitch") is None else meta_dict[name]["can_glitch"])
        self.visual_effects_manager = vfx_manager
        self.background             = (None if meta_dict[name].get("background") is None else meta_dict[name]["background"])
        self.foreground             = (None if meta_dict[name].get("foreground") is None else meta_dict[name]["foreground"])
        self.start_cinematic        = (None if meta_dict[name].get("start_cinematic") is None else meta_dict[name]["start_cinematic"])
        self.end_cinematic          = (None if meta_dict[name].get("end_cinematic") is None else meta_dict[name]["end_cinematic"])
        if type(self.start_cinematic) not in [list, tuple]:
            self.start_cinematic = [self.start_cinematic]
        if type(self.end_cinematic) not in [list, tuple]:
            self.end_cinematic = [self.end_cinematic]
        self.start_message = (None if meta_dict[name].get("start_message") is None else meta_dict[name]["start_message"])
        self.end_message   = (None if meta_dict[name].get("end_message") is None else meta_dict[name]["end_message"])
        if self._retro and meta_dict[name].get("retro_music") is not None:
            self.music = validate_file_list("Music", list(meta_dict[name]["retro_music"].split(" ")), "mp3")
        else:
            self.music = (None if meta_dict[name].get("music") is None else validate_file_list("Music", list(meta_dict[name]["music"].split(" ")), "mp3"))
        self.level_bounds, self._player, self.triggers, self.blocks, self.dynamic_blocks, self.doors, self.static_blocks, self.hazards, self.falling_hazards, self.enemies, self.objectives = build_level(self, levels[self.name], sprite_master, image_master, objects_dict[self.name], player_audios, enemy_audios, block_audios, message_audios, win, controller, None if meta_dict[name].get("player_sprite") is None else meta_dict[name]["player_sprite"], self.block_size, loading_screen)
        if self._retro and meta_dict[name].get("retro_cinematics") is not None:
            self.cinematics = CinematicsManager(meta_dict[name]["retro_cinematics"], controller, player_sprites=self._player.sprites)
        else:
            self.cinematics = (None if meta_dict[name].get("cinematics") is None else CinematicsManager(meta_dict[name]["cinematics"], controller, player_sprites=self._player.sprites))
        self.particle_effects: list[ParticleEffect] = []
        if meta_dict[name].get("particle_effect") is not None:
            effect = self.gen_particle_effect(meta_dict[name]["particle_effect"].upper(), win)
            if effect:
                self.particle_effects.append(effect)
        if self._retro:
            effect = self.gen_particle_effect("FILM", win)
            if effect:
                self.particle_effects.append(effect)
        if meta_dict[name].get("abilities") is not None:
            for key in meta_dict[name]["abilities"]:
                self.player.abilities[key.casefold()] = meta_dict[name]["abilities"][key]
        self._player.been_hit_this_level  = False
        self._player.been_seen_this_level = False
        self._player.deaths_this_level    = 0
        self._player.kills_this_level     = 0
        self.target_time                  = (0 if meta_dict[name].get("target_time") is None else meta_dict[name]["target_time"])
        self.default_objective            = (None if meta_dict[name].get("default_objective") is None else meta_dict[name]["default_objective"])
        self.objectives_collected         = []
        self.objectives_available         = len(self.objectives)
        self.enemies_available            = len(self.enemies)
        self.boss_hp_pct                  = None
        self.hot_swap_level               = (None if meta_dict[name].get("hot_swap_level") is None or meta_dict.get(meta_dict[name]["hot_swap_level"]) is None else Level(meta_dict[name]["hot_swap_level"], levels, meta_dict, objects_dict, sprite_master, image_master, player_audios, enemy_audios, block_audios, message_audios, vfx_manager, win, controller, loading_screen))

    @property
    def player(
            self: Level,
    ) -> Player:
        """Return the level's player."""
        return self._player

    @property
    def retro(
            self: Level,
    ) -> bool:
        """Return whether the level uses retro styling."""
        return self._retro

    def award_achievements(
            self:       Level,
            steamworks: STEAMWORKS,
    ) -> bool:
        """Evaluate and unlock any earned achievements, returning whether any were granted."""
        unlocked_achievements = []
        if self.target_time is not None and self.target_time > 0 and self.time <= self.target_time and self.achievements.get("target_time") is not None and self.achievements["target_time"] is not None:
            unlocked_achievements.append(self.achievements["target_time"])
        if 0 < self.objectives_available == len(self.objectives_collected) and self.achievements.get("all_objectives") is not None and self.achievements["all_objectives"] is not None:
            unlocked_achievements.append(self.achievements["all_objectives"])
        if self.player.kills_this_level == 0 and self.achievements.get("no_kills") is not None and self.achievements["no_kills"] is not None:
            unlocked_achievements.append(self.achievements["no_kills"])
        elif self.player.kills_this_level == self.enemies_available and self.achievements.get("all_kills") is not None and self.achievements["all_kills"] is not None:
            unlocked_achievements.append(self.achievements["all_kills"])
        if self.player.deaths_this_level == 0 and self.achievements.get("no_death") is not None and self.achievements["no_death"] is not None:
            unlocked_achievements.append(self.achievements["no_death"])
        if not self.player.been_hit_this_level and self.achievements.get("no_hit") is not None and self.achievements["no_hit"] is not None:
            unlocked_achievements.append(self.achievements["no_hit"])
        if not self.player.been_seen_this_level and self.achievements.get("no_seen") is not None and self.achievements["no_seen"] is not None:
            unlocked_achievements.append(self.achievements["no_seen"])

        if len(unlocked_achievements) > 0 and steamworks:
            for achievement in unlocked_achievements:
                if not steamworks.UserStats.GetAchievement(achievement):
                    steamworks.UserStats.SetAchievement(achievement)
            return True
        else:
            return False

    @property
    def formatted_time(
            self: Level,
    ) -> str:
        """Return the level time formatted as MM:SS.t."""
        minutes            = int(self.time // 60)
        seconds            = int(self.time - (minutes * 60))
        fractional_seconds = int((self.time - ((minutes * 60) + seconds)) * 10)
        return f'{"0" if minutes < 10 else ""}{minutes}:{"0" if seconds < 10 else ""}{seconds}.{fractional_seconds}'

    def get_recap_text(
            self: Level,
    ) -> list:
        """Return the end-of-level recap lines (time, objectives, kills, deaths, stealth)."""
        objectives_pct = (100 * len(self.objectives_collected) // self.objectives_available) if self.objectives_available > 0 else 0
        text = [f"Mission time: {self.formatted_time}.",
                f"Packets collected: {len(self.objectives_collected)} of {self.objectives_available} ({objectives_pct}%)."]
        if self.player.kills_this_level == 0:
            text.append("Nonlethal: You didn't dispatch any enemies.")
        else:
            kills_pct = (100 * self.player.kills_this_level // self.enemies_available) if self.enemies_available > 0 else 0
            text.append(f"Enemies dispatched: {self.player.kills_this_level} of {self.enemies_available} ({kills_pct} %).")
        if self.player.deaths_this_level == 0:
            text.append("Survivor: You never died.")
        else:
            text.append(f"Deaths: {self.player.deaths_this_level}.")
        if not self.player.been_hit_this_level:
            text.append("Untouchable: You never got hit.")
        if not self.player.been_seen_this_level:
            text.append("Shadow: You were never even seen!")
        return text

    @property
    def entities(
            self: Level,
    ) -> list:
        """Return all level entities in draw/update order."""
        return [self.player] + self.triggers + self.blocks + self.hazards + self.enemies + self.objectives

    def get_entities_in_range(
            self:            Level,
            point:           tuple[float, float],
            dist_x:          tuple[int, int] = (1, 1),
            dist_y:          tuple[int, int] = (1, 1),
            blocks_only:     bool            = False,
            include_doors:   bool            = True,
            include_hazards: bool            = False,
    ) -> list:
        """Return entities near a point, filtered by the blocks/doors/hazards options."""
        x = int(point[0] / self.block_size)
        y = int(point[1] / self.block_size)
        # the sum() below flattens a 2D slice into a 1D list by concatenating rows onto an empty list
        in_range = [block for block in sum([row[max(x - (dist_x[0] - 1), 0):min(x + dist_x[1] + 1, len(row))] for row in self.static_blocks[max(y - (dist_y[0] - 1), 0):min(y + dist_y[1] + 1, len(self.static_blocks))]], []) if block is not None] # noqa

        if include_doors:
            for i in range(dist_x[0] - 1, dist_x[1] + 1):
                if self.doors.get(x + i) is not None:
                    in_range += self.doors[x + i]

        if blocks_only and include_hazards:
            for ent in self.hazards:
                if ent.rect.x - (self.block_size * dist_x[0]) <= point[0] <= ent.rect.x + (self.block_size * dist_x[1]) and ent.rect.y - (self.block_size * dist_y[0]) <= point[1] <= ent.rect.y + (self.block_size * dist_y[1]):
                    in_range.append(ent)

        if not blocks_only:
            for ent in self.triggers + self.dynamic_blocks + self.hazards + self.enemies + self.objectives:
                if ent.rect.x - (self.block_size * dist_x[0]) <= point[0] <= ent.rect.x + (self.block_size * dist_x[1]) and ent.rect.y - (self.block_size * dist_y[0]) <= point[1] <= ent.rect.y + (self.block_size * dist_y[1]):
                    in_range.append(ent)

        return in_range

    def queue_purge(
            self: Level,
            ent:  object,
    ) -> None:
        """Queue an entity for removal in the appropriate purge category."""
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
        return None

    def purge(
            self: Level,
    ) -> None:
        """Remove all queued entities from their lists and clear the purge queues."""
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
            self.blocks         = [ent for ent in self.blocks if ent not in self.purge_queue["blocks"]]
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
        return None

    # NOTE: weather with lots of particles + lots of enemies + bullets will decrease the frame rate
    def gen_particle_effect(
            self: Level,
            name: str,
            win:  pygame.Surface,
    ) -> ParticleEffect | None:
        """Construct the particle effect matching a name (rain, snow, or film grain)."""
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

    def gen_image(
            self: Level,
    ) -> None:
        """Render the whole level to an image file (debug utility)."""
        img = pygame.Surface((self.level_bounds[1][0], self.level_bounds[1][1]), pygame.SRCALPHA)
        for ent in self.entities:
            img.blit(ent.sprite, (ent.rect.x, ent.rect.y))
        pygame.image.save(img, str(ASSETS_FOLDER / "Misc" / (self.name + ".png")))
        return None

    def gen_background(
            self: Level,
    ) -> None:
        """Render a schematic background image of the level's blocks and hazards (debug utility)."""
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
        pygame.image.save(img, str(ASSETS_FOLDER / "Misc" / (self.name + "_bg.png")))
        return None

    def __get_static_block_slice__(
            self:     Level,
            win:      pygame.Surface,
            offset_x: float,
            offset_y: float,
    ) -> list:
        """Return the slice of static blocks visible within 1.5 screens of the camera."""
        return [row[int(offset_x // self.block_size):int((offset_x + (1.5 * win.get_width())) // self.block_size)] for row in self.static_blocks[int(offset_y // self.block_size):int((offset_y + (1.5 * win.get_height())) // self.block_size)]]

    def draw(
            self:          Level,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float],
    ) -> None:
        """Draw the level: effects, blocks, hazards, objectives, enemies, player, and overlays."""
        self.visual_effects_manager.draw(win, (offset_x, offset_y))

        above_player = []

        for ent in self.triggers + self.__get_static_block_slice__(win, offset_x, offset_y) + self.dynamic_blocks + list(self.doors.values()) + self.hazards + self.objectives:
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

        for ent in self.enemies:
            ent.draw(win, offset_x, offset_y, master_volume)

        self.player.draw(win, offset_x, offset_y, master_volume)

        for ent in above_player:
            ent.draw(win, offset_x, offset_y, master_volume)

        for effect in self.particle_effects:
            effect.draw(win, offset_x, offset_y, master_volume)
        return None
