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
    GRAVITY         = 1100
    ANIMATION_DELAY = 0.05

    def __init__(
            self:        Entity,
            level:       Level,
            controller:  Controller,
            x:           float,
            y:           float,
            width:       float,
            height:      float,
            is_blocking: bool = True,
            name:        str  = "Entity",
    ) -> None:
        """Initialize the entity's sprite, geometry, and generic gameplay attributes."""
        super().__init__()
        self.name:          str        = f"{name} ({x}, {y})"
        self.level:         Level      = level
        self.controller:    Controller = controller

        self.sprite:        pygame.Surface | None = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mask:          pygame.Mask | None    = pygame.mask.from_surface(self.sprite) if self.sprite else None
        self.rect:          pygame.Rect | None    = pygame.Rect(x, y, width, height)
        self.width:         float                 = width
        self.height:        float                 = height

        self.is_blocking:   bool         = is_blocking  # whether the entity blocks player movement
        self.is_stacked:    bool         = False  # only used by blocks, but needed here for generic checks
        self.attack_damage: float | None = None
        self.max_hp:        float        = 100
        self.hp:            float        = 100

        self.direction:     MovementDirection | None = None   # only used by actors, but needed here for generic checks
        self.trigger:       str | list[Trigger]      = []
        self.abilities:     dict[str, bool]          = {}
        self.cooldowns:     dict[str, float]         = {}

        self.purgeable_on_load: bool = False

    @property
    def gravity(
            self: Entity,
    ) -> float:
        """Return the entity's gravity acceleration."""
        return self.GRAVITY

    def die(
            self: Entity,
    ) -> float:
        """Set hp to zero and return any frame-time offset incurred."""
        self.hp = 0
        return 0.0

    def save(
            self: Entity,
    ) -> dict[str, dict[str, float]]:
        """Return a serializable dict of the entity's persistent state."""
        return {self.name: {"hp": self.hp}}

    def load(
            self: Entity,
            data: dict[str, Any],
    ) -> None:
        """Restore the entity's state from saved data."""
        self.load_attribute(data, "hp")
        return None

    def load_attribute(
            self:      Entity,
            data:      dict[str, Any],
            attribute: str,
    ) -> None:
        """Set an attribute from saved data if a truthy value is present."""
        if data.get(attribute):
            setattr(self, attribute, data[attribute])
        return None

    def update_cooldowns(
            self:  Entity,
            dtime: float,
    ) -> None:
        """Decrement all active cooldowns by the elapsed time, clamping at zero."""
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= dtime
            elif self.cooldowns[key] < 0:
                self.cooldowns[key] = 0.0
        return None

    def loop(
            self:  Entity,
            dtime: float,
    ) -> float:
        """Advance the entity by one frame and queue it for purging if dead."""
        if self.cooldowns is not None:
            self.update_cooldowns(dtime)
        if self.hp <= 0 and self.cooldowns and self.cooldowns.get("dead", 0) <= 0:
            self.level.queue_purge(self)
        return 0.0

    def draw(
            self:          Entity,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float],
    ) -> None:
        """Blit the entity's sprite to the window if it is within view."""
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
        """Return whether this entity blocks the colliding entity."""
        return self.is_blocking

    def get_hit(
            self: Entity,
            ent:  Entity,
    ) -> float:
        """Handle being hit by another entity (no-op for the base entity)."""
        return 0.0

    def set_difficulty(
            self:  Entity,
            scale: float,
    ) -> None:
        """Apply a difficulty scale to the entity (no-op for the base entity)."""
        return None

    def link_triggers(
            self:     Entity,
            triggers: list[Trigger],
    ) -> None:
        """Resolve this entity's trigger name references into Trigger objects."""
        if self.trigger and isinstance(self.trigger, str):
            self.trigger = link_trigger(self.trigger.split(" "), triggers)
        return None
