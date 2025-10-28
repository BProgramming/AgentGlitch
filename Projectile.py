import math
import pygame
from Entity import Entity


class Projectile(Entity):
    MAX_SPEED = 1700
    STOCK_PROJECTILE_SIZE = 16

    def __init__(self, level, controller, x, y, target, max_dist, attack_damage, difficulty, speed=MAX_SPEED, stock_size=STOCK_PROJECTILE_SIZE, sprite=None, name=None):
        super().__init__(level, controller, x, y, sprite.get_width(), sprite.get_height(), name=name)
        self.speed = (0.75 * speed * (stock_size / sprite.get_width())) + (0.25 * speed * difficulty * (stock_size / sprite.get_width()))
        self.max_dist = max_dist
        if target is None:
            target = (x, y)
        delta = max_dist / math.dist(self.rect.center, target)
        self.dest = (((1 - delta) * self.rect.centerx) + (delta * target[0]), ((1 - delta) * self.rect.centery) + (delta * target[1]))
        self.sprite = sprite
        self.angle = math.degrees(math.atan2(self.dest[1] - self.rect.centery, self.dest[0] - self.rect.centerx))
        self.sprite = pygame.transform.rotate(self.sprite, self.angle)
        self.mask = pygame.mask.from_surface(self.sprite)
        self.attack_damage = attack_damage

    def save(self) -> dict:
        return {self.name: {"hp": self.hp, "cached x y": (self.rect.x, self.rect.y), "speed": self.speed, "max_dist": self.max_dist, "dest": self.dest, "angle": self.angle}}

    def load(self, ent) -> None:
        self.hp = ent["hp"]
        self.rect.x, self.rect.y = ent["cached x y"]
        self.speed = ent["speed"]
        self.max_dist = ent["max_dist"]
        self.dest = ent["dest"]
        self.angle = ent["angle"]

    def move(self, speed) -> None:
        if self.rect.colliderect(self.level.player) and pygame.sprite.collide_mask(self, self.level.player):
            self.collide(None)
            self.level.player.get_hit(self)
            return

        for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only=True):
            if self.rect.colliderect(ent.rect):
                if pygame.sprite.collide_mask(self, ent):
                    self.rect.center = ent.rect.center
                    self.collide(None)
                    return

        dist = math.dist(self.rect.center, self.dest)
        if dist < speed:
            self.rect.center = self.dest
            self.hp = 0
        else:
            delta = speed / dist
            self.rect.center = [((1 - delta) * self.rect.centerx) + (delta * self.dest[0]), ((1 - delta) * self.rect.centery) + (delta * self.dest[1])]

    def loop(self, dtime) -> None:
        self.move(self.speed * dtime * (0.5 if self.level.player is not None and self.level.player.is_slow_time else 1))

    def collide(self, ent) -> bool:
        self.hp = 0
        return True

    def set_difficulty(self, scale) -> None:
        self.speed = (0.75 * self.speed) + (0.25 * self.speed * scale)
