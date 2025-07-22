import pygame
from os.path import join, isfile
from Helpers import handle_exception


class HUD():
    def __init__(self, player, win, grayscale=False):
        self.player = player
        self.win = win
        self.is_grayscale = grayscale
        self.save_icon_timer = 0.0
        self.hp_outline = pygame.Surface((324, 16), pygame.SRCALPHA)
        self.hp_outline.fill((0, 0, 0))
        self.hp_pct = 0
        self.hp_bar = None

        self.icon_bar = pygame.Surface((324, 64), pygame.SRCALPHA)
        file = join("Assets", "Icons", "jump.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_jump = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_jump = pygame.transform.grayscale(self.icon_jump)
        file = join("Assets", "Icons", "double_jump.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_double_jump = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_double_jump = pygame.transform.grayscale(self.icon_double_jump)
        file = join("Assets", "Icons", "block.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_block = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_block = pygame.transform.grayscale(self.icon_block)
        file = join("Assets", "Icons", "teleport.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_teleport = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_teleport = pygame.transform.grayscale(self.icon_teleport)
        file = join("Assets", "Icons", "resize.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_resize = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_resize = pygame.transform.grayscale(self.icon_resize)
        file = join("Assets", "Icons", "bullet_time.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.icon_bullet_time = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.icon_bullet_time = pygame.transform.grayscale(self.icon_bullet_time)

        file = join("Assets", "Icons", "save.png")
        if not isfile(file):
            handle_exception(FileNotFoundError(file))
        else:
            self.save_icon = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
            if grayscale:
                self.save_icon = pygame.transform.grayscale(self.save_icon)

    def draw_health_bar(self) -> None:
        hp_pct = min(1, max(0.01, self.player.hp / self.player.max_hp))
        if self.hp_pct != hp_pct:
            self.hp_pct = hp_pct
            self.hp_bar = pygame.Surface(((self.hp_outline.get_width() - 4) * hp_pct, 12), pygame.SRCALPHA)
            if self.is_grayscale:
                self.hp_bar.fill((255, 255, 255))
            else:
                self.hp_bar.fill((min(2 * 255 * (1 - hp_pct), 255), min(2 * 255 * hp_pct, 255), 0))
        self.win.blit(self.hp_outline, (10, 10))
        self.win.blit(self.hp_bar, (12, 12))

    def draw_icons(self) -> None:
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

    def draw_save(self) -> None:
        self.win.blit(self.save_icon, (self.win.get_width() * 0.94, self.win.get_height() - (self.win.get_width() * 0.06)))

    def output(self) -> None:
        self.draw_health_bar()
        self.draw_icons()
        if self.save_icon_timer > 0:
            self.draw_save()
