import math
import asyncio
import pygame
import random
from Actor import MovementState
from Enemy import Enemy
from Helpers import set_property, validate_file_list


class Boss(Enemy):
    PLAYER_SPOT_RANGE = 6
    PLAYER_SPOT_COOLDOWN = 3
    VELOCITY_TARGET = 0.5

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, music=None, death_triggers=None, path=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE, sprite=None, proj_sprite=None, name="Boss"):
        super().__init__(level, controller, x, y, sprite_master, audios, difficulty, block_size, path=path, hp=hp, can_shoot=can_shoot, spot_range=spot_range, sprite=sprite, proj_sprite=proj_sprite, name=name)
        self.music = (None if music is None else validate_file_list("Music", list(music.split(' ')), "mp3"))
        self.music_is_playing = False
        self.is_animated_attack = True
        self.audio_trigger_frames.update({"WIND_UP": [0], "ATTACK_ANIM": [0], "WIND_DOWN": [0]})
        self.death_triggers = {}
        if death_triggers is not None:
            if death_triggers.get("properties") is not None:
                self.death_triggers["properties"] = death_triggers["properties"]
            if death_triggers.get("cinematics") is not None:
                self.death_triggers["cinematics"] = death_triggers["cinematics"]

    def die(self):
        if self.death_triggers.get("properties") is not None:
            for trigger in self.death_triggers["properties"]:
                set_property(self, trigger)
        if self.death_triggers.get("cinematics") is not None:
            for cinematic in self.death_triggers["cinematics"]:
                self.level.cinematics.queue(cinematic)

    async def __queue_music__(self):
        if self.music_is_playing and (self.hp <= 0 or math.dist((self.level.get_player().rect.x, self.level.get_player().rect.y), (self.rect.x, self.rect.y)) >= 2 * self.spot_range):
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            self.controller.queue_track_list()
            self.music_is_playing = False
        elif not self.music_is_playing and self.hp > 0 and math.dist((self.level.get_player().rect.x, self.level.get_player().rect.y), (self.rect.x, self.rect.y)) <= self.spot_range:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            self.controller.queue_track_list(music=self.music)
            self.music_is_playing = True

    async def __toggle_music__(self):
        await self.__queue_music__()
        pygame.event.Event(pygame.USEREVENT)

    def update_sprite(self, fps, delay=0):
        active_index = super().update_sprite(fps)
        if self.audios is not None and (self.state in [MovementState.WIND_UP, MovementState.ATTACK_ANIM, MovementState.WIND_DOWN]) and self.audio_trigger_frames.get(str(self.state)) is not None:
            audio_folder = self.name.upper().split(" ",1)[0] + "_" + str(self.state)
            if self.audios.get(audio_folder) is not None and active_index in self.audio_trigger_frames[str(self.state)]:
                self.active_audio = self.audios[audio_folder][random.randrange(len(self.audios[audio_folder]))]
                if self.active_audio_channel is not None:
                    self.active_audio_channel.stop()
                    self.active_audio_channel = None

        return active_index

    def loop(self, fps, dtime, target=VELOCITY_TARGET, drag=0, grav=0):
        asyncio.run(self.__toggle_music__())
        return super().loop(fps, dtime, target=target)
