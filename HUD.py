import pygame
from os.path import join, isfile
from Helpers import handle_exception, load_images, ASSETS_FOLDER


class HUD:
    def __init__(self, player, win, grayscale: bool=False):
        self.player = player
        self.win = win
        self.is_grayscale: bool = grayscale
        self.save_icon_timer: float = 0.0
        self.hp_outline: pygame.Surface | None = pygame.Surface((324, 16), pygame.SRCALPHA)
        self.hp_outline.fill((0, 0, 0))
        self.hp_pct: float = 0.0
        self.hp_bar: pygame.Surface | None = None
        self.time_characters: dict[str, pygame.Surface | None] = load_images("Icons", "Timer")
        for i in range(10):
            c = str(i)
            if self.time_characters.get(c) is None:
                handle_exception("File " + join(ASSETS_FOLDER, "Icons", "Timer", c + ".png") + " not found.")
        if self.time_characters.get("COLON") is None:
            handle_exception("File " + join(ASSETS_FOLDER, "Icons", "Timer", "colon.png") + " not found.")
        if self.time_characters.get("DECIMAL") is None:
            handle_exception("File " + join(ASSETS_FOLDER, "Icons", "Timer", "decimal.png") + " not found.")
        self.time_num_icon_width: int = self.time_characters["0"].get_width()
        self.time_punc_icon_width: int = self.time_characters["COLON"].get_width()
        self.old_time: str = "00:00.000"
        self.time_display: list[pygame.Surface | None] = [self.time_characters["0"], self.time_characters["0"], self.time_characters["COLON"], self.time_characters["0"], self.time_characters["0"], self.time_characters["DECIMAL"], self.time_characters["0"], self.time_characters["0"], self.time_characters["0"]]

        self.icon_bar: pygame.Surface | None = pygame.Surface((324, 64), pygame.SRCALPHA)
        file = join(ASSETS_FOLDER, "Icons", "jump.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_jump: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_jump = pygame.transform.grayscale(self.icon_jump)
        file = join(ASSETS_FOLDER, "Icons", "double_jump.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_double_jump: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_double_jump = pygame.transform.grayscale(self.icon_double_jump)
        file = join(ASSETS_FOLDER, "Icons", "block.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_block: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_block = pygame.transform.grayscale(self.icon_block)
        file = join(ASSETS_FOLDER, "Icons", "teleport.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_teleport: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_teleport = pygame.transform.grayscale(self.icon_teleport)
        file = join(ASSETS_FOLDER, "Icons", "resize.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_resize: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_resize = pygame.transform.grayscale(self.icon_resize)
        file = join(ASSETS_FOLDER, "Icons", "bullet_time.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.icon_bullet_time: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_bullet_time = pygame.transform.grayscale(self.icon_bullet_time)

        file = join(ASSETS_FOLDER, "Icons", "save.png")
        if not isfile(file):
            handle_exception("File " + str(FileNotFoundError(file)) + " not found.")
        else:
            self.save_icon: pygame.Surface | None = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.save_icon = pygame.transform.grayscale(self.save_icon)

    def __draw_health_bar__(self) -> None:
        hp_pct: float = min(1.0, max(0.01, self.player.hp / self.player.max_hp))
        if self.hp_pct != hp_pct:
            self.hp_pct = hp_pct
            self.hp_bar = pygame.Surface((int((self.hp_outline.get_width() - 4) * hp_pct), 12), pygame.SRCALPHA)
            if self.is_grayscale:
                self.hp_bar.fill((255, 255, 255))
            else:
                self.hp_bar.fill((min(int(2 * 255 * (1 - hp_pct)), 255), min(int(2 * 255 * hp_pct), 255), 0))
        self.win.blit(self.hp_outline, (10, 10))
        self.win.blit(self.hp_bar, (12, 12))

    def __draw_icons__(self) -> None:
        if self.player.max_jumps > 0:
            if self.player.jump_count == 0 and self.player.max_jumps > 1:
                self.win.blit(self.icon_double_jump, (10, 28))
            else:
                self.icon_jump.set_alpha(128 if self.player.jump_count >= self.player.max_jumps else 255)
                self.win.blit(self.icon_jump, (10, 28))
            self.icon_double_jump.set_alpha(0 if self.player.jump_count > 0 else 255)
            self.win.blit(self.icon_double_jump, (10, 28))
        if self.player.can_block:
            self.icon_block.set_alpha(128 if self.player.cooldowns["block"] > 0 else 255)
            self.win.blit(self.icon_block, (75, 28))
        if self.player.can_teleport:
            self.icon_teleport.set_alpha(128 if self.player.cooldowns["teleport"] > 0 else 255)
            self.win.blit(self.icon_teleport, (140, 28))
        if self.player.can_resize:
            self.icon_resize.set_alpha(128 if self.player.cooldowns["resize"] > 0 else 255)
            self.win.blit(self.icon_resize, (205, 28))
        if self.player.can_bullet_time:
            self.icon_bullet_time.set_alpha(128 if self.player.cooldowns["bullet_time"] > 0 else 255)
            self.win.blit(self.icon_bullet_time, (270, 28))

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
        self.__draw_icons__()
        self.__draw_time__(formatted_level_time)
        if self.save_icon_timer > 0:
            self.__draw_save__()
