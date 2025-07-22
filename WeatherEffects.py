import pygame
import random


class ParticleEffect:
    def __init__(self, level, width, height, amount, color, x_vel=0.0, y_vel=0.0):
        self.image = self.generate(width, height, amount, color, level.level_bounds)
        if level.grayscale:
            pygame.transform.grayscale(self.image)
        self.rect = pygame.Rect(0, 0, self.image.get_width(), self.image.get_height())
        self.x_vel = x_vel
        self.y_vel = y_vel

    def generate(self, width, height, amount, color, level_bounds) -> pygame.Surface:
        points = []
        for i in range(amount):
            points.append((random.randint(0, level_bounds[1][0]), random.randint(0, level_bounds[1][1])))

        image = pygame.Surface(level_bounds[1], pygame.SRCALPHA)
        image.set_colorkey((0, 0, 0))
        particle = pygame.Surface((width, height), pygame.SRCALPHA)
        particle.fill(color)
        for point in points:
            image.blit(particle, point)
        return image

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

    def draw(self, win, offset_x, offset_y) -> None:
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))
        if self.y_vel > 0:
            win.blit(self.image, (self.rect.x - offset_x, self.rect.y - self.rect.height - offset_y))
            if self.x_vel > 0:
                win.blit(self.image, (self.rect.x - self.rect.width - offset_x, self.rect.y - offset_y))
                win.blit(self.image, (self.rect.x - self.rect.width - offset_x, self.rect.y - self.rect.height - offset_y))
            elif self.x_vel < 0:
                win.blit(self.image, (self.rect.x + self.rect.width - offset_x, self.rect.y - offset_y))
                win.blit(self.image, (self.rect.x + self.rect.width - offset_x, self.rect.y - self.rect.height - offset_y))
        elif self.y_vel < 0:
            win.blit(self.image, (self.rect.x - offset_x, self.rect.y + self.rect.height - offset_y))
            if self.x_vel > 0:
                win.blit(self.image, (self.rect.x - self.rect.width - offset_x, self.rect.y - offset_y))
                win.blit(self.image, (self.rect.x - self.rect.width - offset_x, self.rect.y + self.rect.height - offset_y))
            elif self.x_vel < 0:
                win.blit(self.image, (self.rect.x + self.rect.width - offset_x, self.rect.y - offset_y))
                win.blit(self.image, (self.rect.x + self.rect.width - offset_x, self.rect.y + self.rect.height - offset_y))
        else:
            if self.x_vel > 0:
                win.blit(self.image, (self.rect.x - self.rect.width - offset_x, self.rect.y - offset_y))
            elif self.x_vel < 0:
                win.blit(self.image, (self.rect.x + self.rect.width - offset_x, self.rect.y - offset_y))


class Rain(ParticleEffect):
    def __init__(self, level, angled=False):
        color = (208, 244, 255, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 600
        super().__init__(level, 1, 8, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.2)


class Snow(ParticleEffect):
    def __init__(self, level, angled=False):
        color = (235, 245, 245, 200)
        amount = level.level_bounds[1][0] * level.level_bounds[1][1] // 1000
        super().__init__(level, 3, 3, amount, color, x_vel=(0.0 if not angled else -0.05), y_vel=0.15)
