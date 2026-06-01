from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
import time
from Helpers import ASSETS_FOLDER, image_to_retro
from Level import Level
from HUD import HUD

if TYPE_CHECKING:
    from Controller import Controller


class Camera:
    SCROLL_AREA_WIDTH_PCT_FIXED:  float = 0.375
    SCROLL_AREA_HEIGHT_PCT_FIXED: float = 0.25
    SCROLL_SPEED:                 float = 1000

    def __init__(
            self:         Camera,
            win:          pygame.Surface,
            focus_player: bool = True,
    ) -> None:
        """Initialize the camera's viewport, scroll regions, and background/foreground state."""
        self.level:         Level | None          = None
        self.hud:           HUD | None            = None
        self.win:           pygame.Surface        = win
        self.width:         float                 = win.get_width()
        self.scroll_width:  float                 = self.width * Camera.SCROLL_AREA_WIDTH_PCT_FIXED
        self.height:        float                 = win.get_height()
        self.scroll_height: float                 = self.height * Camera.SCROLL_AREA_HEIGHT_PCT_FIXED
        self.focus_player:  bool                  = focus_player
        self.focus_x:       float                 = 0.0
        self.focus_y:       float                 = 0.0
        self.scroll_wait_time: float              = 0.0
        self.offset_x:      float                 = 0.0
        self.offset_y:      float                 = 0.0
        self.bg_tileset:    list                  = []
        self.bg_image:      pygame.Surface | None = None
        self.fg_image:      pygame.Surface | None = None

    def prepare(
            self:  Camera,
            level: Level,
            hud:   HUD,
    ) -> None:
        """Attach a level and HUD and build the background and foreground layers."""
        self.level = level
        self.hud   = hud
        self.__get_background__()
        self.__get_foreground__()
        return None

    def focus_point(
            self: Camera,
            x:    float,
            y:    float,
    ) -> None:
        """Set the camera's focus point directly."""
        self.focus_x = x
        self.focus_y = y
        return None

    def scroll_to_player(
            self:  Camera,
            dtime: float,
    ) -> bool:
        """Centre the camera on the player (instantly or by scrolling) and report arrival."""
        if self.level and self.level.player and self.level.player.rect:
            if self.focus_player:
                self.focus_x = self.level.player.rect.centerx
                self.focus_y = self.level.player.rect.centery
                self.__update_offset__()
                return True
            else:
                return self.scroll_to_point(dtime, self.level.player.rect.centerx, self.level.player.rect.centery)
        return False

    def scroll_to_point(
            self:             Camera,
            dtime:            float,
            target_x:         float,
            target_y:         float,
            target_wait_time: float = 0.0,
    ) -> bool:
        """Scroll the focus toward a target point and report once it has arrived there."""
        arrived = bool(self.focus_x == target_x and self.focus_y == target_y)
        if arrived:
            self.scroll_wait_time += dtime
        else:
            self.scroll_wait_time = 0

            delta_x     = target_x - self.focus_x
            delta_y     = target_y - self.focus_y
            target_dist = (delta_x ** 2 + delta_y ** 2) ** 0.5
            adj_dist    = dtime * Camera.SCROLL_SPEED
            adj_x       = adj_dist * (delta_x / target_dist)
            adj_y       = adj_dist * (delta_y / target_dist)

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

    def __update_offset__(
            self: Camera,
    ) -> None:
        """Clamp the camera offset to keep the focus within the scroll margins and level bounds."""
        if self.level and self.level.level_bounds:
            if self.offset_x > self.focus_x - self.scroll_width:
                self.offset_x = max(self.focus_x - self.scroll_width, self.level.level_bounds[0][0])
            elif self.offset_x < self.focus_x + self.scroll_width - self.width:
                self.offset_x = min(self.focus_x + self.scroll_width - self.width, self.level.level_bounds[1][0] - self.width)

            if self.offset_y > self.focus_y - (2 * self.scroll_height):
                self.offset_y = max(self.focus_y - (2 * self.scroll_height), self.level.level_bounds[0][1])
            elif self.offset_y < self.focus_y + self.scroll_height - self.height:
                self.offset_y = min(self.focus_y + self.scroll_height - self.height, self.level.level_bounds[1][1] - self.height)
        return None

    def __get_background__(
            self: Camera,
    ) -> None:
        """Load the level background image and compute its tiling positions."""
        if self.level:
            file = ASSETS_FOLDER / "Background" / self.level.background
            if not file.is_file():
                file = ASSETS_FOLDER / "Background" / "Blue.png"

            self.bg_image = pygame.image.load(file).convert_alpha()

            if self.level.retro and self.bg_image:
                self.bg_image = image_to_retro(self.bg_image)

            if self.bg_image:
                _, _, width, height = self.bg_image.get_rect()

                self.bg_tileset = []
                if self.level and self.level.level_bounds:
                    for i in range(max((self.level.level_bounds[1][0] // width), 1)):
                        for j in range(max((self.level.level_bounds[1][1] // height), 1)):
                            self.bg_tileset.append((i * width, j * height))
        return None

    def __get_foreground__(
            self: Camera,
    ) -> None:
        """Load the optional level foreground overlay image."""
        if self.level and self.level.foreground:
            file = ASSETS_FOLDER / "Foreground" / self.level.foreground
            if file.is_file():
                self.fg_image = pygame.image.load(file).convert_alpha()
                if self.level.retro and self.fg_image:
                    self.fg_image = image_to_retro(self.fg_image)
        return None

    def draw(
            self:          Camera,
            master_volume: dict[str, float],
            glitches:      list | None = None,
    ) -> None:
        """Draw the background, level, foreground, HUD, and any glitch overlays."""
        visible_screen = pygame.Rect(self.offset_x, self.offset_y, self.width, self.height)

        if self.bg_image:
            if len(self.bg_tileset) == 1:
                self.win.blit(self.bg_image.subsurface(visible_screen), (0, 0))
            else:
                for tile in self.bg_tileset:
                    self.win.blit(self.bg_image, (tile[0] - self.offset_x, tile[1] - self.offset_y))

        if self.level:
            self.level.draw(self.win, self.offset_x, self.offset_y, master_volume)

        if self.fg_image is not None:
            self.win.blit(self.fg_image.subsurface(visible_screen), (0, 0))

        if self.hud and self.level:
            self.hud.boss_hp_pct = self.level.boss_hp_pct
            self.hud.draw(self.level.formatted_time)
            if self.level.boss_hp_pct == 0:
                self.level.boss_hp_pct = None

        if glitches is not None:
            for spot in glitches:
                self.win.blit(spot[0], spot[1])
        return None

    def __fade__(
            self:       Camera,
            controller: Controller,
            direction:  str = "in",
    ) -> None:
        """Fade the screen in or out over the level, ramping music volume to match."""
        black = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        black.fill((0, 0, 0))
        for i in range(64):
            self.draw(controller.master_volume)
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
                    controller.quit()
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume((controller.master_volume["background"]) * volume)
            time.sleep(0.01)
        return None

    def fade_in(
            self:       Camera,
            controller: Controller,
    ) -> None:
        """Fade the screen in from black."""
        self.__fade__(controller, direction="in")
        return None

    def fade_out(
            self:       Camera,
            controller: Controller,
    ) -> None:
        """Fade the screen out to black and clear the window."""
        self.__fade__(controller, direction="out")
        self.win.fill((0, 0, 0))
        return None
