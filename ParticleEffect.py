from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
import random
from enum import Enum

from Helpers import image_to_retro, NORMAL_WHITE, RETRO_WHITE

if TYPE_CHECKING:
    from Level import Level


class ParticleType(Enum):
    STATIC   = 0
    VARIABLE = 1


class ParticleEffect:
    VARIABLE_IMAGE_DISPLAY_TIME = 0.1

    def __init__(
            self:        ParticleEffect,
            level:       Level,
            win:         pygame.Surface | None,
            width:       int,
            height:      int,
            amount:      int,
            color:       tuple[int, int, int, int],
            x_vel:       float        = 0.0,
            y_vel:       float        = 0.0,
            effect_type: ParticleType = ParticleType.STATIC,
            should_move: bool         = True,
    ) -> None:
        """Initialize a particle effect, generating its static or variable particle image(s)."""
        self.effect_type = effect_type
        self.image: pygame.Surface | list[pygame.Surface] | None = None
        self.image_index:  int  = 0
        self.image_count:  int  = 0
        self.should_move:  bool = should_move
        if self.should_move or win is None:
            bounds: tuple[tuple[int, int], tuple[int, int]] = level.level_bounds
        else:
            bounds: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (win.get_width(), win.get_height()))
        if self.effect_type == ParticleType.STATIC:
            self.image = self.generate_static_effect(width, height, amount, color, bounds, level.retro)
        elif self.effect_type == ParticleType.VARIABLE:
            self.image = self.generate_variable_effect(width, height, amount, color, level.retro)
        self.rect:  pygame.Rect = pygame.Rect(0, 0, bounds[1][0], bounds[1][1])
        self.x_vel: float       = x_vel
        self.y_vel: float       = y_vel

    @property
    def type(
            self: ParticleEffect,
    ) -> ParticleType:
        """Return the particle effect's type."""
        return self.effect_type

    @staticmethod
    def generate_static_effect(
            width:    int,
            height:   int,
            amount:   int,
            color:    tuple[int, int, int, int],
            bounds:   tuple[tuple[int, int], tuple[int, int]],
            is_retro: bool,
    ) -> pygame.Surface:
        """Build a single surface with `amount` particles scattered across the bounds."""
        points = []
        for i in range(amount):
            points.append((random.randint(0, bounds[1][0]), random.randint(0, bounds[1][1])))

        image = pygame.Surface(bounds[1], pygame.SRCALPHA)
        image.set_colorkey((0, 0, 0))
        particle = pygame.Surface((width, height), pygame.SRCALPHA)
        particle.fill(color)
        if is_retro:
            particle = image_to_retro(particle)

        for point in points:
            image.blit(particle, point)

        return image

    @staticmethod
    def generate_variable_effect(
            width:    int,
            height:   int,
            amount:   int,
            color:    tuple[int, int, int, int],
            is_retro: bool,
    ) -> list[pygame.Surface]:
        """Build a list of randomly sized circular/rectangular particle surfaces."""
        images = []
        for i in range(amount):
            if random.randint(0, 1) == 0:
                radius           = random.randint(1, width) * random.randint(1, width)
                border_thickness = random.randint(0, 1)
                particle         = pygame.Surface(((radius + border_thickness) * 2, (radius + border_thickness) * 2), pygame.SRCALPHA)
                pygame.draw.circle(particle, color, (radius, radius), radius, border_thickness)
            else:
                particle = pygame.Surface((random.randint(0, width), random.randint(0, height)), pygame.SRCALPHA)
                particle.fill(color)

            if is_retro:
                particle = image_to_retro(particle)

            images.append(particle)
        return images

    def move(
            self:  ParticleEffect,
            dtime: float,
    ) -> None:
        """Scroll the particle layer, wrapping it around the bounds."""
        if self.x_vel != 0:
            self.rect.x += self.x_vel * dtime
            if self.rect.x < 0:
                self.rect.x = self.rect.width
            elif self.rect.x > self.rect.width:
                self.rect.x = 0
        if self.y_vel != 0:
            self.rect.y += self.y_vel * dtime
            if self.rect.y < 0:
                self.rect.y = self.rect.height
            elif self.rect.y > self.rect.height:
                self.rect.y = 0
        return None

    def cycle_image(
            self:  ParticleEffect,
            dtime: float,
    ) -> None:
        """Periodically switch to a different random frame for variable effects."""
        self.image_count += dtime
        if isinstance(self.image, list) and self.image_count > ParticleEffect.VARIABLE_IMAGE_DISPLAY_TIME:
            self.image_count = 0
            for i in range(2):
                next_ind = random.randint(0, len(self.image) - 1)
                if self.image_index != next_ind:
                    self.image_index = next_ind
                    break
        return None

    def loop(
            self:  ParticleEffect,
            dtime: float,
    ) -> float:
        """Advance the effect for one frame, scrolling it if it moves."""
        if self.should_move:
            self.move(dtime)
        return 0.0

    def draw(
            self:          ParticleEffect,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float], # noqa - Not used, just here for consistency with other draw methods
    ) -> None:
        """Draw the particle layer, tiling a scrolling layer or scattering a static one."""
        if self.should_move:
            image = self.image[self.image_index] if isinstance(self.image, list) else self.image
            if image:
                coord_x = [self.rect.x - offset_x]
                coord_y = [self.rect.y - offset_y]
                if self.x_vel > 0:
                    coord_x.append(coord_x[0] - self.rect.width)
                elif self.x_vel < 0:
                    coord_x.append(coord_x[0] + self.rect.width)
                if self.y_vel > 0:
                    coord_y.append(coord_y[0] - self.rect.height)
                elif self.y_vel < 0:
                    coord_y.append(coord_y[0] + self.rect.height)
                for x in coord_x:
                    for y in coord_y:
                        win.blit(image, (x, y))
        else:
            if isinstance(self.image, pygame.Surface):
                win.blit(self.image, (0, 0))
            elif isinstance(self.image, list):
                for image in self.image:
                    if random.randint(0, 1) == 1:
                        win.blit(image, (random.randint(-image.get_width(), win.get_width() + image.get_width()), random.randint(-image.get_height(), win.get_height() + image.get_height())))
                return None
        return None


class Rain(ParticleEffect):
    def __init__(
            self:   Rain,
            level:  Level,
            angled: bool = False,
    ) -> None:
        """Initialize a rain particle effect scaled to the level size."""
        color  = (208, 244, 255, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 600
        super().__init__(level, None, 1, 8, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.2)


class Snow(ParticleEffect):
    def __init__(
            self:   Snow,
            level:  Level,
            angled: bool = False,
    ) -> None:
        """Initialize a snow particle effect scaled to the level size."""
        color  = (235, 245, 245, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 1000
        super().__init__(level, None, 3, 3, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.15)


class FilmGrain(ParticleEffect):
    def __init__(
            self:  FilmGrain,
            level: Level,
            win:   pygame.Surface,
    ) -> None:
        """Initialize a static film-grain overlay scaled to the window size."""
        color  = RETRO_WHITE if level.retro else NORMAL_WHITE
        color  = (color[0], color[1], color[2], 200)
        amount = win.get_width() * win.get_height() // 400000
        super().__init__(level, win, 2, 1000, amount, color, effect_type=ParticleType.VARIABLE, should_move=False)
