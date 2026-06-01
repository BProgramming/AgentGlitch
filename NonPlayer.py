from __future__ import annotations
from typing import Any, TYPE_CHECKING
import math
import time
import pygame
from enum import Enum
from Actor import Actor, MovementState
from Block import Door
from Entity import Entity
from Helpers import (
    DifficultyScale,
    MovementDirection,
    load_text_from_file,
    display_text,
    image_to_retro,
    RETRO_BLACK,
    RETRO_WHITE,
    NORMAL_WHITE,
    NORMAL_BLACK,
    TEXT_BOX_BORDER_RADIUS,
    process_text, PathPoint,
)
from SimpleVFX.SimpleVFX import VisualEffect

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class NPCAlertState(Enum):
    PATROL = 0
    WAIT   = 1
    SEARCH = 2
    PURSUE = 3

    def __str__(
            self: NPCAlertState,
    ) -> str:
        """Return the alert state's name."""
        return self.name


class NonPlayer(Actor):
    VELOCITY_TARGET:      float = 250.0
    PLAYER_SPOT_COOLDOWN: float =   2.0
    ALERT_COOLDOWN:       float =   1.5
    SEARCH_LOOK_TIME:     float =   0.9
    PATH_WAIT_TIME:       float =   2.0

    PLAYER_SPOT_RANGE: int =  3
    GAP_LOOKAHEAD:     int = 10

    def __init__(
            self:              NonPlayer,
            level:             Level,
            controller:        Controller,
            x:                 float,
            y:                 float,
            sprite_master:     dict[str, dict[str, list[pygame.Surface]]],
            audios:            dict[str, list[pygame.mixer.Sound]],
            difficulty:        float,
            block_size:        float,
            path:              list[PathPoint] | None             = None,
            kill_at_end:       bool                               = False,
            is_hostile:        bool                               = True,
            collision_message: str | dict[str, str | None] | None = None,
            bark:              str | None                         = None,
            hp:                float                              = 100,
            can_shoot:         bool                               = False,
            spot_range:        float                              = PLAYER_SPOT_RANGE,
            sprite:            str | None                         = None,
            proj_sprite:       str | None                         = None,
            name:              str                                = "Enemy",
    ) -> None:
        """Initialize a non-player actor's patrol path, alert state, vision cones, and bark."""
        super().__init__(
            level,
            controller,
            x,
            y,
            sprite_master,
            audios,
            difficulty,
            block_size,
            can_shoot   = can_shoot,
            sprite      = sprite,
            proj_sprite = proj_sprite,
            name        = name,
        )
        self.target_vel = NonPlayer.VELOCITY_TARGET
        self.is_hostile = is_hostile

        self.collision_message: list[str] | dict[str, Any] | None = None
        if collision_message:
            if isinstance(collision_message, str):
                self.collision_message = load_text_from_file(collision_message)
            elif isinstance(collision_message, dict):
                f = collision_message.get("text")
                if f:
                    self.collision_message = load_text_from_file(f)
                f = collision_message.get("audio")
                if f:
                    self.collision_message = {
                        "text":  self.collision_message,
                        "audio": pygame.mixer.Sound(f),
                    }
        self.queued_message: str | list[str] | dict[str, Any] | None = None

        self.patrol_path = path
        self.kill_at_end = kill_at_end
        self.spot_range  = spot_range * block_size
        if path is None:
            self.spot_range *= 2
        self.patrol_path_index = 0
        if self.patrol_path and self.rect:
            for point in self.patrol_path:
                point.x += (block_size - self.rect.width) // 2
                point.y += (block_size - self.rect.height)
            min_dist = math.dist((self.rect.x, self.rect.y), (self.patrol_path[0].x, self.patrol_path[0].y))
            for i in range(len(self.patrol_path)):
                d = math.dist((self.rect.x, self.rect.y), (self.patrol_path[i].x, self.patrol_path[i].y))
                if d < min_dist:
                    min_dist               = d
                    self.patrol_path_index = i
            self.direction = self.facing = (
                MovementDirection.RIGHT
                if self.patrol_path[self.patrol_path_index].x - self.rect.x >= 0
                else MovementDirection.LEFT
            )

        self.max_hp = self.hp = hp * self.difficulty

        self.cooldowns.update({
            "spot_player":    0.0,
            "alert_cooldown": 0.0,
            "search_turn":    0.0,
            "wait":           0.0,
        })
        self.cached_cooldowns = self.cooldowns.copy()

        self.alert_state: NPCAlertState = NPCAlertState.PATROL

        self._waiting_for_door: bool = False

        vision_hidden  = pygame.Surface((256, 10), pygame.SRCALPHA)
        vision_spotted = vision_hidden.copy()
        chunk = pygame.Surface((1, 10), pygame.SRCALPHA)
        chunk.fill((0, 255, 0))
        for i in range(256):
            chunk.set_alpha(i)
            vision_hidden.blit(chunk, (i, 0))
        chunk.fill((255, 0, 0))
        for i in range(256):
            chunk.set_alpha(i)
            vision_spotted.blit(chunk, (i, 0))
        if self.level.retro:
            vision_hidden  = image_to_retro(vision_hidden)
            vision_spotted = image_to_retro(vision_spotted)
        self.vision = {
            "hidden": {
                MovementDirection.LEFT:  vision_hidden,
                MovementDirection.RIGHT: pygame.transform.flip(vision_hidden, True, False),
            },
            "spotted": {
                MovementDirection.LEFT:  vision_spotted,
                MovementDirection.RIGHT: pygame.transform.flip(vision_spotted, True, False),
            },
        }

        self.bark:       pygame.Surface | None = self.set_bark(load_text_from_file(bark)) if bark else None
        self.has_barked: bool                  = False

    def _enter_search(
            self:        NonPlayer,
            *,
            from_pursue: bool,
    ) -> None:
        """Enter the SEARCH state, reset its cooldowns, and spawn the spot/lose-player VFX."""
        if self.rect:
            self.alert_state                 = NPCAlertState.SEARCH
            self.cooldowns["alert_cooldown"] = NonPlayer.ALERT_COOLDOWN
            self.cooldowns["search_turn"]    = NonPlayer.SEARCH_LOOK_TIME
            vfx_name = "LOSE_PLAYER" if from_pursue else "SPOT_PLAYER"
            # TODO: create SPOT_PLAYER and LOSE_PLAYER images in Assets/VisualEffects/
            self.level.visual_effects_manager.spawn(
                VisualEffect(
                    self,
                    self.level.visual_effects_manager.image_master, # noqa
                    image_name = vfx_name,
                    alpha      = 255,
                    offset     = (0, -self.rect.height),
                    scale      = (self.rect.height, self.rect.height),
                ),
                time = NonPlayer.ALERT_COOLDOWN,
            )
        return None

    def __adj_spot_range__(
            self: NonPlayer,
    ) -> float:
        """Return the spot range adjusted for the player's size and crouch state."""
        return self.spot_range * self.level.player.size / (1.5 if self.level.player.is_crouching else 1)

    def __spot_player__(
            self: NonPlayer,
    ) -> bool:
        """Return whether the player is visible: in range, faced, and unobstructed by blocks."""
        if self.rect and self.level.player.rect:
            dist = math.dist(self.level.player.rect.center, self.rect.center)
            facing_toward = (
                self.facing == (
                    MovementDirection.RIGHT
                    if self.level.player.rect.centerx - self.rect.centerx >= 0
                    else MovementDirection.LEFT
                )
            )
            if dist <= self.__adj_spot_range__() and (facing_toward or self.cooldowns["get_hit"] > 0):
                half_w = self.rect.width // 2
                cx, cy = self.rect.centerx, self.rect.centery
                step   = max(1, self.level.block_size // 2)
                for i in range(0, round(dist), step):
                    probe_x = cx + (self.facing * (half_w + i))
                    for ent in self.level.get_entities_in_range((probe_x, cy), blocks_only=True):
                        if ent.rect.collidepoint(probe_x, cy):
                            return False
                self.cooldowns["spot_player"] = NonPlayer.PLAYER_SPOT_COOLDOWN
                if (self.state in (
                        MovementState.IDLE, MovementState.CROUCH, MovementState.RUN,
                        MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK)
                        and self.abilities["can_shoot"]
                        and dist > self.spot_range // 3):
                    self.shoot_at_target(self.level.player.rect.center)
                self.level.player.been_seen_this_level = True
                return True
        return False

    def __find_floor__(
            self: NonPlayer,
            dist: float,
    ) -> bool:
        """Return whether there is solid floor a given horizontal distance ahead."""
        if self.rect:
            check_x = int(self.rect.x + dist)
            check_y = self.rect.bottom
            for block in self.level.get_entities_in_range((check_x, check_y), blocks_only=True):
                if block.rect.collidepoint(check_x, check_y):
                    return True
        return False

    def __increment_patrol_index__(
            self: NonPlayer,
    ) -> None:
        """Advance the patrol index, reversing at path ends or purging if kill_at_end is set."""
        if self.patrol_path:
            if self.patrol_path_index < 0:
                self.patrol_path_index -= 1
            elif self.patrol_path_index >= 0:
                self.patrol_path_index += 1
            if self.patrol_path_index >= len(self.patrol_path) - 1:
                if self.kill_at_end:
                    self.level.queue_purge(self)
                    return None
                self.patrol_path_index = -1
            elif self.patrol_path_index <= -len(self.patrol_path):
                self.patrol_path_index = 0
        return None

    def patrol(
            self:  NonPlayer,
            dtime: float,
    ) -> None:   # noqa: C901 (intentionally complex)
        """Run one tick of the patrol/search/pursue AI, driving movement and attacks."""
        self.should_move_horiz = False

        if (self.cooldowns["get_hit"] > 0
                or self.state in (MovementState.WIND_UP, MovementState.WIND_DOWN)):
            return None

        if self.rect and self._waiting_for_door:
            still_blocked = any(
                isinstance(ent, Door) and pygame.sprite.collide_rect(self, ent) # noqa
                for ent in self.level.get_entities_in_range(self.rect.center, blocks_only=True)
            )
            if still_blocked:
                return None
            self._waiting_for_door = False

        if self.alert_state == NPCAlertState.SEARCH:
            if self.cooldowns["search_turn"] <= 0:
                self.direction = self.facing = self.direction.swap()
                self.cooldowns["search_turn"] = NonPlayer.SEARCH_LOOK_TIME

            if self.cooldowns["alert_cooldown"] <= 0:
                self.cooldowns["spot_player"] = 0
                if self.is_hostile and self.__spot_player__():
                    self.alert_state = NPCAlertState.PURSUE
                else:
                    self.alert_state = NPCAlertState.PATROL
            return None

        if self.alert_state == NPCAlertState.WAIT:
            if self.cooldowns["wait"] <= 0:
                self.alert_state = NPCAlertState.PATROL
            else:
                if self.is_hostile and self.cooldowns["spot_player"] <= 0:
                    if self.__spot_player__():
                        self._enter_search(from_pursue=False)
                return None

        can_see_player: bool
        if self.is_hostile:
            if self.cooldowns["spot_player"] <= 0:
                can_see_player = self.__spot_player__()
            else:
                can_see_player = True
        else:
            can_see_player = False

        if self.rect and self.level.player.rect and not self.patrol_path:
            self.should_move_vert = False
            self.direction = self.facing = (
                MovementDirection.RIGHT
                if self.level.player.rect.centerx - self.rect.centerx >= 0
                else MovementDirection.LEFT
            )
            if can_see_player:
                dist = math.dist(self.level.player.rect.center, self.rect.center)
                if self.alert_state == NPCAlertState.PATROL:
                    self._enter_search(from_pursue=False)
                elif self.alert_state == NPCAlertState.PURSUE:
                    if dist >= self.spot_range // 3:
                        self.is_attacking = True
                    elif not self.is_animated_attack:
                        self.is_attacking = False
            else:
                if self.alert_state == NPCAlertState.PURSUE:
                    self.alert_state = NPCAlertState.PATROL
            return None

        if self.alert_state == NPCAlertState.PATROL and can_see_player:
            self._enter_search(from_pursue = False)
            return None
        elif self.alert_state == NPCAlertState.PURSUE and self.rect and self.level.player.rect:
            if not can_see_player:
                self._enter_search(from_pursue = True)
                return None
            # Chase / shoot
            dist = math.dist(self.level.player.rect.center, self.rect.center)
            if self.abilities["can_shoot"]:
                if dist < self.spot_range // 3:
                    # Back away to preferred shooting distance
                    if abs(self.rect.x - self.level.player.rect.x) > 5:
                        self.direction = (
                            MovementDirection.RIGHT
                            if self.rect.centerx - self.level.player.rect.centerx >= 0
                            else MovementDirection.LEFT
                        )
                        self.facing            = self.direction.swap()
                        self.x_vel             = float(self.direction) * self.target_vel
                        self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)
                    if not self.is_animated_attack:
                        self.is_attacking = False
                else:
                    self.is_attacking = True
                    self.x_vel        = 0.0
            else:
                if pygame.sprite.collide_rect(self, self.level.player): # noqa
                    self.is_attacking = True
                    if (abs(self.rect.x - self.level.player.rect.x) <= 5
                            or pygame.sprite.collide_mask(self, self.level.player)): # noqa
                        self.x_vel = 0.0
                    else:
                        self.direction = self.facing = (
                            MovementDirection.RIGHT
                            if self.level.player.rect.centerx - self.rect.centerx >= 0
                            else MovementDirection.LEFT
                        )
                        self.x_vel             = float(self.direction) * self.target_vel
                        self.should_move_horiz = True
                else:
                    self.direction = self.facing = (
                        MovementDirection.RIGHT
                        if self.level.player.rect.centerx - self.rect.centerx >= 0
                        else MovementDirection.LEFT
                    )
                    self.x_vel             = float(self.direction) * self.target_vel
                    self.should_move_horiz = True
            return None

        if self.rect and self.patrol_path:
            target_x = self.patrol_path[self.patrol_path_index].x - self.rect.x

            if abs(target_x) > 1:
                self.direction = self.facing = (
                    MovementDirection.RIGHT if target_x >= 0 else MovementDirection.LEFT
                )
                self.x_vel = (
                    min(abs(target_x) / dtime, self.target_vel) * float(self.direction)
                )
                self.should_move_horiz = True

                # Check floor one step ahead of the NPC's leading edge.
                if self.rect and self.jump_count == 0 and not self.should_move_vert:
                    leading_edge_offset = (
                        self.rect.width + NonPlayer.GAP_LOOKAHEAD
                        if self.direction == MovementDirection.RIGHT
                        else -NonPlayer.GAP_LOOKAHEAD
                    )
                    if not self.__find_floor__(leading_edge_offset):
                        self.jump()
            else:
                # Reached waypoint.
                # A third element of True in the path point means "wait here".
                if self.patrol_path and self.patrol_path[self.patrol_path_index].wait:
                    self.alert_state       = NPCAlertState.WAIT
                    self.cooldowns["wait"] = NonPlayer.PATH_WAIT_TIME
                self.__increment_patrol_index__()
        return None

    def collide(
            self: NonPlayer,
            ent:  Entity,
    ) -> bool:
        """Resolve a collision: navigate doors/obstacles, or queue a message/bark on player contact."""
        if ent != self.level.player:
            if self.rect and ent.rect and self.direction == (
                MovementDirection.RIGHT
                if ent.rect.centerx - self.rect.centerx > 0
                else MovementDirection.LEFT
            ):
                if ent.is_stacked or isinstance(ent, Door):
                    if isinstance(ent, Door) and not ent.is_locked:
                        # Unlocked door: open it and wait for it to clear.
                        if not ent.is_open:
                            ent.open()
                        self._waiting_for_door = True
                    elif self.patrol_path and self.alert_state in (NPCAlertState.PATROL, NPCAlertState.WAIT):
                        # Locked door or solid stacked block: skip to next waypoint.
                        for _ in range(len(self.patrol_path)):
                            self.__increment_patrol_index__()
                            if (self.direction == MovementDirection.RIGHT
                                    and self.rect.centerx
                                    > self.patrol_path[self.patrol_path_index].x):
                                self.direction = self.facing = self.direction.swap()
                                break
                            elif (self.direction == MovementDirection.LEFT
                                    and self.rect.centerx
                                    < self.patrol_path[self.patrol_path_index].x):
                                self.direction = self.facing = self.direction.swap()
                                break
                else:
                    # Non-wall obstacle: try jumping over it.
                    self.jump()
        elif self.collision_message is not None:
            self.queued_message    = self.collision_message
            self.collision_message = None
        elif self.bark is not None:
            self.cooldowns["bark"] = NonPlayer.BARK_TIME
            self.has_barked        = True
        return True

    def draw(
            self:          NonPlayer,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict[str, float],
    ) -> None:
        """Draw the vision cone (on easy difficulty), the actor sprite, and any active bark."""
        if self.rect and self.difficulty <= DifficultyScale.EASY and self.is_hostile:
            adj_x = self.rect.centerx - offset_x - (
                self.__adj_spot_range__() if self.facing == MovementDirection.LEFT else 0
            )
            adj_y = self.rect.y - offset_y + (7 * self.rect.height // 24)
            win_w = win.get_width()
            win_h = win.get_height()
            if (-self.__adj_spot_range__() < adj_x <= win_w
                    and -self.rect.height < adj_y <= win_h):
                # Red cone when alert; green cone when calm.
                if self.alert_state in (NPCAlertState.SEARCH, NPCAlertState.PURSUE):
                    cone = self.vision["spotted"][self.facing]
                else:
                    cone = self.vision["hidden"][self.facing]
                win.blit(
                    pygame.transform.scale(cone, (self.__adj_spot_range__(), self.rect.height // 4)),
                    (adj_x, adj_y),
                )
        super().draw(win, offset_x, offset_y, master_volume)
        if self.rect and self.cooldowns["bark"] > 0 and self.bark is not None:
            adj_x = self.rect.x - offset_x
            if adj_x > win.get_width() // 2:
                adj_x -= self.bark.get_width() - self.rect.width
            adj_y = self.rect.y - (offset_y + self.bark.get_height())
            win.blit(self.bark, (adj_x, adj_y))
        return None

    def loop(
            self:  NonPlayer,
            dtime: float,
    ) -> float:
        """Expire the bark once its cooldown ends, then run the base actor loop."""
        if self.has_barked and self.cooldowns["bark"] <= 0:
            self.bark              = None
            self.cooldowns["bark"] = 0.0
            self.has_barked        = False
        return super().loop(dtime)

    def die(
            self: NonPlayer,
    ) -> float:
        """Credit the player with a kill and run the base actor death handling."""
        self.level.player.kills_this_level += 1
        return super().die()

    def play_queued_message(
            self: NonPlayer,
    ) -> float:
        """Display any queued collision message (with optional audio) and return the frame-time offset."""
        start = time.perf_counter()
        if (isinstance(self.queued_message, dict)
                and self.queued_message.get("text") is not None
                and self.queued_message.get("audio") is not None):
            display_text(
                self.queued_message["text"],
                self.controller,
                audio            = self.queued_message["audio"],
                should_type_text = False,
                retro            = self.level.retro,
            )
        elif isinstance(self.queued_message, str) or isinstance(self.queued_message, list):
            display_text(
                self.queued_message,
                self.controller,
                should_type_text = False,
                retro            = self.level.retro,
            )
        self.queued_message = None
        return time.perf_counter() - start

    def set_bark(
            self:   NonPlayer,
            output: list[str] | str | None,
    ) -> pygame.Surface | None:
        """Render bark text into a translucent speech-box surface, or None if there is no text."""
        if output is None or output == "":
            return None
        line = "\n".join(output) if isinstance(output, list) else output
        line, is_bold, is_italics = process_text(line, self.controller)

        text_colour = RETRO_WHITE if self.controller.retro else NORMAL_WHITE
        box_colour  = RETRO_BLACK if self.controller.retro else NORMAL_BLACK
        box_colour  = (box_colour[0], box_colour[1], box_colour[2], 128)

        text_line = pygame.font.SysFont(
            "courier", 32, bold=is_bold, italic=is_italics
        ).render(line, True, text_colour)
        text_box = pygame.Surface(
            (text_line.get_width() + 10, text_line.get_height() + 10), pygame.SRCALPHA
        )
        pygame.draw.rect(
            text_box, box_colour,
            pygame.Rect(0, 0, text_box.get_width(), text_box.get_height()),
            border_radius=TEXT_BOX_BORDER_RADIUS,
        )
        text_box.blit(text_line, (5, 5))
        return text_box
