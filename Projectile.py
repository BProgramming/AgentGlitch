from __future__ import annotations
from typing import TYPE_CHECKING
import math
import pygame
from Entity import Entity

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class Projectile(Entity):
    MAX_SPEED             = 1700
    STOCK_PROJECTILE_SIZE = 16
    PIXEL_DIST_TOLERANCE  = 1

    def __init__(
            self:          Projectile,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            target:        tuple[float, float] | None,
            max_dist:      float,
            attack_damage: float,
            difficulty:    float,
            speed:         float                 = MAX_SPEED,
            stock_size:    int                   = STOCK_PROJECTILE_SIZE,
            sprite:        pygame.Surface | None = None,
            name:          str                   = "Projectile",
    ) -> None:
        """Initialize a projectile aimed at a target, scaling speed by sprite size and difficulty."""
        super().__init__(level, controller, x, y, sprite.get_width() if sprite else 0, sprite.get_height() if sprite else 0, name = name)
        self.rect.center = (int(x), int(y))
        self.speed       = (0.75 * speed * (stock_size / sprite.get_width())) + (0.25 * speed * difficulty * (stock_size / sprite.get_width())) if sprite else 0
        self.max_dist    = max_dist
        if target is None:
            self.target = (x * 2, y * 2)
        else:
            self.target = target
        self.clamp_target()
        self.sprite        = sprite
        self.angle         = math.degrees(math.atan2(self.target[1] - self.rect.centery, self.target[0] - self.rect.centerx)) if self.rect else 0
        self.sprite        = pygame.transform.rotate(self.sprite, self.angle) if self.sprite else None
        self.mask          = pygame.mask.from_surface(self.sprite) if self.sprite else None
        self.attack_damage = attack_damage

    def save(
            self: Projectile,
    ) -> dict:
        """Return a serializable dict of the projectile's persistent state."""
        return {self.name: {"hp": self.hp, "cached x y": (self.rect.x, self.rect.y), "speed": self.speed, "max_dist": self.max_dist, "angle": self.angle}} if self.rect else {}

    def load(
            self: Projectile,
            ent:  dict,
    ) -> None:
        """Restore the projectile's state from saved data."""
        self.hp                  = ent["hp"]
        self.rect.x, self.rect.y = ent["cached x y"]
        self.speed               = ent["speed"]
        self.max_dist            = ent["max_dist"]
        self.clamp_target()
        self.angle               = ent["angle"]
        return None

    @staticmethod
    def __lerp_point__( # noqa
            a:      float,
            b:      float,
            weight: float,
    ) -> int:
        """Linearly interpolate between two scalars by the given weight."""
        return int(a + ((b - a) * weight))

    def lerp( # noqa
            self:   Projectile,
            a:      tuple[float, float],
            b:      tuple[float, float],
            weight: float,
    ) -> tuple[int, int]:
        """Linearly interpolate between two points by the given weight."""
        return self.__lerp_point__(a[0], b[0], weight), self.__lerp_point__(a[1], b[1], weight)

    def clamp_target(
            self: Projectile,
    ) -> None:
        """Clamp the target to the projectile's maximum travel distance."""
        if self.rect:
            dist = math.dist(self.rect.center, self.target)
            if dist != 0:
                self.target = self.lerp(self.rect.center, self.target, self.max_dist / dist)
        return None

    def move(
            self:  Projectile,
            speed: float,
    ) -> None:
        """Advance toward the target, resolving collisions with the player or blocks."""
        if self.rect and self.level and self.level.player and self.level.player.rect:
            if self.rect.colliderect(self.level.player) and pygame.sprite.collide_mask(self, self.level.player): # noqa
                self.collide(self.level.player)
                self.level.player.get_hit(self)
                return None

            for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only=True):
                if self.rect.colliderect(ent.rect):
                    if pygame.sprite.collide_mask(self, ent): # noqa
                        self.collide(ent)
                        return None

            dist = math.dist(self.rect.center, self.target)
            if dist != 0:
                self.rect.center = self.lerp(self.rect.center, self.target, speed / dist)

            if abs(math.dist(self.rect.center, self.target)) <= self.PIXEL_DIST_TOLERANCE:
                self.die()

        return None

    def loop(
            self:  Projectile,
            dtime: float,
    ) -> float:
        """Move the projectile for one frame, slowing it during bullet time."""
        self.move(self.speed * dtime * (0.5 if self.level.player is not None and self.level.player.is_slow_time else 1))
        return 0.0

    def collide(
            self: Projectile,
            ent:  Entity,
    ) -> bool:
        """Destroy the projectile on collision."""
        self.die()
        return True

    def set_difficulty(
            self:  Projectile,
            scale: float,
    ) -> None:
        """Rescale the projectile's speed toward the new difficulty."""
        self.speed = (0.75 * self.speed) + (0.25 * self.speed * scale)
        return None
