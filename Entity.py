from __future__ import annotations
from typing import Any, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level
    from Trigger import Trigger

from Helpers import (
    MovementDirection,
    link_trigger,
)


class Entity(pygame.sprite.Sprite):
    GRAVITY = 1100
    ANIMATION_DELAY = 0.05

    def __init__(
            self:        Entity,
            level:       Level,
            controller:  Controller,
            x:           float | int,
            y:           float | int,
            width:       float | int,
            height:      float | int,
            is_blocking: bool = True,
            name:        str  = "Entity",
    ) -> None:
        super().__init__()
        self.name:          str                      = f"{name} ({x}, {y})"
        self.level:         Level                    = level
        self.controller:    Controller               = controller
        self.sprite:        pygame.Surface | None    = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mask:          pygame.Mask | None       = pygame.mask.from_surface(self.sprite) if self.sprite else None
        self.rect:          pygame.Rect | None       = pygame.Rect(x, y, width, height)
        self.width:         float | int              = width
        self.height:        float | int              = height
        self.is_blocking:   bool                     = is_blocking # This property indicates whether the entity blocks player movement
        self.attack_damage: float | int | None       = None
        self.max_hp:        float | int              = 100
        self.hp:            float | int              = 100
        self.is_stacked:    bool                     = False # this property is only used by blocks, but needed here for generic checks
        self.direction:     MovementDirection | None = None  # this property is only used by actors, but needed here for generic checks
        self.trigger:       str | list[Trigger]      = []
        self.cooldowns:     dict[str, float | int]   = {}

    @property
    def gravity(
            self: Entity,
    ) -> float | int:
        return self.GRAVITY

    def die(
            self: Entity,
    ) -> None:
        self.hp = 0
        return None

    def save(
            self: Entity,
    ) -> dict[str, dict[str, float | int]]:
        return {self.name: {"hp": self.hp}}

    def load(
            self: Entity,
            data: dict[str, Any],
    ) -> None:
        self.load_attribute(data, "hp")
        return None

    def load_attribute(
            self:      Entity,
            data:      dict[str, Any],
            attribute: str,
    ) -> None:
        if data.get(attribute):
            setattr(self, attribute, data[attribute])
        return None

    def update_cooldowns(
            self:  Entity,
            dtime: float | int,
    ) -> None:
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= dtime
            elif self.cooldowns[key] < 0:
                self.cooldowns[key] = 0.0
        return None

    def loop(
            self:  Entity,
            dtime: float | int,
    ) -> float | int:
        if self.cooldowns is not None:
            self.update_cooldowns(dtime)
        if self.hp <= 0 and self.cooldowns and self.cooldowns.get("dead", 0) <= 0:
            self.level.queue_purge(self)
        return 0.0

    def draw(
            self:          Entity,
            win:           pygame.Surface,
            offset_x:      float | int,
            offset_y:      float | int,
            master_volume: dict[str, float | int],
    ) -> None:
        if self.rect and self.sprite:
            adj_x = self.rect.x - offset_x
            adj_y = self.rect.y - offset_y
            if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
                win.blit(self.sprite, (adj_x, adj_y))
        return None

    def collide(
            self: Entity,
            ent:  Entity,
    ) -> bool:
        return self.is_blocking

    def get_hit(
            self: Entity,
            ent:  Entity,
    ) -> None:
        return None

    def set_difficulty(
            self:  Entity,
            scale: float | int,
    ) -> None:
        return None

    def link_triggers(
            self:     Entity,
            triggers: list[Trigger],
    ) -> None:
        if self.trigger and isinstance(self.trigger, str):
            self.trigger = link_trigger(self.trigger.split(" "), triggers)
        return None
