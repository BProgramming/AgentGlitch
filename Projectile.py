import math
import pygame
from Object import Object


class Projectile(Object):
    MAX_SPEED = 100
    STOCK_PROJECTILE_SIZE = 16

    def __init__(self, x, y, target, max_dist, attack_damage, difficulty, speed=MAX_SPEED, stock_size=STOCK_PROJECTILE_SIZE, sprite=None, name=None):
        super().__init__(x, y, sprite.get_width(), sprite.get_height(), name=name)
        self.speed = (0.75 * speed * (stock_size / sprite.get_width())) + (0.25 * speed * difficulty * (stock_size / sprite.get_width()))
        self.max_dist = max_dist
        if target is None:
            target = (x, y)
        delta = max_dist / math.dist(self.rect.center, target)
        self.dest = (((1 - delta) * self.rect.centerx) + (delta * target[0]), ((1 - delta) * self.rect.centery) + (delta * target[1]))
        self.sprite = sprite
        self.angle = math.degrees(math.atan2(self.dest[1] - self.rect.centery, self.dest[0] - self.rect.centerx))
        self.sprite = pygame.transform.rotate(self.sprite, self.angle)
        self.attack_damage = attack_damage

    def save(self):
        return {self.name: {"hp": self.hp, "cached x y": (self.rect.x, self.rect.y), "speed": self.speed, "max_dist": self.max_dist, "dest": self.dest, "angle": self.angle}}

    def load(self, obj):
        self.hp = obj["hp"]
        self.rect.x, self.rect.y = obj["cached x y"]
        self.speed = obj["speed"]
        self.max_dist = obj["max_dist"]
        self.dest = obj["dest"]
        self.angle = obj["angle"]

    def move(self, speed, objects):
        for obj in objects:
            if self.rect.colliderect(obj.rect):
                if obj.rect.collidepoint(self.rect.center):
                    self.rect.center = obj.rect.center
                    self.collide(obj)
                    if obj.name == "Player":
                        obj.get_hit(self)
                    return
        dist = math.dist(self.rect.center, self.dest)
        if dist < speed:
            self.rect.center = self.dest
            self.hp = 0
        else:
            delta = speed / dist
            self.rect.center = [((1 - delta) * self.rect.centerx) + (delta * self.dest[0]), ((1 - delta) * self.rect.centery) + (delta * self.dest[1])]

    def loop(self, fps, dtime, objects):
        self.move(self.speed * (dtime / fps) * (0.5 if self.player is not None and self.player.is_slow_time else 1), objects)

    def collide(self, obj):
        self.hp = 0
        obj.get_hit(self)
        return True

    def set_difficulty(self, scale):
        self.speed = (0.75 * self.speed) + (0.25 * self.speed * scale)
