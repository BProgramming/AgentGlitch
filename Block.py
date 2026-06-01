from __future__ import annotations
from typing import TYPE_CHECKING
import math
import random
import pygame
from pathlib import Path
from Entity import Entity
from Helpers import (
    handle_exception,
    MovementDirection,
    load_sprite_sheets,
    set_sound_source,
    ASSETS_FOLDER,
    image_to_retro,
    PathPoint,
)
from SimpleVFX.SimpleVFX import VisualEffect, ImageDirection

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class Block(Entity):
    def __init__(
            self:         Block,
            level:        Level,
            controller:   Controller,
            x:            float,
            y:            float,
            width:        float,
            height:       float,
            image_master: dict,
            audios:       dict,
            is_stacked:   bool,
            coord_x:      int  = 0,
            coord_y:      int  = 0,
            is_blocking:  bool = True,
            name:         str  = "Block",
    ) -> None:
        """Initialize a static block from the terrain sheet at the given tile coordinates."""
        super().__init__(level, controller, x, y, width, height, is_blocking = is_blocking, name = name)
        self.sprite     = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, coord_x, coord_y, retro = self.level.retro)
        self.mask       = pygame.mask.from_surface(self.sprite) if self.sprite else None
        self.is_stacked = is_stacked
        self.audios     = audios

    @property
    def gravity(
            self: Block,
    ) -> float:
        """Return the block's (greatly reduced) gravity acceleration."""
        return super().gravity * 0.01

    def save(
            self: Block,
    ) -> dict | None:
        """Return the block's saved state, or None if it is undamaged."""
        if self.hp != 0:
            return super().save()
        else:
            return None

    def play_sound(
            self: Block,
            name: str,
    ) -> None:
        """Play a named sound effect positioned relative to the player."""
        if self.audios.get(name.upper()) is not None:
            active_audio_channel = pygame.mixer.find_channel()
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[name.upper()][random.randrange(len(self.audios[name.upper()]))])
                set_sound_source(self.rect, self.level.player.rect, self.controller.master_volume["non-player"], active_audio_channel)
        return None

    @staticmethod
    def load_image(
            path:         Path,
            width:        float,
            height:       float,
            image_master: dict,
            coord_x:      int,
            coord_y:      int,
            retro:        bool = False,
    ) -> pygame.Surface | None:
        """Load and cache a block-sized slice of the terrain sheet, applying retro tinting if needed."""
        path = Path(path)
        if path.is_file():
            retro_path = path.with_name(path.stem + "_retro.png")
            if retro and retro_path.is_file():
                path = retro_path
            if image_master.get(path) is None:
                image_master[path] = pygame.image.load(path).convert_alpha()
            surface = pygame.Surface((width // 2, height // 2), pygame.SRCALPHA)
            rect    = pygame.Rect(coord_x, coord_y, width // 2, height // 2)
            surface.blit(image_master[path], (0, 0), rect)
            if retro:
                surface = image_to_retro(surface)
            return pygame.transform.scale2x(surface)
        else:
            handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
            return None


class BreakableBlock(Block):
    GET_HIT_COOLDOWN = 1
    BREAK_EFFECT     = 0.05

    def __init__(
            self:         BreakableBlock,
            level:        Level,
            controller:   Controller,
            x:            float,
            y:            float,
            width:        float,
            height:       float,
            image_master: dict,
            audios:       dict,
            is_stacked:   bool,
            coord_x:      int = 0,
            coord_y:      int = 0,
            coord_x2:     int = 0,
            coord_y2:     int = 0,
            name:         str = "BreakableBlock",
    ) -> None:
        """Initialize a breakable block with both intact and damaged terrain sprites."""
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x = coord_x, coord_y = coord_y, name = name)
        self.sprite_damaged = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, coord_x2, coord_y2, retro = self.level.retro)
        self.cooldowns.update({"get_hit": 0})
        self.purgeable_on_load = True

    def get_hit(
            self: BreakableBlock,
            ent:  Entity,
    ) -> float:
        """Damage the block on the first hit and destroy it on the second."""
        dtime_offset = 0.0
        if self.rect and self.cooldowns["get_hit"] <= 0:
            if self.hp == self.max_hp:
                self.hp     = self.max_hp // 2
                self.sprite = self.sprite_damaged
                self.mask   = pygame.mask.from_surface(self.sprite) if self.sprite else None
                self.cooldowns["get_hit"] += BreakableBlock.GET_HIT_COOLDOWN
            else:
                dtime_offset += self.die()
                self.level.visual_effects_manager.spawn( # noqa
                    VisualEffect(
                        self,
                        self.level.visual_effects_manager.image_master, # noqa
                        image_name = "BREAKBURST",
                        alpha      = 128,
                        scale      = (self.rect.width, self.rect.height),
                    ),
                    time = BreakableBlock.BREAK_EFFECT,
                )
            self.play_sound("smash_box")
        return dtime_offset


class MovingBlock(Block):
    VELOCITY_TARGET = 500
    PATH_STOP_TIME  = 1

    def __init__(
            self:               MovingBlock,
            level:              Level,
            controller:         Controller,
            x:                  float,
            y:                  float,
            width:              float,
            height:             float,
            image_master:       dict,
            audios:             dict,
            is_stacked:         bool,
            is_enabled:         bool                   = True,
            hold_for_collision: bool                   = False,
            speed:              float                  = VELOCITY_TARGET,
            path:               list[PathPoint] | None = None,
            coord_x:            int                    = 0,
            coord_y:            int                    = 0,
            is_blocking:        bool                   = True,
            name:               str                    = "MovingBlock",
    ) -> None:
        """Initialize a block that travels along a path and pushes actors it touches."""
        Block.__init__(
            self,
            level,
            controller,
            x,
            y,
            width,
            height,
            image_master,
            audios,
            is_stacked,
            coord_x     = coord_x,
            coord_y     = coord_y,
            is_blocking = is_blocking,
            name        = name,
        )
        self.speed             = speed
        self.is_enabled        = is_enabled
        self.hold              = hold_for_collision
        self.patrol_path       = path
        self.patrol_path_index = 0
        if self.patrol_path and self.rect:
            min_dist = math.dist((self.rect.x, self.rect.y), (self.patrol_path[0].x, self.patrol_path[0].y))
            for i in range(len(self.patrol_path)):
                dist = math.dist((self.rect.x, self.rect.y), (self.patrol_path[i].x, self.patrol_path[i].y))
                if dist < min_dist:
                    self.patrol_path_index = i
            self.direction = self.facing = (MovementDirection.RIGHT if self.patrol_path[self.patrol_path_index].x - self.rect.x > 0 else MovementDirection.LEFT)
        self.x_vel = self.y_vel = 0.0
        self.should_move_horiz = self.should_move_vert = True
        self.cooldowns.update({"wait": 0.0})

    def increment_patrol_index(
            self: MovingBlock,
    ) -> None:
        """Advance the path index, reversing direction at either end of the path."""
        if self.patrol_path:
            if self.patrol_path_index < 0:
                self.patrol_path_index -= 1
            elif self.patrol_path_index >= 0:
                self.patrol_path_index += 1
            if self.patrol_path_index >= len(self.patrol_path) - 1:
                self.patrol_path_index = -1
            elif self.patrol_path_index <= -len(self.patrol_path):
                self.patrol_path_index = 0
        return None

    def patrol(
            self:  MovingBlock,
            dtime: float,
    ) -> None:
        """Move toward the current waypoint, pausing at flagged wait points."""
        self.should_move_horiz = self.should_move_vert = False
        if self.rect and self.patrol_path and self.cooldowns["wait"] <= 0:
            target_x = self.patrol_path[self.patrol_path_index].x - self.rect.x
            if target_x != 0:
                self.direction = (MovementDirection.RIGHT if target_x >= 0 else MovementDirection.LEFT)
                if self.direction:
                    self.x_vel     = min(abs(target_x) / dtime, abs(self.speed)) * float(self.direction)
                    self.should_move_horiz = True

            target_y = self.patrol_path[self.patrol_path_index].y - self.rect.y
            if target_y != 0:
                self.y_vel = min(abs(target_y) / dtime, abs(self.speed)) * (1 if target_y >= 0 else -1)
                self.should_move_vert = True

            if not self.should_move_horiz and not self.should_move_vert:
                if self.patrol_path[self.patrol_path_index].wait:
                    self.cooldowns["wait"] = MovingBlock.PATH_STOP_TIME
                self.increment_patrol_index()
        return None

    def collide(
            self: MovingBlock,
            ent:  Entity,
    ) -> bool:
        """Transfer this block's velocity to a pushable colliding entity."""
        if self.hold and self.is_enabled and ent == self.level.player:
            self.hold = False
        if (hasattr(ent, "push_x") and ent.rect and self.rect and
                (ent.rect.y < self.rect.y or
                 (hasattr(ent, "is_wall_jumping") and ent.is_wall_jumping) or
                 (ent.rect.x >= self.rect.x and ent.direction == self.direction == MovementDirection.RIGHT) or
                 (ent.rect.x <= self.rect.x and ent.direction == self.direction == MovementDirection.LEFT))):
            ent.push_x = self.x_vel
        if hasattr(ent, "push_y"):
            ent.push_y = self.y_vel
        return self.is_blocking

    def move(
            self: MovingBlock,
            dx:   float,
            dy:   float,
    ) -> None:
        """Move the block by the given deltas, clamping to level bounds and the current waypoint."""
        if self.rect:
            if dx != 0:
                if self.rect.left + dx < self.level.level_bounds[0][0]:
                    self.rect.left = self.rect.width
                    self.x_vel     = 0.0
                elif self.rect.right + dx > self.level.level_bounds[1][0]:
                    self.rect.right = self.level.level_bounds[1][0] - self.rect.width
                    self.x_vel      = 0.0
                else:
                    self.rect.x += dx

            if dy != 0:
                if self.rect.top + dy < self.level.level_bounds[0][1]:
                    self.y_vel *= -0.5
                elif self.rect.top + dy > self.level.level_bounds[1][1]:
                    self.x_vel = 0.0
                elif self.patrol_path:
                    target = self.rect.y + dy
                    if self.y_vel > 0 and target > self.patrol_path[self.patrol_path_index].y:
                        self.rect.y = int(self.patrol_path[self.patrol_path_index].y)
                    elif self.y_vel < 0 and target < self.patrol_path[self.patrol_path_index].y:
                        self.rect.y = int(self.patrol_path[self.patrol_path_index].y)
                    else:
                        self.rect.y = int(target)
        return None

    def loop(
            self:  MovingBlock,
            dtime: float,
    ) -> float:
        """Advance the block's motion for one frame and run the base entity loop."""
        if self.is_enabled and not self.hold:
            if not self.should_move_horiz:
                self.x_vel = 0.0

            if not self.should_move_vert:
                self.y_vel = 0.0

            if self.x_vel != 0 or self.y_vel != 0:
                if self.level.player.is_slow_time:
                    self.x_vel /= 2
                    self.y_vel /= 2

                self.move(self.x_vel * dtime, self.y_vel * dtime)
        return super().loop(dtime)


class Door(MovingBlock):
    VELOCITY_TARGET = 500

    def __init__(
            self:             Door,
            level:            Level,
            controller:       Controller,
            x:                float,
            y:                float,
            width:            float,
            height:           float,
            image_master:     dict,
            audios:           dict,
            is_stacked:       bool,
            speed:            float      = VELOCITY_TARGET,
            direction:        int        = -1,
            is_locked:        bool       = False,
            coord_x:          int        = 0,
            coord_y:          int        = 0,
            locked_coord_x:   int | None = None,
            locked_coord_y:   int | None = None,
            unlocked_coord_x: int | None = None,
            unlocked_coord_y: int | None = None,
            name:             str        = "Door",
    ) -> None:
        """Initialize a sliding door with optional distinct locked and unlocked sprites."""
        super().__init__(
            level,
            controller,
            x,
            y,
            width,
            height,
            image_master,
            audios,
            is_stacked,
            speed   = speed,
            coord_x = coord_x,
            coord_y = coord_y,
            name    = name,
        )
        if is_locked:
            self.is_locked = True
            if locked_coord_x is not None and locked_coord_y is not None and unlocked_coord_x is not None and unlocked_coord_y is not None:
                self.locked_sprite   = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, locked_coord_x, locked_coord_y, retro = self.level.retro)
                self.locked_mask     = pygame.mask.from_surface(self.locked_sprite) if self.locked_sprite else None
                self.unlocked_sprite = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, unlocked_coord_x, unlocked_coord_y, retro = self.level.retro)
                self.unlocked_mask   = pygame.mask.from_surface(self.unlocked_sprite) if self.unlocked_sprite else None
                self.sprite          = self.locked_sprite
                self.mask            = self.locked_mask
            else:
                self.locked_sprite = self.unlocked_sprite = self.sprite
                self.locked_mask   = self.unlocked_mask   = self.mask
        else:
            self.is_locked = False
            if locked_coord_x is not None and locked_coord_y is not None and unlocked_coord_x is not None and unlocked_coord_y is not None:
                self.locked_sprite   = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, locked_coord_x, locked_coord_y, retro = self.level.retro)
                self.locked_mask     = pygame.mask.from_surface(self.locked_sprite) if self.locked_sprite else None
                self.unlocked_sprite = self.load_image(ASSETS_FOLDER / "Terrain" / "Terrain.png", width, height, image_master, unlocked_coord_x, unlocked_coord_y, retro = self.level.retro)
                self.unlocked_mask   = pygame.mask.from_surface(self.unlocked_sprite) if self.unlocked_sprite else None
                self.sprite          = self.unlocked_sprite
                self.mask            = self.unlocked_mask
            else:
                self.locked_sprite = self.unlocked_sprite = self.sprite
                self.locked_mask   = self.unlocked_mask   = self.mask
        self.patrol_path_open   = [PathPoint(x, y + (height * direction))]
        self.patrol_path_closed = [PathPoint(x, y)]
        self.is_open            = False
        self.direction          = self.facing = MovementDirection.LEFT

    def open(
            self: Door,
    ) -> None:
        """Open the door if unlocked, playing the appropriate sound."""
        if not self.is_locked:
            self.patrol_path = self.patrol_path_open
            self.is_open     = True
            self.play_sound("door")
        else:
            self.play_sound("door_locked")
        return None

    def close(
            self: Door,
    ) -> None:
        """Close the door and play the door sound."""
        self.patrol_path = self.patrol_path_closed
        self.is_open     = False
        self.play_sound("door")
        return None

    def toggle_open(
            self: Door,
    ) -> None:
        """Toggle the door open or closed (only opening if unlocked)."""
        if self.is_open:
            self.close()
        elif not self.is_locked:
            self.open()
        return None

    def unlock(
            self: Door,
    ) -> None:
        """Unlock the door and switch to its unlocked sprite."""
        self.is_locked = False
        self.sprite    = self.unlocked_sprite
        self.mask      = self.unlocked_mask
        return None

    def lock(
            self: Door,
    ) -> None:
        """Lock the door and switch to its locked sprite."""
        self.is_locked = True
        self.sprite    = self.locked_sprite
        self.mask      = self.locked_mask
        return None

    def toggle_lock(
            self: Door,
    ) -> None:
        """Toggle the door's locked state."""
        if self.is_locked:
            self.unlock()
        else:
            self.lock()
        return None

    def collide(
            self: Door,
            ent:  Entity,
    ) -> bool:
        """Open the door for entities that can open doors and are touching it from below."""
        if ent.abilities and ent.abilities.get("can_open_doors") is not None and ent.abilities["can_open_doors"] and ent.rect and self.rect and ent.rect.bottom > self.rect.top:
            self.open()
        return True

    def loop(
            self:  Door,
            dtime: float,
    ) -> float:
        """Sync the door's sprite to its lock state and close it once the player is far away."""
        if (self.is_locked and self.sprite == self.unlocked_sprite) or (not self.is_locked and self.sprite == self.locked_sprite):
            self.is_locked = not self.is_locked
            self.toggle_lock()
        if not self.is_open and self.rect and self.rect.y == self.patrol_path_closed[0].y:
            return 0.0
        else:
            if self.rect and self.level.player.rect and math.dist((self.level.player.rect.centerx, self.level.player.rect.centery), (self.rect.centerx, self.rect.centery)) > math.sqrt(self.rect.height ** 2 + (1.5 * self.rect.width) ** 2):
                self.close()
            return super().loop(dtime)


class MovableBlock(Block):
    def __init__(
            self:         MovableBlock,
            level:        Level,
            controller:   Controller,
            x:            float,
            y:            float,
            width:        float,
            height:       float,
            image_master: dict,
            audios:       dict,
            is_stacked:   bool,
            coord_x:      int = 0,
            coord_y:      int = 0,
            name:         str = "MovableBlock",
    ) -> None:
        """Initialize a player-pushable block that resets if it falls off the map."""
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x = coord_x, coord_y = coord_y, name = name)
        self.start_x, self.start_y = int(x), int(y)
        self.x_vel = self.y_vel = self.push_x = self.push_y = 0.0
        self.should_move_horiz = self.should_move_vert = True

    def collide(
            self: MovableBlock,
            ent:  Entity,
    ) -> bool:
        """Transfer this block's velocity to a pushable colliding entity."""
        if hasattr(ent, "push_x"):
            ent.push_x = self.x_vel
        if hasattr(ent, "push_y") and self.rect and ent.rect and self.rect.top >= ent.rect.bottom:
            ent.push_y = self.y_vel
        return True

    def get_collisions(
            self: MovableBlock,
    ) -> None:
        """Resolve collisions against nearby blocks and hazards, halting motion on contact."""
        self.should_move_horiz = self.should_move_vert = True
        if self.rect:
            for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only = True, include_hazards = True):
                if ent != self and pygame.sprite.collide_rect(self, ent): # noqa
                    if pygame.sprite.collide_mask(self, ent) and ent.collide(self): # noqa
                        self.collide(ent)
                        overlap = self.rect.clip(ent.rect)
                        if overlap.width < overlap.height:
                            if self.x_vel <= 0 and self.rect.left == overlap.left:
                                self.rect.left = ent.rect.right
                                self.should_move_horiz = False
                            elif self.x_vel >= 0 and self.rect.right == overlap.right:
                                self.rect.right = ent.rect.left
                                self.should_move_horiz = False
                        if overlap.width > overlap.height:
                            if self.y_vel > 0 and self.rect.bottom == overlap.bottom:
                                self.should_move_vert = False
                            elif self.y_vel < 0 and self.rect.top == overlap.top:
                                self.rect.top = ent.rect.bottom
                                self.y_vel *= -0.5
                if not self.should_move_horiz and not self.should_move_vert:
                    break
        return None

    def move(
            self: MovableBlock,
            dx:   float,
            dy:   float,
    ) -> None:
        """Move the block by the given deltas, resetting to its start if it falls off the map."""
        if self.rect:
            if dx != 0:
                if self.rect.left + dx < self.level.level_bounds[0][0]:
                    self.rect.left = self.rect.width
                    self.x_vel     = 0.0
                elif self.rect.right + dx > self.level.level_bounds[1][0]:
                    self.rect.right = self.level.level_bounds[1][0] - self.rect.width
                    self.x_vel      = 0.0
                else:
                    self.rect.x += dx

            if dy != 0:
                if self.rect.top + dy < self.level.level_bounds[0][1]:
                    self.y_vel *= -0.5
                elif self.rect.top + dy > self.level.level_bounds[1][1]:
                    self.rect.x = self.start_x
                    self.rect.y = self.start_y
                    self.x_vel  = 0.0
                else:
                    self.rect.y += dy
        return None

    def loop(
            self:  MovableBlock,
            dtime: float,
    ) -> float:
        """Apply push/gravity, resolve collisions, and run the base entity loop."""
        self.push_x *= max(0.0, 1 - (2 * dtime))
        self.push_y = 0.0
        self.get_collisions()
        if not self.should_move_horiz:
            self.x_vel = 0.0

        if self.should_move_vert:
            self.y_vel += self.gravity
        else:
            self.y_vel = 0.0

        if self.x_vel + self.push_x != 0.0 or self.y_vel + self.push_y != 0.0:
            self.move((self.x_vel + self.push_x) * dtime, (self.y_vel + self.push_y) * dtime)

        return super().loop(dtime)


class Hazard(Block):
    ATTACK_DAMAGE = 99

    def __init__(
            self:          Hazard,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            width:         float,
            height:        float,
            image_master:  dict,
            sprite_master: dict,
            audios:        dict,
            difficulty:    float,
            hit_sides:     str        = "UDLR",
            sprite:        str | None = None,
            coord_x:       int        = 0,
            coord_y:       int        = 0,
            attack_damage: float      = ATTACK_DAMAGE,
            name:          str        = "Hazard",
    ) -> None:
        """Initialize a damaging hazard with animated sprites and active hit sides."""
        super().__init__(
            level,
            controller,
            x,
            (y + width - height),
            width,
            height,
            image_master,
            audios,
            False,
            coord_x = coord_x,
            coord_y = coord_y,
            name    = name,
        )
        self.difficulty    = difficulty
        self.attack_damage = attack_damage * difficulty
        self.is_attacking  = True
        self.hit_sides     = hit_sides.upper()
        if sprite is not None:
            avail_sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction = False, retro = self.level.retro)
            if self.level.retro and avail_sprites.get("ANIMATE_RETRO") is not None:
                self.sprites = avail_sprites["ANIMATE_RETRO"]
            else:
                self.sprites = avail_sprites["ANIMATE"]
        else:
            self.sprites = [self.sprite]
        self.animation_count = 0
        self.sprite          = None
        self.update_sprite()
        self.update_geo()

    def set_difficulty(
            self:  Hazard,
            scale: float,
    ) -> None:
        """Rescale the hazard's attack damage to the new difficulty."""
        self.difficulty     = scale
        self.attack_damage *= scale
        return None

    def update_sprite(
            self: Hazard,
    ) -> int:
        """Advance the hazard's animation and return the active frame index."""
        active_index = math.floor((self.animation_count / Hazard.ANIMATION_DELAY) % len(self.sprites))
        if active_index >= len(self.sprites):
            active_index         = 0
            self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def update_geo(
            self: Hazard,
    ) -> None:
        """Recompute the hazard's rect and collision mask from its current sprite."""
        if self.sprite and self.rect:
            self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
            self.mask = pygame.mask.from_surface(self.sprite) if self.sprite else None
        return None

    def loop(
            self:  Hazard,
            dtime: float,
    ) -> float:
        """Advance the hazard's animation and run the base entity loop."""
        self.animation_count += dtime
        return super().loop(dtime)

    def draw(
            self:          Hazard,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float],
    ) -> None:
        """Update and blit the hazard's animated sprite if it is within view."""
        if self.rect:
            adj_x = self.rect.x - offset_x
            adj_y = self.rect.y - offset_y
            if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
                self.update_sprite()
                self.update_geo()
                if self.sprite:
                    win.blit(self.sprite, (adj_x, adj_y))
        return None


class MovingHazard(MovingBlock, Hazard):
    VELOCITY_TARGET = 500
    ATTACK_DAMAGE   = 99

    def __init__(
            self:          MovingHazard,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            width:         float,
            height:        float,
            image_master:  dict,
            sprite_master: dict,
            audios:        dict,
            difficulty:    float,
            is_stacked:    bool,
            speed:         float                  = VELOCITY_TARGET,
            path:          list[PathPoint] | None = None,
            hit_sides:     str                    = "UDLR",
            sprite:        str | None             = None,
            coord_x:       int                    = 0,
            coord_y:       int                    = 0,
            attack_damage: float                  = ATTACK_DAMAGE,
            name:          str                    = "MovingHazard",
    ) -> None:
        """Initialize a hazard that travels along a path while dealing damage."""
        MovingBlock.__init__(
            self,
            level,
            controller,
            x,
            y,
            width,
            height,
            image_master,
            audios,
            is_stacked,
            hold_for_collision = False,
            speed              = speed,
            path               = path,
            coord_x            = coord_x,
            coord_y            = coord_y,
            name               = name,
        )
        self.attack_damage = attack_damage * difficulty
        self.is_attacking  = True
        self.hit_sides     = hit_sides.upper()
        if sprite is not None:
            avail_sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction = False, retro = self.level.retro)
            if self.level.retro and avail_sprites.get("ANIMATE_RETRO") is not None:
                self.sprites = avail_sprites["ANIMATE_RETRO"]
            else:
                self.sprites = avail_sprites["ANIMATE"]
        else:
            self.sprites = [self.sprite]
        self.animation_count = 0
        self.sprite          = None
        self.update_sprite()

    def loop(
            self:  MovingHazard,
            dtime: float,
    ) -> float:
        """Advance the moving hazard using the MovingBlock loop."""
        return MovingBlock.loop(self, dtime)


class FallingHazard(Hazard):
    ATTACK_DAMAGE  = 99
    RESET_DELAY    = 2.5
    LANDING_EFFECT = 0.05

    def __init__(
            self:          FallingHazard,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            width:         float,
            height:        float,
            image_master:  dict,
            sprite_master: dict,
            audios:        dict,
            difficulty:    float,
            hit_sides:     str        = "D",
            drop_x:        float      = 0,
            drop_y:        float      = 0,
            fire_once:     bool       = True,
            sprite:        str | None = None,
            coord_x:       int        = 0,
            coord_y:       int        = 0,
            attack_damage: float      = ATTACK_DAMAGE,
            name:          str        = "FallingHazard",
    ) -> None:
        """Initialize a hazard that drops when the player passes beneath its trigger zone."""
        super().__init__(
            level,
            controller,
            x,
            y,
            width,
            height,
            image_master,
            sprite_master,
            audios,
            difficulty,
            hit_sides     = hit_sides,
            sprite        = sprite,
            coord_x       = coord_x,
            coord_y       = coord_y,
            attack_damage = attack_damage,
            name          = name,
        )
        self.start_x     = self.rect.x if self.rect else 0
        self.start_y     = self.rect.y if self.rect else 0
        self.drop_x      = drop_x
        self.drop_y      = drop_y
        self.fire_once   = fire_once
        self.has_fired   = False
        self.should_fire = False
        self.y_vel       = 0.0
        self.cooldowns.update({"reset_time": 0.0, "landing_effect": 0.0})

    def update_sprite(
            self: FallingHazard,
    ) -> int:
        """Choose the falling, landed, or animated idle frame and return its index."""
        if hasattr(self, "has_fired") and self.has_fired:
            if self.y_vel != 0:
                active_index = -2
            else:
                active_index = -1
        else:
            active_index = math.floor((self.animation_count / FallingHazard.ANIMATION_DELAY) % (len(self.sprites) - 2))
            if active_index >= len(self.sprites) - 2:
                active_index         = 0
                self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def loop(
            self:  FallingHazard,
            dtime: float,
    ) -> float:
        """Handle triggering, falling, landing on other hazards, and resetting."""
        dtime_offset = 0.0
        if not self.has_fired:
            if self.rect and self.level.player.rect and abs(self.level.player.rect.x - self.rect.x) <= self.drop_x and self.level.player.rect.top >= self.rect.bottom and abs(self.level.player.rect.y - self.rect.y) <= self.drop_y:
                self.should_fire = True

            if self.should_fire:
                self.has_fired = True
                self.play_sound("block_drop")
            else:
                self.animation_count += dtime
                return dtime_offset

        should_reset  = bool(self.cooldowns["reset_time"] > 0)
        dtime_offset += super().loop(dtime)
        should_reset  = should_reset and bool(self.cooldowns["reset_time"] <= 0)

        if should_reset:
            self.should_fire = False
            if self.fire_once:
                self.die()
                return dtime_offset
            else:
                self.rect.x    = self.start_x
                self.rect.y    = self.start_y
                self.has_fired = False
                self.y_vel     = 0

        if self.rect and self.has_fired and self.cooldowns["reset_time"] <= 0:
            self.y_vel += self.gravity * dtime

            ents = self.level.get_entities_in_range((self.rect.x, self.rect.y + self.y_vel), blocks_only=True)
            # this part lets falling hazards hit each other and cause those to fall too
            x = int(self.rect.x / self.level.block_size)
            if self.level.falling_hazards.get(x) is not None:
                ents += self.level.falling_hazards[x]

            for ent in ents:
                if self.rect and ent != self and pygame.sprite.collide_rect(self, ent) and pygame.sprite.collide_mask(self, ent): # noqa
                    self.rect.bottom = ent.rect.top
                    self.y_vel       = 0
                    self.play_sound("block_land")
                    self.level.visual_effects_manager.spawn( # noqa
                        VisualEffect(
                            self,
                            self.level.visual_effects_manager.image_master, # noqa
                            image_name = "LANDBURST",
                            direction  = ImageDirection.BOTTOM,
                            alpha      = 128,
                            scale      = (self.rect.width * 2, self.rect.height / 2),
                        ),
                        time = FallingHazard.LANDING_EFFECT,
                    )
                    if isinstance(ent, FallingHazard):
                        ent.should_fire = True
                    else:
                        self.cooldowns["reset_time"] += FallingHazard.RESET_DELAY
                    break

            self.rect.y += self.y_vel
            if self.rect.y > self.level.level_bounds[1][1]:
                self.cooldowns["reset_time"] += FallingHazard.RESET_DELAY

        return dtime_offset
