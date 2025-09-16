import pygame
import time
import sys
from os.path import join, isfile
from Level import Level
from HUD import HUD


class Camera:
    SCROLL_AREA_WIDTH_PCT_FIXED = 0.375
    SCROLL_AREA_HEIGHT_PCT_FIXED = 0.25
    SCROLL_SPEED = 1

    def __init__(self, win: pygame.Surface, focus_player=True) -> None:
        self.level = None
        self.hud = None
        self.win = win
        self.width = win.get_width()
        self.scroll_width = self.width * Camera.SCROLL_AREA_WIDTH_PCT_FIXED
        self.height = win.get_height()
        self.scroll_height = self.height * Camera.SCROLL_AREA_HEIGHT_PCT_FIXED
        self.focus_player = focus_player
        self.focus_x = self.focus_y = 0.0
        self.scroll_wait_time = 0.0
        self.offset_x = self.offset_y = 0.0
        self.bg_tileset = []
        self.bg_image = self.fg_image = None

    def prepare(self, level: Level, hud: HUD) -> None:
        self.level = level
        self.hud = hud
        self.__get_background__()
        self.__get_foreground__()

    def focus_point(self, x: float, y: float) -> None:
        self.focus_x = x
        self.focus_y = y

    def scroll_to_player(self, dtime: float) -> bool:
        player_rect = self.level.get_player().rect
        if self.focus_player:
            self.focus_x = player_rect.centerx
            self.focus_y = player_rect.centery
            self.__update_offset__()
            return True
        else:
            return self.scroll_to_point(dtime, player_rect.centerx, player_rect.centery)

    def scroll_to_point(self, dtime: float, target_x: float, target_y: float, target_wait_time: float=0.0) -> bool:
        arrived = bool(self.focus_x == target_x and self.focus_y == target_y)
        if arrived:
            self.scroll_wait_time += dtime
        else:
            self.scroll_wait_time = 0

            delta_x = target_x - self.focus_x
            delta_y = target_y - self.focus_y
            target_dist = (delta_x ** 2 + delta_y ** 2) ** 0.5
            adj_dist = dtime * Camera.SCROLL_SPEED
            adj_x = adj_dist * (delta_x / target_dist)
            adj_y = adj_dist * (delta_y / target_dist)

            if abs(delta_x) > abs(adj_x):
                self.focus_x += adj_x
            else:
                self.focus_x = target_x

            if abs(delta_y) > abs(adj_y):
                self.focus_y += adj_y
            else:
                self.focus_y = target_y

            self.__update_offset__()
        return bool(arrived and self.scroll_wait_time >= target_wait_time)

    def __update_offset__(self) -> None:
        if self.offset_x > self.focus_x - self.scroll_width:
            self.offset_x = max(self.focus_x - self.scroll_width, self.level.level_bounds[0][0])
        elif self.offset_x < self.focus_x + self.scroll_width - self.width:
            self.offset_x = min(self.focus_x + self.scroll_width - self.width, self.level.level_bounds[1][0] - self.width)

        if self.offset_y > self.focus_y - (2 * self.scroll_height):
            self.offset_y = max(self.focus_y - (2 * self.scroll_height), self.level.level_bounds[0][1])
        elif self.offset_y < self.focus_y + self.scroll_height - self.height:
            self.offset_y = min(self.focus_y + self.scroll_height - self.height, self.level.level_bounds[1][1] - self.height)

    def __get_background__(self) -> None:
        file = join("Assets", "Background", self.level.background)
        if not isfile(file):
            file = join("Assets", "Background", "Blue.png")

        self.bg_image = pygame.image.load(file).convert_alpha()
        if self.level.grayscale:
            self.bg_image = pygame.transform.grayscale(self.bg_image)
        _, _, width, height = self.bg_image.get_rect()

        self.bg_tileset = []
        for i in range(max((self.level.level_bounds[1][0] // width), 1)):
            for j in range(max((self.level.level_bounds[1][1] // height), 1)):
                self.bg_tileset.append((i * width, j * height))

    def __get_foreground__(self) -> None:
        if self.level.foreground is not None:
            file = join("Assets", "Foreground", self.level.foreground)
            if isfile(file):
                self.fg_image = pygame.image.load(file).convert_alpha()
                if self.level.grayscale:
                    self.fg_image = pygame.transform.grayscale(self.fg_image)

    def draw(self, master_volume: dict, fps: int, glitches: list=None):
        visible_screen = pygame.Rect(self.offset_x, self.offset_y, self.width, self.height)

        if len(self.bg_tileset) == 1:
            self.win.blit(self.bg_image.subsurface(visible_screen), (0, 0))
        else:
            for tile in self.bg_tileset:
                self.win.blit(self.bg_image, (tile[0] - self.offset_x, tile[1] - self.offset_y))

        self.level.draw(self.win, self.offset_x, self.offset_y, master_volume, fps)

        if self.fg_image is not None:
            self.win.blit(self.fg_image.subsurface(visible_screen), (0, 0))

        self.hud.draw(self.level.get_formatted_time())

        if glitches is not None:
            for spot in glitches:
                self.win.blit(spot[0], spot[1])

    def __fade__(self, controller, direction: str="in"):
        black = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        black.fill((0, 0, 0))
        for i in range(64):
            self.draw(controller.master_volume, 1)
            if direction == "in":
                black.set_alpha(255 - (4 * i))
                volume = (i + 1) / 64
            elif direction == "out":
                black.set_alpha(4 * i)
                volume = 1 - ((i + 1) / 64)
            else:
                volume = 1
            self.win.blit(black, (0, 0))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    controller.save_player_profile(controller)
                    pygame.quit()
                    sys.exit()
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume((controller.master_volume["background"]) * volume)
            time.sleep(0.01)

    def fade_in(self, controller):
        self.__fade__(controller, direction="in")

    def fade_out(self, controller):
        self.__fade__(controller, direction="out")
        self.win.fill((0, 0, 0))
