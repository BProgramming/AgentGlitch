import pygame
import random
from enum import Enum

from Helpers import retroify_image


class ParticleType(Enum):
    STATIC = 0
    VARIABLE = 1


class ParticleEffect:
    VARIABLE_IMAGE_DISPLAY_TIME = 100

    def __init__(self, level, win, width: int, height: int, amount: int, color: tuple[int, int, int, int], x_vel: float=0.0, y_vel: float=0.0, effect_type: ParticleType=ParticleType.STATIC, should_move: bool=True):
        self.effect_type = effect_type
        self.image: pygame.Surface | list[pygame.Surface] | None = None
        self.image_index: int = 0
        self.image_count: int = 0
        self.should_move: bool = should_move
        if self.should_move or win is None:
            bounds: tuple[tuple[int, int], tuple[int, int]] = level.level_bounds
        else:
            bounds: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (win.get_width(), win.get_height()))
        if self.effect_type == ParticleType.STATIC:
            self.image = self.generate_static_effect(width, height, amount, color, bounds, level.retro)
        elif self.effect_type == ParticleType.VARIABLE:
            self.image = self.generate_variable_effect(width, height, amount, color, bounds, level.retro)
        self.rect: pygame.Rect = pygame.Rect(0, 0, bounds[1][0], bounds[1][1])
        self.x_vel: float = x_vel
        self.y_vel: float = y_vel

    @property
    def type(self):
        return self.effect_type

    @staticmethod
    def generate_static_effect(width, height, amount, color, bounds, is_retro) -> pygame.Surface:
        points = []
        for i in range(amount):
            points.append((random.randint(0, bounds[1][0]), random.randint(0, bounds[1][1])))

        image = pygame.Surface(bounds[1], pygame.SRCALPHA)
        image.set_colorkey((0, 0, 0))
        particle = pygame.Surface((width, height), pygame.SRCALPHA)
        particle.fill(color)
        if is_retro:
            particle = retroify_image(particle)

        for point in points:
            image.blit(particle, point)

        return image

    @staticmethod
    def generate_variable_effect(width, height, amount, color, bounds, is_retro) -> list[pygame.Surface]:
        images = []
        min_screens = 12
        max_screens = 24
        for i in range(random.randint(min_screens, max_screens)):
            points = []
            for j in range(random.randint(0, amount)):
                points.append((random.randint(0, bounds[1][0]), random.randint(0, bounds[1][1])))

            image = pygame.Surface(bounds[1], pygame.SRCALPHA)
            image.set_colorkey((0, 0, 0))

            for point in points:
                if random.randint(0, 1) == 0:
                    rand_width = random.randint(1, width) * random.randint(1, width)
                    particle = pygame.Surface((rand_width, rand_width), pygame.SRCALPHA)
                    pygame.draw.circle(particle, color, (rand_width / 2, rand_width / 2), rand_width)
                else:
                    particle = pygame.Surface((random.randint(0, width), random.randint(0, height)), pygame.SRCALPHA)
                    particle.fill(color)
                if is_retro:
                    particle = retroify_image(particle)
                image.blit(particle, point)
            images.append(image)

        return images

    def move(self, dtime) -> None:
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

    def cycle_image(self, dtime):
        self.image_count += dtime
        if self.image_count > ParticleEffect.VARIABLE_IMAGE_DISPLAY_TIME:
            self.image_count = 0
            self.image_index += 1
            if self.image_index >= len(self.image):
                self.image_index = 0

    def loop(self, dtime):
        if self.should_move:
            self.move(dtime)
        if isinstance(self.image, list):
            self.cycle_image(dtime)

    def draw(self, win, offset_x, offset_y, master_volume, fps) -> None:
        if self.should_move:
            image = self.image[self.image_index] if isinstance(self.image, list) else self.image
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
                win.blit(self.image[self.image_index], (0, 0))


class Rain(ParticleEffect):
    def __init__(self, level, angled=False):
        color = (208, 244, 255, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 600
        super().__init__(level, None, 1, 8, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.2)


class Snow(ParticleEffect):
    def __init__(self, level, angled=False):
        color = (235, 245, 245, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 1000
        super().__init__(level, None, 3, 3, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.15)


class FilmGrain(ParticleEffect):
    def __init__(self, level, win):
        color = (255, 255, 255, 200)
        amount = win.get_width() * win.get_height() // 100000
        super().__init__(level, win, 2, 1000, amount, color, effect_type=ParticleType.VARIABLE, should_move=False)