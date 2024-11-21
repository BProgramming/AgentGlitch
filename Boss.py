import math
import asyncio
import pygame
from Enemy import Enemy
from Helpers import validate_file_list


class Boss(Enemy):
    PLAYER_SPOT_RANGE = 480
    PLAYER_SPOT_COOLDOWN = 2

    def __init__(self, level, x, y, sprite_master, audios, difficulty, block_size, music=None, path=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE, sprite=None, proj_sprite=None, name="Boss"):
        super().__init__(level, x, y, sprite_master, audios, difficulty, block_size, path=path, hp=hp, can_shoot=can_shoot, spot_range=spot_range, sprite=sprite, proj_sprite=proj_sprite, name=name)
        self.music = (None if music is None else validate_file_list("Music", list(music.split(' ')), "mp3"))
        self.music_is_playing = False
        self.is_animated_attack = True

    async def queue_music(self, controller):
        if self.music_is_playing and math.dist((self.level.get_player().rect.x, self.level.get_player().rect.y), (self.rect.x, self.rect.y)) >= 2 * self.spot_range:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            controller.queue_track_list()
            self.music_is_playing = False
        elif not self.music_is_playing and math.dist((self.level.get_player().rect.x, self.level.get_player().rect.y), (self.rect.x, self.rect.y)) <= self.spot_range:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            controller.queue_track_list(music=self.music)
            self.music_is_playing = True

    async def toggle_music(self, controller):
        await self.queue_music(controller)
        pygame.event.Event(pygame.USEREVENT)

    def loop(self, fps, dtime, controller):
        asyncio.run(self.toggle_music(controller))
        super().loop(fps, dtime)
