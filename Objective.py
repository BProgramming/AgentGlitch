from __future__ import annotations
from typing import TYPE_CHECKING
import math
import random
import time
import pygame
from Entity import Entity
from Helpers import (
    handle_exception,
    set_sound_source,
    load_sprite_sheets,
    ASSETS_FOLDER,
    image_to_retro,
)
from Trigger import Trigger

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level

class Objective(Entity):
    if not (ASSETS_FOLDER / "Icons" / "Pointer" / "pointer.png").is_file():
        handle_exception(f"File {FileNotFoundError((ASSETS_FOLDER / 'Icons' / 'Pointer' / 'pointer.png').resolve())} not found.")
    else:
        POINTER_SPRITE: pygame.Surface = pygame.transform.scale2x(pygame.image.load(ASSETS_FOLDER / "Icons" / "Pointer" / "pointer.png").convert_alpha())
        if (ASSETS_FOLDER / "Icons" / "Pointer" / "pointer_retro.png").is_file():
            POINTER_SPRITE_RETRO: pygame.Surface = pygame.transform.scale2x(pygame.image.load(ASSETS_FOLDER / "Icons" / "Pointer" / "pointer_retro.png").convert_alpha())
        else:
            POINTER_SPRITE_RETRO: pygame.Surface = image_to_retro(POINTER_SPRITE)
        POINTER_SPRITE_HEIGHT: int = POINTER_SPRITE.get_height()
        POINTER_SPRITE_WIDTH:  int = POINTER_SPRITE.get_width()
    NICE_BORDER_DISTANCE = 64

    def __init__(
            self:          Objective,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            width:         float,
            height:        float,
            sprite_master: dict[str, dict[str, list[pygame.Surface]]],
            audios:        dict[str, list[pygame.mixer.Sound]],
            is_active:     bool       = False,
            sprite:        str | None = None,
            sound:         str        = "objective",
            text:          str | None = None,
            trigger:       str | None = None,
            is_blocking:   bool       = False,
            achievement:   str | None = None,
            name:          str        = "Objective",
    ) -> None:
        """Initialize a collectible objective with optional animated sprite, sound, and trigger."""
        super().__init__(level, controller, x, y, width, height, is_blocking = is_blocking, name = name)

        self.sprites:         list[pygame.Surface] | None            = None
        if sprite:
            avail_sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction = False, retro = self.level.retro)
            if self.level.retro and avail_sprites.get("ANIMATE_RETRO"):
                self.sprites = avail_sprites["ANIMATE_RETRO"]
            else:
                self.sprites = avail_sprites["ANIMATE"]
        self.animation_count: int                                    = 0
        self.sprite:          pygame.Surface | None                  = None
        if self.sprites:
            self.update_sprite()
            self.update_geo()
        self.audios:          dict[str, list[pygame.mixer.Sound]]    = audios
        self.sound:           str | None                             = sound
        self.text:            str | None                             = text
        self.trigger:         str | list[Trigger] | None             = trigger
        self.achievement:     str | None                             = achievement
        self.is_active:       bool                                   = is_active
        self.pointer:         pygame.Surface                         = (Objective.POINTER_SPRITE_RETRO if self.level.retro else Objective.POINTER_SPRITE)
        self.pointer_offset:  tuple[float, tuple[int, float]] | None = ((self.rect.width - Objective.POINTER_SPRITE_WIDTH) / 2, (-(Objective.POINTER_SPRITE_HEIGHT + 2), -(self.rect.height - Objective.POINTER_SPRITE_HEIGHT / 2))) if self.rect else None

    def collide(
            self: Objective,
            ent:  Entity,
    ) -> bool:
        """Objectives never block movement."""
        return False

    def get_hit(
            self: Objective,
            ent:  Entity,
    ) -> float:
        """Collect the objective if active, award any achievement, and return the frame-time offset."""
        if self.is_active:
            start          = time.perf_counter()
            self.is_active = False
            self.die()
            if self.sound:
                self.play_sound(self.sound)

            if self.achievement is not None and self.controller.steamworks is not None and not self.controller.steamworks.UserStats.GetAchievement(self.achievement):
                self.controller.steamworks.UserStats.SetAchievement(self.achievement)
                self.controller.should_store_steam_stats = True

            dtime_offset: float = time.perf_counter() - start
            return dtime_offset + self.__collect__()
        else:
            return 0.0

    def save(
            self: Objective,
    ) -> dict:
        """Return a serializable dict of the objective's persistent state."""
        return super().save()

    def load(
            self: Objective,
            ent:  dict,
    ) -> None:
        """Restore the objective's state, collecting and purging it if already taken."""
        self.hp = ent["hp"]
        if self.hp <= 0:
            self.__collect__()
            self.level.queue_purge(self)
        return None

    def __collect__(
            self: Objective,
    ) -> float:
        """Record the objective as collected and fire its trigger once all of its group are gone."""
        start = time.perf_counter()
        self.level.objectives_collected.append(self)
        alive = []
        for objective in self.level.objectives:
            if objective.hp > 0 and objective.name.casefold().split(" ")[0] == self.name.casefold().split(" ")[0]:
                alive.append(objective)
        dtime_offset: float = time.perf_counter() - start
        if len(alive) == 0:
            self.controller.activate_objective(None, True, popup=False)
            if self.trigger:
                for trigger in self.trigger:
                    if isinstance(trigger, Trigger):
                        dtime_offset += trigger.collide(self.level.player)
        return dtime_offset

    def play_sound(
            self: Objective,
            name: str,
    ) -> None:
        """Play a named sound effect positioned relative to the player."""
        if self.sound is not None and self.audios.get(name.upper()) is not None:
            active_audio_channel = pygame.mixer.find_channel(force=True)
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[name.upper()][random.randrange(len(self.audios[name.upper()]))])
                set_sound_source(self.rect, self.level.player.rect, self.controller.master_volume["non-player"], active_audio_channel)
        return None

    def update_sprite(
            self: Objective,
    ) -> int:
        """Advance the objective's animation and return the active frame index."""
        if self.sprites:
            active_index = math.floor((self.animation_count / Objective.ANIMATION_DELAY) % len(self.sprites))
            if active_index >= len(self.sprites):
                active_index         = 0
                self.animation_count = 0
            self.sprite = self.sprites[active_index]
            return active_index
        return 0

    def update_geo(
            self: Objective,
    ) -> None:
        """Recompute the objective's rect and collision mask from its current sprite."""
        if self.rect and self.sprite:
            self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
            self.mask = pygame.mask.from_surface(self.sprite)
        return None

    def loop(
            self:  Objective,
            dtime: float,
    ) -> float:
        """Advance the objective's animation and run the base entity loop."""
        self.animation_count += dtime
        return super().loop(dtime)

    def draw(
            self:          Objective,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float],
    ) -> None:
        """Draw the objective and, when active, an on-screen or edge-clamped pointer toward it."""
        if self.rect:
            adj_x = self.rect.x - offset_x
            adj_y = self.rect.y - offset_y
            if self.sprite and -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
                self.update_sprite()
                self.update_geo()
                win.blit(self.sprite, (adj_x, adj_y))

            if self.is_active and self.pointer_offset :
                if self.NICE_BORDER_DISTANCE - self.rect.width < adj_x + self.pointer_offset[0] <= (win.get_width() - Objective.POINTER_SPRITE_WIDTH - self.NICE_BORDER_DISTANCE) and self.NICE_BORDER_DISTANCE - self.rect.height < adj_y + self.pointer_offset[1][1] <= (win.get_height() - Objective.POINTER_SPRITE_HEIGHT - self.NICE_BORDER_DISTANCE):
                    win.blit(self.pointer, (adj_x + self.pointer_offset[0], adj_y + self.pointer_offset[1][0]))
                elif self.level.player.rect:
                    if adj_x < self.NICE_BORDER_DISTANCE:
                        pointer_x = self.NICE_BORDER_DISTANCE
                    elif adj_x > win.get_width() - (self.NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_WIDTH):
                        pointer_x = win.get_width() - (self.NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_WIDTH)
                    else:
                        pointer_x = adj_x + self.pointer_offset[0]

                    if adj_y < self.NICE_BORDER_DISTANCE:
                        pointer_y = self.NICE_BORDER_DISTANCE
                    elif adj_y > win.get_height() - (self.NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_HEIGHT):
                        pointer_y = win.get_height() - (self.NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_HEIGHT)
                    else:
                        pointer_y = adj_y + self.pointer_offset[1][1]

                    rotation = math.degrees(math.atan2(self.rect.x - self.level.player.rect.x, self.rect.y - self.level.player.rect.y))

                    win.blit(pygame.transform.rotate(self.pointer, rotation), (pointer_x, pointer_y))
        return None
