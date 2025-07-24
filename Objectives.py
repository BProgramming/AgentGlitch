import math
import random
import pygame
from os.path import join, isfile
from Object import Object
from Helpers import handle_exception, set_sound_source, load_sprite_sheets


class Objective(Object):
    ANIMATION_DELAY = 0.3

    def __init__(self, level, controller, x, y, width, height, sprite_master, audios, sprite=None, sound="objective", is_blocking=False, achievement=None, name="Objective"):
        super().__init__(level, controller, x, y, width, height, is_blocking=is_blocking, name=name)
        if sprite is not None:
            self.sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, grayscale=self.level.grayscale)["ANIMATE"]
        else:
            self.sprites = [self.sprite]
        self.animation_count = 0
        self.sprite = None
        self.update_sprite(1)
        self.update_geo()
        self.audios = audios
        self.sound = sound
        self.achievement = achievement

    def collide(self, obj) -> bool:
        return False

    def get_hit(self, obj, cd=0) -> None:
        self.hp = 0
        self.play_sound(self.sound)
        self.__collect__()
        if self.achievement is not None and self.controller.steamworks is not None and not self.controller.steamworks.UserStats.GetAchievement(self.achievement):
            self.controller.steamworks.UserStats.SetAchievement(self.achievement)
            self.controller.should_store_steam_stats = True

    def save(self) -> dict:
        return super().save()

    def load(self, obj) -> None:
        self.hp = obj["hp"]
        if self.hp <= 0:
            self.__collect__()
            self.level.queue_purge(self)

    def __collect__(self) -> None:
        self.level.objectives_collected.append(self)

    def play_sound(self, name) -> None:
        if self.audios.get(name.upper()) is not None:
            active_audio_channel = pygame.mixer.find_channel()
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[name.upper()][random.randrange(len(self.audios[name.upper()]))])
                set_sound_source(self.rect, self.level.get_player().rect, self.controller.master_volume["non-player"], active_audio_channel)

    def update_sprite(self, fps, delay=ANIMATION_DELAY) -> int:
        active_index = math.floor((self.animation_count // (1000 // (fps * delay))) % len(self.sprites))
        if active_index >= len(self.sprites):
            active_index = 0
            self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def update_geo(self) -> None:
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def loop(self, fps, dtime) -> None:
        self.animation_count += dtime
        super().loop(fps, dtime)

    def output(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            self.update_sprite(fps)
            self.update_geo()
            win.blit(self.sprite, (adj_x, adj_y))
