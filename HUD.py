import pygame
from os.path import join, isfile, abspath
from Helpers import handle_exception, load_images, ASSETS_FOLDER, retroify_image, NORMAL_BLACK, NORMAL_WHITE, \
    RETRO_BLACK, RETRO_WHITE


class HUD:
    def __init__(self, player, win, retro: bool=False):
        self.player = player
        self.win = win
        self.scale_factor: tuple[float, float] = (self.win.get_width() / 1920, self.win.get_height() / 1080)
        self.retro: bool = retro
        self.border = self.__make_border__(win, retro)
        self.save_icon_timer: float = 0.0
        self.hp_outline: pygame.Surface | None = pygame.Surface((389 * self.scale_factor[0], 16 * self.scale_factor[1]), pygame.SRCALPHA)
        self.hp_outline.fill((0, 0, 0))
        self.hp_pct: float = 0.0
        self.hp_bar: pygame.Surface | None = None
        self.boss_hp_bar_alpha: int = 0
        self.boss_hp_outline: pygame.Surface | None = pygame.Surface((990 * self.scale_factor[0], 40 * self.scale_factor[1]), pygame.SRCALPHA)
        self.boss_hp_outline.fill((0, 0, 0, self.boss_hp_bar_alpha))
        self.boss_hp_pct: float | None = None
        self.boss_hp_bar: pygame.Surface | None = None
        self.time_characters: dict[str, pygame.Surface | None] = load_images("Icons", "Timer")
        for i in range(10):
            c = str(i)
            if self.time_characters.get(c) is None:
                handle_exception(f'File {FileNotFoundError(abspath(join(ASSETS_FOLDER, "Icons", "Timer", f'{c}.png')))} not found.')
        if self.time_characters.get("COLON") is None:
            handle_exception(f'File {FileNotFoundError(abspath(join(ASSETS_FOLDER, "Icons", "Timer", "colon.png")))} not found.')
        if self.time_characters.get("DECIMAL") is None:
            handle_exception(f'File {FileNotFoundError(abspath(join(ASSETS_FOLDER, "Icons", "Timer", "decimal.png")))} not found.')
        self.time_num_icon_width: int = self.time_characters["0"].get_width()
        self.time_punc_icon_width: int = self.time_characters["COLON"].get_width()
        self.old_time: str = "00:00.000"
        self.time_display: list[pygame.Surface | None] = [self.time_characters["0"], self.time_characters["0"], self.time_characters["COLON"], self.time_characters["0"], self.time_characters["0"], self.time_characters["DECIMAL"], self.time_characters["0"], self.time_characters["0"], self.time_characters["0"]]

        self.icon_bar: pygame.Surface | None = pygame.Surface((self.hp_outline.get_width(), 64 * self.scale_factor[1]), pygame.SRCALPHA)
        file = join(ASSETS_FOLDER, "Icons", "jump.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_jump: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_jump = retroify_image(self.icon_jump)
        file = join(ASSETS_FOLDER, "Icons", "double_jump.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_double_jump: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_double_jump = retroify_image(self.icon_double_jump)
        file = join(ASSETS_FOLDER, "Icons", "block.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_block: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_block = retroify_image(self.icon_block)
        file = join(ASSETS_FOLDER, "Icons", "teleport.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_teleport: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_teleport = retroify_image(self.icon_teleport)
        file = join(ASSETS_FOLDER, "Icons", "wall_jump.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_wall_jump: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_wall_jump = retroify_image(self.icon_wall_jump)
        file = join(ASSETS_FOLDER, "Icons", "resize.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_resize: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_resize = retroify_image(self.icon_resize)
        file = join(ASSETS_FOLDER, "Icons", "bullet_time.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.icon_bullet_time: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.icon_bullet_time = retroify_image(self.icon_bullet_time)

        file = join(ASSETS_FOLDER, "Icons", "save.png")
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
        else:
            self.save_icon: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if retro:
                self.save_icon = retroify_image(self.save_icon)

    @staticmethod
    def __make_border__(win, retro) -> pygame.Surface:
        thickness = 8
        surf = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
        line_colour = RETRO_WHITE if retro else NORMAL_WHITE
        bar_colour = RETRO_BLACK if retro else NORMAL_BLACK
        for x in [0, win.get_width()]:
            pygame.draw.line(surf, bar_colour, (x, 0), (x, win.get_height()), thickness * 2)
            if x == 0:
                pygame.draw.line(surf, line_colour, (x + thickness, thickness), (x + thickness, win.get_height() - thickness), 1)
            else:
                pygame.draw.line(surf, line_colour, (x - thickness, thickness), (x - thickness, win.get_height() - thickness), 1)
        for y in [0, win.get_height()]:
            pygame.draw.line(surf, bar_colour, (0, y), (win.get_width(), y), thickness * 2)
            if y == 0:
                pygame.draw.line(surf, line_colour, (thickness, y + thickness), (win.get_width() - thickness, y + thickness), 1)
            else:
                pygame.draw.line(surf, line_colour, (thickness, y - thickness), (win.get_width() - thickness, y - thickness), 1)
        file = join(ASSETS_FOLDER, "Foreground", "border_retro.png")
        corner: pygame.Surface | None
        if not isfile(file):
            handle_exception(f'File {FileNotFoundError(abspath(file))} not found.')
            corner = None
        else:
            corner = pygame.image.load(file).convert_alpha()
        if corner is not None:
            coords = ((0, 0, 0), (win.get_width() - corner.get_width(), 0, 270), (win.get_width() - corner.get_width(), win.get_height() - corner.get_height(), 180), (0, win.get_height() - corner.get_height(), 90))
            for coord in coords:
                surf.blit(pygame.transform.rotate(corner, coord[2]), (coord[0], coord[1]))
        return surf


    def __draw_health_bar__(self) -> None:
        hp_pct: float = min(1.0, max(0.01, self.player.hp / self.player.max_hp))
        if self.hp_pct != hp_pct:
            self.hp_pct = hp_pct
            self.hp_bar = pygame.Surface((int((self.hp_outline.get_width() - 4) * hp_pct) * self.scale_factor[0], 12 * self.scale_factor[1]), pygame.SRCALPHA)
            if self.retro:
                self.hp_bar.fill((min(int(250 * hp_pct), 255), min(int(215 * hp_pct), 255), min(int(195 * hp_pct), 255)))
            else:
                self.hp_bar.fill((min(int(2 * 255 * (1 - hp_pct)), 255), min(int(2 * 255 * hp_pct), 255), 0))
        self.win.blit(self.hp_outline, (10, 10))
        self.win.blit(self.hp_bar, (12, 12))

    def __draw_boss_health_bar__(self) -> None:
        if self.boss_hp_pct is not None:
            self.boss_hp_bar = pygame.Surface((int((self.boss_hp_outline.get_width() - 4) * self.boss_hp_pct) * self.scale_factor[0], 36 * self.scale_factor[1]), pygame.SRCALPHA)
            if self.boss_hp_bar_alpha < 128:
                self.boss_hp_bar_alpha += 1
                self.boss_hp_outline.fill((0, 0, 0, self.boss_hp_bar_alpha))
            if self.retro:
                self.boss_hp_bar.fill((RETRO_WHITE[0], RETRO_WHITE[1], RETRO_WHITE[2], self.boss_hp_bar_alpha))
            else:
                self.boss_hp_bar.fill((255, 0, 0, self.boss_hp_bar_alpha))
            if self.boss_hp_bar_alpha < 128:
                rendered_hp_outline = pygame.transform.scale_by(self.boss_hp_outline, (self.boss_hp_bar_alpha / 128, 1))
                rendered_hp_bar = pygame.transform.scale_by(self.boss_hp_bar, (self.boss_hp_bar_alpha / 128, 1))
            else:
                rendered_hp_outline = self.boss_hp_outline
                rendered_hp_bar = self.boss_hp_bar
            self.win.blit(rendered_hp_outline, ((self.win.get_width() - rendered_hp_outline.get_width()) // 2, self.win.get_height() - (rendered_hp_outline.get_height() + 100)))
            self.win.blit(rendered_hp_bar, (((self.win.get_width() - rendered_hp_outline.get_width()) // 2) + 2, (self.win.get_height() - (rendered_hp_outline.get_height() + 100)) + 2))
        elif self.boss_hp_bar_alpha > 0:
            self.boss_hp_bar_alpha -= 1
            if self.retro:
                self.boss_hp_bar.fill((RETRO_WHITE[0], RETRO_WHITE[1], RETRO_WHITE[2], self.boss_hp_bar_alpha))
            else:
                self.boss_hp_bar.fill((255, 0, 0, self.boss_hp_bar_alpha))
            self.boss_hp_outline.fill((0, 0, 0, self.boss_hp_bar_alpha))
            self.win.blit(self.boss_hp_outline, ((self.win.get_width() - self.boss_hp_outline.get_width()) // 2, self.win.get_height() - (self.boss_hp_outline.get_height() + 100)))
            self.win.blit(self.boss_hp_bar, (((self.win.get_width() - self.boss_hp_outline.get_width()) // 2) + 2, (self.win.get_height() - (self.boss_hp_outline.get_height() + 100)) + 2))
        else:
            self.boss_hp_bar = None

    def __draw_icons__(self) -> None:
        if self.player.abilities["can_double_jump"] and self.player.jump_count == 0 and self.player.max_jumps > 1:
            self.win.blit(self.icon_double_jump, (10 * self.scale_factor[0], 28 * self.scale_factor[1]))
        else:
            self.icon_jump.set_alpha(128 if self.player.jump_count >= self.player.max_jumps else 255)
            self.win.blit(self.icon_jump, (10 * self.scale_factor[0], 28))
        if self.player.abilities["can_teleport"]:
            self.icon_teleport.set_alpha(128 if self.player.cooldowns["teleport"] > 0 else 255)
            self.win.blit(self.icon_teleport, (75 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.player.abilities["can_wall_jump"]:
            self.icon_wall_jump.set_alpha(255 if self.player.is_wall_jumping else 128)
            self.win.blit(self.icon_wall_jump, (140 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.player.abilities["can_resize"]:
            self.icon_resize.set_alpha(128 if self.player.cooldowns["resize"] > 0 else 255)
            self.win.blit(self.icon_resize, (205 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.player.abilities["can_block"]:
            self.icon_block.set_alpha(128 if self.player.cooldowns["block"] > 0 else 255)
            self.win.blit(self.icon_block, (270 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.player.abilities["can_bullet_time"]:
            self.icon_bullet_time.set_alpha(128 if self.player.cooldowns["bullet_time"] > 0 else 255)
            self.win.blit(self.icon_bullet_time, (335 * self.scale_factor[0], 28 * self.scale_factor[1]))

    def __draw_save__(self) -> None:
        self.win.blit(self.save_icon, (self.win.get_width() * 0.94, self.win.get_height() - (self.win.get_width() * 0.06)))

    def __draw_time__(self, formatted_level_time: str) -> None:
        if len(formatted_level_time) <= 9:
            for i in range(len(formatted_level_time)):
                if formatted_level_time[i] != self.old_time[i]:
                    char = formatted_level_time[i]
                    if char == ":":
                        char = "COLON"
                    elif char == ".":
                        char = "DECIMAL"
                    self.time_display[i] = self.time_characters[char]
                offset_x = (len(formatted_level_time) - i) * self.time_num_icon_width
                if i < len(formatted_level_time) - 6:
                    offset_x += self.time_punc_icon_width - self.time_num_icon_width
                if i < len(formatted_level_time) - 3:
                    offset_x += self.time_punc_icon_width - self.time_num_icon_width
                self.win.blit(self.time_display[i], (self.win.get_width() - (10 + offset_x), 10))
            self.old_time = formatted_level_time

    def draw(self, formatted_level_time: str) -> None:
        self.__draw_health_bar__()
        self.__draw_boss_health_bar__()
        self.__draw_icons__()
        self.__draw_time__(formatted_level_time)
        if self.save_icon_timer > 0:
            self.__draw_save__()
        if self.retro:
            self.win.blit(self.border, (0, 0))
