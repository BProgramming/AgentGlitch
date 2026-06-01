from __future__ import annotations
from typing import TYPE_CHECKING
import math
import pygame
import random
from Actor import MovementState
from NonPlayer import NonPlayer
from Helpers import validate_file_list, PathPoint

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class Boss(NonPlayer):
    PLAYER_SPOT_RANGE    = 6
    PLAYER_SPOT_COOLDOWN = 3

    def __init__(
            self:            Boss,
            level:           Level,
            controller:      Controller,
            x:               float,
            y:               float,
            sprite_master:   dict,
            audios:          dict,
            difficulty:      float,
            block_size:      float,
            music:           str | None             = None,
            trigger:         str | None             = None,
            path:            list[PathPoint] | None = None,
            hp:              float                  = 100,
            show_health_bar: bool                   = True,
            can_shoot:       bool                   = False,
            spot_range:      float                  = PLAYER_SPOT_RANGE,
            sprite:          str | None             = None,
            proj_sprite:     str | None             = None,
            name:            str                    = "Boss",
    ) -> None:
        """Initialize a boss with its own music, health bar, and animated attack frames."""
        super().__init__(
            level,
            controller,
            x,
            y,
            sprite_master,
            audios,
            difficulty,
            block_size,
            path        = path,
            hp          = hp,
            can_shoot   = can_shoot,
            spot_range  = spot_range,
            sprite      = sprite,
            proj_sprite = proj_sprite,
            name        = name,
        )
        self.music:              list[str] | None    = validate_file_list("Music", list(music.split(" ")), "mp3") if music else None
        self.music_is_playing:   bool                = False
        self.is_animated_attack: bool                = True
        self.audio_trigger_frames.update({"WIND_UP": [0], "ATTACK_ANIM": [0], "WIND_DOWN": [0]})
        self.is_on_screen:       bool                = False
        self.show_health_bar:    bool                = show_health_bar
        self.trigger:            str | list[Trigger] = trigger if trigger else []

    def die(
            self: Boss,
    ) -> float:
        """Run the death handling, clear the boss health bar, and fire any death triggers."""
        dtime_offset: float = super().die()
        self.level.boss_hp_pct = 0
        if self.trigger:
            for trigger in self.trigger:
                if hasattr(trigger, 'collide'):
                    dtime_offset += trigger.collide(self.level.player)
        return dtime_offset

    def __update_onscreen_presence__(
            self: Boss,
    ) -> None:
        """Update whether the boss is considered on-screen, using distance hysteresis."""
        if self.rect and self.level.player.rect:
            if self.level.boss_hp_pct is None and math.dist((self.level.player.rect.x, self.level.player.rect.y), (self.rect.x, self.rect.y)) <= self.spot_range:
                self.is_on_screen = True
            elif math.dist((self.level.player.rect.x, self.level.player.rect.y), (self.rect.x, self.rect.y)) >= 2 * self.spot_range:
                self.is_on_screen = False
        return None

    def __update_health_bar__(
            self: Boss,
    ) -> None:
        """Publish or clear the boss's health-bar percentage based on on-screen presence."""
        if self.is_on_screen:
            self.level.boss_hp_pct = self.hp / self.max_hp
        elif self.level.boss_hp_pct is not None:
            self.level.boss_hp_pct = None
        return None

    def __queue_music__(
            self: Boss,
    ) -> None:
        """Start the boss music when active and on-screen, or fade back to level music otherwise."""
        if self.music_is_playing and (self.hp <= 0 or not self.is_on_screen):
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            self.controller.queue_track_list()
            self.music_is_playing = False
        elif not self.music_is_playing and self.hp > 0 and self.is_on_screen:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            self.controller.queue_track_list(music=self.music)
            self.music_is_playing = True
        return None

    def update_sprite(
            self: Boss,
    ) -> int:
        """Advance the sprite and trigger boss-specific attack audio on the active frame."""
        active_index = super().update_sprite()
        if self.audios is not None and (self.state in [MovementState.WIND_UP, MovementState.ATTACK_ANIM, MovementState.WIND_DOWN]) and self.audio_trigger_frames.get(str(self.state)) is not None:
            audio_folder = f'{self.name.upper().split(" ", 1)[0]}_{str(self.state)}'
            if self.audios.get(audio_folder) is not None and active_index in self.audio_trigger_frames[str(self.state)]:
                self.active_audio = self.audios[audio_folder][random.randrange(len(self.audios[audio_folder]))]
                if self.active_audio_channel is not None:
                    self.active_audio_channel.stop()
                    self.active_audio_channel = None
        return active_index

    def loop(
            self:  Boss,
            dtime: float,
    ) -> float:
        """Update on-screen state, health bar, and boss music, then run the actor loop."""
        self.__update_onscreen_presence__()
        if self.show_health_bar:
            self.__update_health_bar__()
        self.__queue_music__()
        return super().loop(dtime)
