import math
import pygame
from Entity import Entity


class Projectile(Entity):
    MAX_SPEED = 1700
    STOCK_PROJECTILE_SIZE = 16

    def __init__(self, level, controller, x, y, target, max_dist, attack_damage, difficulty, speed=MAX_SPEED, stock_size=STOCK_PROJECTILE_SIZE, sprite=None, name=None):
        super().__init__(level, controller, x, y, sprite.get_width(), sprite.get_height(), name=name)
        self.rect.center = (int(x), int(y))
        self.speed = (0.75 * speed * (stock_size / sprite.get_width())) + (0.25 * speed * difficulty * (stock_size / sprite.get_width()))
        self.max_dist = max_dist
        if target is None:
            self.target = (x * 2, y * 2)
        else:
            self.target = target
        self.clamp_target()
        self.sprite = sprite
        self.angle = math.degrees(math.atan2(self.target[1] - self.rect.centery, self.target[0] - self.rect.centerx))
        self.sprite = pygame.transform.rotate(self.sprite, self.angle)
        self.mask = pygame.mask.from_surface(self.sprite)
        self.attack_damage = attack_damage

    def save(self) -> dict:
        return {self.name: {"hp": self.hp, "cached x y": (self.rect.x, self.rect.y), "speed": self.speed, "max_dist": self.max_dist, "angle": self.angle}}

    def load(self, ent) -> None:
        self.hp = ent["hp"]
        self.rect.x, self.rect.y = ent["cached x y"]
        self.speed = ent["speed"]
        self.max_dist = ent["max_dist"]
        self.clamp_target()
        self.angle = ent["angle"]

    def __lerp_point__(self, a: float | int, b: float | int, weight: float | int):
        return a + ((b - a) * weight)

    def lerp(self, a: tuple[float | int, float | int], b: tuple[float | int, float | int], weight: float | int) -> tuple[float | int, float | int]:
        return self.__lerp_point__(a[0], b[0], weight), self.__lerp_point__(a[1], b[1], weight)

    def clamp_target(self) -> None:
        self.target = self.lerp(self.rect.center, self.target, self.max_dist / max(1.0, math.dist(self.rect.center, self.target)))

    def move(self, speed) -> None:
        if self.rect.colliderect(self.level.player) and pygame.sprite.collide_mask(self, self.level.player):
            self.collide(self.level.player)
            self.level.player.get_hit(self)
            return

        for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only=True):
            if self.rect.colliderect(ent.rect):
                if pygame.sprite.collide_mask(self, ent):
                    self.collide(ent)
                    return

        self.rect.center = self.lerp(self.rect.center, self.target, speed / math.dist(self.rect.center, self.target))
        TOLERANCE = 1
        if abs(math.dist(self.rect.center, self.target)) <= TOLERANCE:
            self.hp = 0

    def loop(self, dtime) -> None:
        self.move(self.speed * dtime * (0.5 if self.level.player is not None and self.level.player.is_slow_time else 1))

    def collide(self, ent) -> bool:
        self.hp = 0
        return True

    def set_difficulty(self, scale) -> None:
        self.speed = (0.75 * self.speed) + (0.25 * self.speed * scale)
