import math
import random
import pygame
from os.path import join, isfile, abspath
from Entity import Entity
from Helpers import handle_exception, set_sound_source, load_sprite_sheets, ASSETS_FOLDER, retroify_image


class Objective(Entity):
    if not isfile(join(ASSETS_FOLDER, "Icons", "Pointer", "pointer.png")):
        handle_exception(f'File {FileNotFoundError(abspath(join(ASSETS_FOLDER, "Icons", "Pointer", "pointer.png")))} not found.')
    else:
        POINTER_SPRITE: pygame.Surface = pygame.transform.scale2x(pygame.image.load(join(ASSETS_FOLDER, "Icons", "Pointer", "pointer.png")).convert_alpha())
        if isfile(join(ASSETS_FOLDER, "Icons", "Pointer", "pointer_retro.png")):
            POINTER_SPRITE_RETRO: pygame.Surface = pygame.transform.scale2x(pygame.image.load(join(ASSETS_FOLDER, "Icons", "Pointer", "pointer_retro.png")).convert_alpha())
        else:
            POINTER_SPRITE_RETRO: pygame.Surface = retroify_image(POINTER_SPRITE)
        POINTER_SPRITE_HEIGHT: int = POINTER_SPRITE.get_height()
        POINTER_SPRITE_WIDTH: int = POINTER_SPRITE.get_width()

    def __init__(self, level, controller, x, y, width, height, sprite_master, audios, is_active=False, sprite=None, sound="objective", is_blocking=False, achievement=None, name="Objective"):
        super().__init__(level, controller, x, y, width, height, is_blocking=is_blocking, name=name)
        if sprite is not None:
            avail_sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, retro=self.level.retro)
            if self.level.retro and avail_sprites.get("ANIMATE_RETRO") is not None:
                self.sprites = avail_sprites["ANIMATE_RETRO"]
            else:
                self.sprites = avail_sprites["ANIMATE"]
        else:
            self.sprites = None
        self.animation_count = 0
        self.sprite = None
        if self.sprites is not None:
            self.update_sprite(1)
            self.update_geo()
        self.audios = audios
        self.sound = None if sound == "none" else sound
        self.achievement = achievement
        self.name = name
        self.is_active = is_active
        self.pointer = (Objective.POINTER_SPRITE_RETRO if self.level.retro == True else Objective.POINTER_SPRITE)
        self.pointer_offset = ((self.rect.width - Objective.POINTER_SPRITE_WIDTH) / 2, (-(Objective.POINTER_SPRITE_HEIGHT + 2), -(self.rect.height - Objective.POINTER_SPRITE_HEIGHT / 2)))

    def collide(self, ent) -> bool:
        return False

    def get_hit(self, ent) -> None:
        self.hp = 0
        self.play_sound(self.sound)
        self.__collect__()
        if self.achievement is not None and self.controller.steamworks is not None and not self.controller.steamworks.UserStats.GetAchievement(self.achievement):
            self.controller.steamworks.UserStats.SetAchievement(self.achievement)
            self.controller.should_store_steam_stats = True

    def save(self) -> dict:
        return super().save()

    def load(self, ent) -> None:
        self.hp = ent["hp"]
        if self.hp <= 0:
            self.__collect__()
            self.level.queue_purge(self)

    def __collect__(self) -> None:
        if self.is_active:
            self.is_active = False
        self.level.objectives_collected.append(self)

    def play_sound(self, name) -> None:
        if self.sound is not None and self.audios.get(name.upper()) is not None:
            active_audio_channel = pygame.mixer.find_channel(force=True)
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[name.upper()][random.randrange(len(self.audios[name.upper()]))])
                set_sound_source(self.rect, self.level.player.rect, self.controller.master_volume["non-player"], active_audio_channel)

    def update_sprite(self, fps) -> int:
        active_index = math.floor((self.animation_count // (1000 // (fps * Objective.ANIMATION_DELAY))) % len(self.sprites))
        if active_index >= len(self.sprites):
            active_index = 0
            self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def update_geo(self) -> None:
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def loop(self, dtime) -> None:
        self.animation_count += dtime
        super().loop(dtime)

    def draw(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if self.sprite is not None and -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            self.update_sprite(fps)
            self.update_geo()
            win.blit(self.sprite, (adj_x, adj_y))

        if self.is_active:
            NICE_BORDER_DISTANCE = 64

            if NICE_BORDER_DISTANCE - self.rect.width < adj_x + self.pointer_offset[0] <= (win.get_width() - Objective.POINTER_SPRITE_WIDTH - NICE_BORDER_DISTANCE) and NICE_BORDER_DISTANCE - self.rect.height < adj_y + self.pointer_offset[1][1] <= (win.get_height() - Objective.POINTER_SPRITE_HEIGHT - NICE_BORDER_DISTANCE):
                win.blit(self.pointer, (adj_x + self.pointer_offset[0], adj_y + self.pointer_offset[1][0]))
            else:
                if adj_x < NICE_BORDER_DISTANCE:
                    pointer_x = NICE_BORDER_DISTANCE
                elif adj_x > win.get_width() - (NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_WIDTH):
                    pointer_x = win.get_width() - (NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_WIDTH)
                else:
                    pointer_x = adj_x + self.pointer_offset[0]

                if adj_y < NICE_BORDER_DISTANCE:
                    pointer_y = NICE_BORDER_DISTANCE
                elif adj_y > win.get_height() - (NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_HEIGHT):
                    pointer_y = win.get_height() - (NICE_BORDER_DISTANCE + Objective.POINTER_SPRITE_HEIGHT)
                else:
                    pointer_y = adj_y + self.pointer_offset[1][1]

                rotation = math.degrees(math.atan2(self.rect.x - self.level.player.rect.x, self.rect.y - self.level.player.rect.y))

                win.blit(pygame.transform.rotate(self.pointer, rotation), (pointer_x, pointer_y))
