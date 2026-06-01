from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
from Helpers import (
    handle_exception,
    load_images,
    ASSETS_FOLDER,
    image_to_retro,
    NORMAL_BLACK,
    NORMAL_WHITE,
    RETRO_BLACK,
    RETRO_WHITE,
)

if TYPE_CHECKING:
    from Player import Player


class HUD:
    def __init__(
            self:   HUD,
            player: Player,
            win:    pygame.Surface,
            retro:  bool = False,
    ) -> None:
        """Initialize the HUD's health bars, timer display, ability icons, and border."""
        self.player = player
        self.win    = win

        self.scale_factor:      tuple[float, float]   = (self.win.get_width() / 1920, self.win.get_height() / 1080)
        self.retro:             bool                  = retro
        self.objective:         pygame.Surface | None = None
        self.save_icon_timer:   float                 = 0.0

        self.hp_outline:        pygame.Surface | None = pygame.Surface((389 * self.scale_factor[0], 16 * self.scale_factor[1]), pygame.SRCALPHA)
        if self.hp_outline:
            self.hp_outline.fill((0, 0, 0))
        self.hp_pct:            float                 = 0.0
        self.hp_bar:            pygame.Surface | None = None
        self.boss_hp_bar_alpha: int                   = 0
        self.boss_hp_outline:   pygame.Surface | None = pygame.Surface((990 * self.scale_factor[0], 40 * self.scale_factor[1]), pygame.SRCALPHA)
        if self.boss_hp_outline:
            self.boss_hp_outline.fill((0, 0, 0, self.boss_hp_bar_alpha))
        self.boss_hp_pct:       float | None          = None
        self.boss_hp_bar:       pygame.Surface | None = None

        self.time_characters:   dict[str, pygame.Surface | None] | None = load_images("Icons", "Timer")
        if self.time_characters:
            for i in range(10):
                c = str(i)
                if self.time_characters.get(c) is None:
                    handle_exception(f"File {FileNotFoundError((ASSETS_FOLDER / 'Icons' / 'Timer' / f'{c}.png').resolve())} not found.")
            if self.time_characters.get("COLON") is None:
                handle_exception(f"File {FileNotFoundError((ASSETS_FOLDER / 'Icons' / 'Timer' / 'colon.png').resolve())} not found.")
            if self.time_characters.get("DECIMAL") is None:
                handle_exception(f"File {FileNotFoundError((ASSETS_FOLDER / 'Icons' / 'Timer' / 'decimal.png').resolve())} not found.")
            if self.retro:
                for key in self.time_characters:
                    if self.time_characters[key]:
                        self.time_characters[key] = image_to_retro(self.time_characters[key]) # noqa
        self.time_num_icon_width:  int                   = self.time_characters["0"].get_width() if self.time_characters else 0 # noqa
        self.time_punc_icon_width: int                   = self.time_characters["COLON"].get_width() if self.time_characters else 0 # noqa
        self.old_time:             str                   = "00:00.000"
        self.time_display:         list[pygame.Surface | None] = [self.time_characters["0"], self.time_characters["0"], self.time_characters["COLON"], self.time_characters["0"], self.time_characters["0"], self.time_characters["DECIMAL"], self.time_characters["0"], self.time_characters["0"], self.time_characters["0"]]  # noqa
        self.time_capsule:         pygame.Surface        = self.__make_capsule__(self.retro, (5 * self.time_num_icon_width) + (2 * self.time_punc_icon_width) + ((self.time_characters["0"].get_height() + 4) / 2) + 20, self.time_characters["0"].get_height() + 4)  # noqa
        self.objective_capsule:    pygame.Surface | None = None
        self.border:               pygame.Surface        = self.__make_border__(win, retro)

        self.icon_bar:         pygame.Surface | None = pygame.Surface((self.hp_outline.get_width(), 64 * self.scale_factor[1]), pygame.SRCALPHA) if self.hp_outline else None
        self.icon_jump:        pygame.Surface | None = self.__load_icon__("jump.png", retro)
        self.icon_double_jump: pygame.Surface | None = self.__load_icon__("double_jump.png", retro)
        self.icon_block:       pygame.Surface | None = self.__load_icon__("block.png", retro)
        self.icon_teleport:    pygame.Surface | None = self.__load_icon__("teleport.png", retro)
        self.icon_wall_jump:   pygame.Surface | None = self.__load_icon__("wall_jump.png", retro)
        self.icon_resize:      pygame.Surface | None = self.__load_icon__("resize.png", retro)
        self.icon_bullet_time: pygame.Surface | None = self.__load_icon__("bullet_time.png", retro)
        self.save_icon:        pygame.Surface | None = self.__load_icon__("save.png", retro)

    @staticmethod
    def __load_icon__(
            filename: str,
            retro:    bool,
    ) -> pygame.Surface | None:
        """Load, scale, and optionally retro-tint a single HUD icon, or report it missing."""
        file = ASSETS_FOLDER / "Icons" / filename
        if not file.is_file():
            handle_exception(f"File {FileNotFoundError(file.resolve())} not found.")
            return None
        icon = pygame.transform.scale2x(pygame.image.load(file).convert_alpha())
        if retro:
            icon = image_to_retro(icon)
        return icon

    @staticmethod
    def __make_capsule__(
            retro:  bool,
            width:  float,
            height: float,
    ) -> pygame.Surface:
        """Build a rounded capsule background surface for a HUD element."""
        capsule: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.circle(capsule, RETRO_BLACK if retro else NORMAL_BLACK, ((capsule.get_height() / 2), (capsule.get_height() / 2)), (capsule.get_height() / 2))
        pygame.draw.circle(capsule, RETRO_WHITE if retro else NORMAL_WHITE, ((capsule.get_height() / 2), (capsule.get_height() / 2)), (capsule.get_height() / 2), width=1)
        bar = pygame.Surface((capsule.get_width() - (capsule.get_height() / 2), capsule.get_height()), pygame.SRCALPHA)
        bar.fill(RETRO_BLACK if retro else NORMAL_BLACK)
        pygame.draw.line(bar, RETRO_WHITE if retro else NORMAL_WHITE, (0, 0), (bar.get_width(), 0), 1)
        pygame.draw.line(bar, RETRO_WHITE if retro else NORMAL_WHITE, (0, bar.get_height() - 1), (bar.get_width(), bar.get_height() - 1), 1)
        capsule.blit(bar, ((capsule.get_height() // 2), 0))
        return capsule

    def activate_objective(
            self: HUD,
            text: str | None,
    ) -> None:
        """Render the current objective text and build its capsule background."""
        text_colour    = RETRO_WHITE if self.retro else NORMAL_WHITE
        self.objective = pygame.font.SysFont("courier", 32).render(text, True, text_colour)
        if self.objective:
            self.objective_capsule = self.__make_capsule__(self.retro, self.objective.get_width() + ((self.objective.get_height() + 4) // 2) + 20, self.objective.get_height() + 4)
        return None

    def __draw_objective__(
            self: HUD,
    ) -> None:
        """Draw the objective capsule and text in the top-right corner."""
        if self.objective:
            if self.objective_capsule:
                self.win.blit(self.objective_capsule, (self.win.get_width() - (self.objective_capsule.get_width() - 1), self.time_capsule.get_height() + 7))
            self.win.blit(self.objective, (self.win.get_width() - (self.objective.get_width() + 9), self.time_capsule.get_height() + 9))
        return None

    @staticmethod
    def __make_border__(
            win:   pygame.Surface,
            retro: bool,
    ) -> pygame.Surface:
        """Build the retro screen border surface with framed edges and rotated corners."""
        thickness = 8
        surf        = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
        line_colour = RETRO_WHITE if retro else NORMAL_WHITE
        bar_colour  = RETRO_BLACK if retro else NORMAL_BLACK
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
        file = ASSETS_FOLDER / "Foreground" / "border_retro.png"
        corner: pygame.Surface | None
        if not file.is_file():
            handle_exception(f"File {FileNotFoundError(file.resolve())} not found.")
            corner = None
        else:
            corner = pygame.image.load(file).convert_alpha()
        if corner is not None:
            coords = ((0, 0, 0), (win.get_width() - corner.get_width(), 0, 270), (win.get_width() - corner.get_width(), win.get_height() - corner.get_height(), 180), (0, win.get_height() - corner.get_height(), 90))
            for coord in coords:
                surf.blit(pygame.transform.rotate(corner, coord[2]), (coord[0], coord[1]))
        return surf

    def __draw_health_bar__(
            self: HUD,
    ) -> None:
        """Draw the player's health bar, recolouring it only when the percentage changes."""
        hp_pct: float = min(1.0, max(0.01, self.player.hp / self.player.max_hp))
        if self.hp_outline and self.hp_pct != hp_pct:
            self.hp_pct = hp_pct
            self.hp_bar = pygame.Surface((int((self.hp_outline.get_width() - 4) * hp_pct) * self.scale_factor[0], 12 * self.scale_factor[1]), pygame.SRCALPHA)
            if self.hp_bar:
                if self.retro:
                    self.hp_bar.fill((min(int(250 * hp_pct), 255), min(int(215 * hp_pct), 255), min(int(195 * hp_pct), 255)))
                else:
                    self.hp_bar.fill((min(int(2 * 255 * (1 - hp_pct)), 255), min(int(2 * 255 * hp_pct), 255), 0))

        if self.hp_outline and self.hp_bar:
            self.win.blit(self.hp_outline, (10, 10))
            self.win.blit(self.hp_bar, (12, 12))

        return None

    def __draw_boss_health_bar__(
            self: HUD,
    ) -> None:
        """Draw or fade the boss health bar based on the current boss-hp percentage."""
        if self.boss_hp_pct and self.boss_hp_outline:
            self.boss_hp_bar = pygame.Surface((int((self.boss_hp_outline.get_width() - 4) * self.boss_hp_pct) * self.scale_factor[0], 36 * self.scale_factor[1]), pygame.SRCALPHA)
            if self.boss_hp_bar:
                if self.boss_hp_bar_alpha < 128:
                    self.boss_hp_bar_alpha += 1
                    self.boss_hp_outline.fill((0, 0, 0, self.boss_hp_bar_alpha))
                if self.retro:
                    self.boss_hp_bar.fill((RETRO_WHITE[0], RETRO_WHITE[1], RETRO_WHITE[2], self.boss_hp_bar_alpha))
                else:
                    self.boss_hp_bar.fill((255, 0, 0, self.boss_hp_bar_alpha))
                if self.boss_hp_bar_alpha < 128:
                    rendered_hp_outline = pygame.transform.scale_by(self.boss_hp_outline, (self.boss_hp_bar_alpha / 128, 1))
                    rendered_hp_bar     = pygame.transform.scale_by(self.boss_hp_bar, (self.boss_hp_bar_alpha / 128, 1))
                else:
                    rendered_hp_outline = self.boss_hp_outline
                    rendered_hp_bar     = self.boss_hp_bar
                self.win.blit(rendered_hp_outline, ((self.win.get_width() - rendered_hp_outline.get_width()) // 2, self.win.get_height() - (rendered_hp_outline.get_height() + 100)))
                self.win.blit(rendered_hp_bar, (((self.win.get_width() - rendered_hp_outline.get_width()) // 2) + 2, (self.win.get_height() - (rendered_hp_outline.get_height() + 100)) + 2))
        elif self.boss_hp_bar_alpha > 0 and self.boss_hp_outline and self.boss_hp_bar:
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
        return None

    def __draw_icons__(
            self: HUD,
    ) -> None:
        """Draw the player's ability icons, dimming those on cooldown or unavailable."""
        if self.icon_double_jump and self.player.abilities["can_double_jump"] and self.player.jump_count == 0 and self.player.max_jumps > 1:
            self.win.blit(self.icon_double_jump, (10 * self.scale_factor[0], 28 * self.scale_factor[1]))
        elif self.icon_jump:
            self.icon_jump.set_alpha(128 if self.player.jump_count >= self.player.max_jumps else 255)
            self.win.blit(self.icon_jump, (10 * self.scale_factor[0], 28))
        if self.icon_wall_jump and self.player.abilities["can_wall_jump"]:
            self.icon_wall_jump.set_alpha(255 if self.player.is_wall_jumping else 128)
            self.win.blit(self.icon_wall_jump, (75 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.icon_teleport and self.player.abilities["can_teleport"]:
            self.icon_teleport.set_alpha(int(128 / (1 + self.player.cooldowns["teleport"]) if self.player.cooldowns["teleport"] > 0 else 255))
            self.win.blit(self.icon_teleport, (140 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.icon_resize and self.player.abilities["can_resize"]:
            self.icon_resize.set_alpha(int(128 / (1 + self.player.cooldowns["resize"]) if self.player.cooldowns["resize"] > 0 else 255))
            self.win.blit(self.icon_resize, (205 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.icon_block and self.player.abilities["can_block"]:
            self.icon_block.set_alpha(int(128 / (1 + self.player.cooldowns["block"]) if self.player.cooldowns["block"] > 0 else 255))
            self.win.blit(self.icon_block, (270 * self.scale_factor[0], 28 * self.scale_factor[1]))
        if self.icon_bullet_time and self.player.abilities["can_bullet_time"]:
            self.icon_bullet_time.set_alpha(int(128 / (1 + self.player.cooldowns["bullet_time"]) if self.player.cooldowns["bullet_time"] > 0 else 255))
            self.win.blit(self.icon_bullet_time, (335 * self.scale_factor[0], 28 * self.scale_factor[1]))
        return None

    def __draw_save__(
            self: HUD,
    ) -> None:
        """Draw the save icon in the lower-right corner."""
        if self.save_icon:
            self.win.blit(self.save_icon, (self.win.get_width() * 0.94, self.win.get_height() - (self.win.get_width() * 0.06)))
        return None

    def __draw_time__(
            self:                 HUD,
            formatted_level_time: str,
    ) -> None:
        """Draw the level timer, updating only the digits that changed since last frame."""
        if len(formatted_level_time) <= 7:
            self.win.blit(self.time_capsule, (self.win.get_width() - self.time_capsule.get_width(), 8))
            for i in range(len(formatted_level_time)):
                if formatted_level_time[i] != self.old_time[i]:
                    char = formatted_level_time[i]
                    if char == ":":
                        char = "COLON"
                    elif char == ".":
                        char = "DECIMAL"
                    self.time_display[i] = self.time_characters[char] # noqa
                offset_x = (len(formatted_level_time) - i) * self.time_num_icon_width
                if i < len(formatted_level_time) - 4:
                    offset_x += self.time_punc_icon_width - self.time_num_icon_width
                if i < len(formatted_level_time) - 1:
                    offset_x += self.time_punc_icon_width - self.time_num_icon_width
                if self.time_display[i]:
                    self.win.blit(self.time_display[i], (self.win.get_width() - (10 + offset_x), 10)) # noqa
            self.old_time = formatted_level_time
        return None

    def draw(
            self:                 HUD,
            formatted_level_time: str,
    ) -> None:
        """Draw the full HUD: health bars, icons, timer, objective, save icon, and border."""
        self.__draw_health_bar__()
        self.__draw_boss_health_bar__()
        self.__draw_icons__()
        self.__draw_time__(formatted_level_time)
        self.__draw_objective__()
        if self.save_icon_timer > 0:
            self.__draw_save__()
        if self.retro:
            self.win.blit(self.border, (0, 0))
        return None
