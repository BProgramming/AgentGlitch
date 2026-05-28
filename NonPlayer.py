import math
import pygame
import time
import re
from enum import Enum
from pathlib import Path
from Actor import Actor, MovementState
from Block import Door
from Helpers import DifficultyScale, MovementDirection, load_text_from_file, display_text, ASSETS_FOLDER, \
    retroify_image, RETRO_BLACK, RETRO_WHITE, NORMAL_WHITE, NORMAL_BLACK, TEXT_BOX_BORDER_RADIUS, process_text
from SimpleVFX.SimpleVFX import VisualEffect, ImageDirection


class NPCAlertState(Enum):
    """Behaviour state for hostile NPC awareness of the player.

    PATROL  – following the assigned patrol path (or standing idle if no path).
    WAIT    – paused at a waypoint (duplicate-coordinate stop on the patrol path).
    SEARCH  – player was recently spotted or just lost; NPC looks back and forth.
    PURSUE  – actively chasing / engaging the player.
    """
    PATROL = 0
    WAIT   = 1
    SEARCH = 2
    PURSUE = 3

    def __str__(self) -> str:
        return self.name


class NonPlayer(Actor):
    VELOCITY_TARGET      = 250
    PLAYER_SPOT_RANGE    = 3
    # Rate-limiter: minimum seconds between full raycasting spot-checks.
    PLAYER_SPOT_COOLDOWN = 2
    # How long the NPC lingers in SEARCH before committing to PURSUE or PATROL.
    ALERT_COOLDOWN       = 1.5
    # How long the NPC faces each direction while searching.
    SEARCH_LOOK_TIME     = 0.9
    # How long the NPC waits at a marked waypoint.
    PATH_WAIT_TIME       = 2.0
    # Pixels beyond the NPC's leading edge used when checking for a gap ahead.
    GAP_LOOKAHEAD        = 10

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size,
                 path=None, kill_at_end=False, is_hostile=True, collision_message=None,
                 bark=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE,
                 sprite=None, proj_sprite=None, name="Enemy"):
        super().__init__(level, controller, x, y, sprite_master, audios, difficulty, block_size,
                         can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name=name)
        self.target_vel  = NonPlayer.VELOCITY_TARGET
        self.is_hostile  = is_hostile

        # ── collision / bark message setup ─────────────────────────────────
        if collision_message is not None:
            if isinstance(collision_message, dict) \
                    and collision_message.get("text") is not None \
                    and collision_message.get("audio") is not None:
                audio_file = Path(ASSETS_FOLDER) / "SoundEffects" / "Text" / collision_message["audio"]
                if audio_file.is_file():
                    self.collision_message = {
                        "text":  load_text_from_file(collision_message["text"]),
                        "audio": pygame.mixer.Sound(str(audio_file)),
                    }
                else:
                    self.collision_message = load_text_from_file(collision_message["text"])
            else:
                self.collision_message = load_text_from_file(collision_message)
        else:
            self.collision_message = None
        self.queued_message = None

        # ── patrol path ────────────────────────────────────────────────────
        self.patrol_path       = path
        self.kill_at_end       = kill_at_end
        self.spot_range        = spot_range * block_size
        if path is None:
            self.spot_range *= 2
        self.patrol_path_index = 0
        if self.patrol_path is not None:
            for point in self.patrol_path:
                point[0] += (block_size - self.rect.width) // 2
                point[1] += (block_size - self.rect.height)
            min_dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[0])
            for i in range(len(self.patrol_path)):
                d = math.dist((self.rect.x, self.rect.y), self.patrol_path[i])
                if d < min_dist:
                    min_dist = d
                    self.patrol_path_index = i
            self.direction = self.facing = (
                MovementDirection.RIGHT
                if self.patrol_path[self.patrol_path_index][0] - self.rect.x >= 0
                else MovementDirection.LEFT
            )

        # ── HP ─────────────────────────────────────────────────────────────
        self.max_hp = self.hp = hp * self.difficulty

        # ── cooldowns (all decremented each frame by update_cooldowns) ──────
        self.cooldowns.update({
            "spot_player":    0.0,  # rate-limiter for raycasting
            "alert_cooldown": 0.0,  # SEARCH decision window
            "search_turn":    0.0,  # look-direction flip timer in SEARCH
            "wait":           0.0,  # waypoint pause timer
        })
        self.cached_cooldowns = self.cooldowns.copy()

        # ── alert state machine ─────────────────────────────────────────────
        self.alert_state: NPCAlertState = NPCAlertState.PATROL

        # ── door interaction ────────────────────────────────────────────────
        # True while the NPC has triggered a door open and is waiting for it
        # to slide clear before resuming movement.
        self._waiting_for_door: bool = False

        # ── vision cone surfaces ────────────────────────────────────────────
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
            vision_hidden  = retroify_image(vision_hidden)
            vision_spotted = retroify_image(vision_spotted)
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

        # ── bark ────────────────────────────────────────────────────────────
        self.bark: pygame.Surface | None = (
            None if bark is None else self.set_bark(load_text_from_file(bark))
        )
        self.has_barked = False

    # ──────────────────────────────────────────────────────────────────────
    # Alert-state helpers
    # ──────────────────────────────────────────────────────────────────────

    def _enter_search(self, *, from_pursue: bool) -> None:
        """Transition into SEARCH state and spawn the appropriate VFX above the NPC."""
        self.alert_state = NPCAlertState.SEARCH
        self.cooldowns["alert_cooldown"] = NonPlayer.ALERT_COOLDOWN
        self.cooldowns["search_turn"]    = NonPlayer.SEARCH_LOOK_TIME
        vfx_name = "LOSE_PLAYER" if from_pursue else "SPOT_PLAYER"
        # TODO: create SPOT_PLAYER and LOSE_PLAYER images in Assets/VisualEffects/
        self.level.visual_effects_manager.spawn(
            VisualEffect(
                self,
                self.level.visual_effects_manager.image_master,
                image_name=vfx_name,
                alpha=255,
                offset=(0, -self.rect.height),
                scale=(self.rect.height, self.rect.height),
            ),
            time=NonPlayer.ALERT_COOLDOWN,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def __adj_spot_range__(self) -> float:
        return self.spot_range * self.level.player.size / (
            1.5 if self.level.player.is_crouching else 1
        )

    def __spot_player__(self) -> bool:
        """Raycast visibility check.  Sets spot_player cooldown as a rate-limiter.
        Returns True if the player is currently visible."""
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
            step = max(1, self.level.block_size // 2)
            for i in range(0, round(dist), step):
                probe_x = cx + (self.facing * (half_w + i))
                for ent in self.level.get_entities_in_range((probe_x, cy), blocks_only=True):
                    if ent.rect.collidepoint(probe_x, cy):
                        return False
            # Visible – refresh rate-limiter and optionally shoot
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

    def __find_floor__(self, dist: float) -> bool:
        """Check whether there is a floor tile at horizontal offset *dist* from
        the NPC's left edge (negative = left, positive = right).

        Bug-fix: both the range query and the exact collidepoint test now use
        the same reference x so results are consistent.
        """
        check_x = int(self.rect.x + dist)
        check_y = self.rect.bottom
        for block in self.level.get_entities_in_range((check_x, check_y), blocks_only=True):
            if block.rect.collidepoint(check_x, check_y):
                return True
        return False

    def __increment_patrol_index__(self) -> None:
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index >= len(self.patrol_path) - 1:
            if self.kill_at_end:
                self.level.queue_purge(self)
                return
            self.patrol_path_index = -1
        elif self.patrol_path_index <= -len(self.patrol_path):
            self.patrol_path_index = 0

    # ──────────────────────────────────────────────────────────────────────
    # Core per-frame logic
    # ──────────────────────────────────────────────────────────────────────

    def patrol(self, dtime: float) -> None:   # noqa: C901 (intentionally complex)
        """Called once per frame by the engine before loop().
        Drives both patrol-path following and the alert-state machine.
        """
        self.should_move_horiz = False

        # Don't override wind-up / wind-down animations or the hit stagger.
        if (self.cooldowns["get_hit"] > 0
                or self.state in (MovementState.WIND_UP, MovementState.WIND_DOWN)):
            return

        # ── Door wait: stand still until the door slides out of the way ───
        if self._waiting_for_door:
            still_blocked = any(
                isinstance(ent, Door) and pygame.sprite.collide_rect(self, ent)
                for ent in self.level.get_entities_in_range(self.rect.center, blocks_only=True)
            )
            if still_blocked:
                return
            self._waiting_for_door = False

        # ── SEARCH state: look back and forth while deciding ───────────────
        if self.alert_state == NPCAlertState.SEARCH:
            if self.cooldowns["search_turn"] <= 0:
                self.direction = self.facing = self.direction.swap()
                self.cooldowns["search_turn"] = NonPlayer.SEARCH_LOOK_TIME

            if self.cooldowns["alert_cooldown"] <= 0:
                # Decision moment: force a fresh raycasting check.
                self.cooldowns["spot_player"] = 0
                if self.is_hostile and self.__spot_player__():
                    self.alert_state = NPCAlertState.PURSUE
                else:
                    self.alert_state = NPCAlertState.PATROL
            return  # NPC stands still while searching

        # ── WAIT state: paused at waypoint ────────────────────────────────
        if self.alert_state == NPCAlertState.WAIT:
            if self.cooldowns["wait"] <= 0:
                self.alert_state = NPCAlertState.PATROL
            else:
                # Can still spot the player while waiting
                if self.is_hostile and self.cooldowns["spot_player"] <= 0:
                    if self.__spot_player__():
                        self._enter_search(from_pursue=False)
                return

        # ─────────────────────────────────────────────────────────────────
        # Determine current player visibility (rate-limited)
        # ─────────────────────────────────────────────────────────────────
        can_see_player: bool
        if self.is_hostile:
            if self.cooldowns["spot_player"] <= 0:
                can_see_player = self.__spot_player__()
            else:
                # Within the rate-limiter window: we saw them recently.
                can_see_player = True
        else:
            can_see_player = False

        # ── Stationary NPC (no patrol path) ──────────────────────────────
        if self.patrol_path is None:
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
            return

        # ── Has a patrol path ─────────────────────────────────────────────

        # PATROL → SEARCH transition
        if self.alert_state == NPCAlertState.PATROL and can_see_player:
            self._enter_search(from_pursue=False)
            return

        # PURSUE state
        if self.alert_state == NPCAlertState.PURSUE:
            if not can_see_player:
                self._enter_search(from_pursue=True)
                return
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
                        self.facing = self.direction.swap()
                        self.x_vel = float(self.direction) * self.target_vel
                        self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)
                    if not self.is_animated_attack:
                        self.is_attacking = False
                else:
                    self.is_attacking = True
                    self.x_vel = 0.0
            else:
                if pygame.sprite.collide_rect(self, self.level.player):
                    self.is_attacking = True
                    if (abs(self.rect.x - self.level.player.rect.x) <= 5
                            or pygame.sprite.collide_mask(self, self.level.player)):
                        self.x_vel = 0.0
                    else:
                        self.direction = self.facing = (
                            MovementDirection.RIGHT
                            if self.level.player.rect.centerx - self.rect.centerx >= 0
                            else MovementDirection.LEFT
                        )
                        self.x_vel = float(self.direction) * self.target_vel
                        self.should_move_horiz = True
                else:
                    self.direction = self.facing = (
                        MovementDirection.RIGHT
                        if self.level.player.rect.centerx - self.rect.centerx >= 0
                        else MovementDirection.LEFT
                    )
                    self.x_vel = float(self.direction) * self.target_vel
                    self.should_move_horiz = True
            return

        # ── PATROL state: follow path ─────────────────────────────────────
        # (WAIT is handled above; we only reach here in PATROL)
        target_x = self.patrol_path[self.patrol_path_index][0] - self.rect.x

        if abs(target_x) > 1:
            self.direction = self.facing = (
                MovementDirection.RIGHT if target_x >= 0 else MovementDirection.LEFT
            )
            self.x_vel = (
                min(abs(target_x) / dtime, self.target_vel) * float(self.direction)
            )
            self.should_move_horiz = True

            # ── Gap detection: jump before walking off an edge ─────────────
            # Check floor one step ahead of the NPC's leading edge.
            if self.jump_count == 0 and not self.should_move_vert:
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
            is_wait_point = (
                len(self.patrol_path[self.patrol_path_index]) > 2
                and self.patrol_path[self.patrol_path_index][2]
            )
            if is_wait_point:
                self.alert_state = NPCAlertState.WAIT
                self.cooldowns["wait"] = NonPlayer.PATH_WAIT_TIME
            self.__increment_patrol_index__()

    def collide(self, ent) -> bool:
        if ent != self.level.player:
            if self.direction == (
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
                    elif (self.patrol_path is not None
                            and self.alert_state in (NPCAlertState.PATROL, NPCAlertState.WAIT)):
                        # Locked door or solid stacked block: skip to next waypoint.
                        for _ in range(len(self.patrol_path)):
                            self.__increment_patrol_index__()
                            if (self.direction == MovementDirection.RIGHT
                                    and self.rect.centerx
                                    > self.patrol_path[self.patrol_path_index][0]):
                                self.direction = self.facing = self.direction.swap()
                                break
                            elif (self.direction == MovementDirection.LEFT
                                    and self.rect.centerx
                                    < self.patrol_path[self.patrol_path_index][0]):
                                self.direction = self.facing = self.direction.swap()
                                break
                else:
                    # Non-wall obstacle: try jumping over it.
                    self.jump()
        elif self.collision_message is not None:
            self.queued_message = self.collision_message
            self.collision_message = None
        elif self.bark is not None:
            self.cooldowns["bark"] = NonPlayer.BARK_TIME
            self.has_barked = True
        return True

    def draw(self, win, offset_x, offset_y, master_volume) -> None:
        # Vision cone (only shown on easier difficulties).
        if self.difficulty <= DifficultyScale.EASY and self.is_hostile:
            adj_x = self.rect.centerx - offset_x - (
                self.__adj_spot_range__() if self.facing == MovementDirection.LEFT else 0
            )
            adj_y  = self.rect.y - offset_y + (7 * self.rect.height // 24)
            win_w  = win.get_width()
            win_h  = win.get_height()
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
        if self.cooldowns["bark"] > 0 and self.bark is not None:
            adj_x = self.rect.x - offset_x
            if adj_x > win.get_width() // 2:
                adj_x -= self.bark.get_width() - self.rect.width
            adj_y = self.rect.y - (offset_y + self.bark.get_height())
            win.blit(self.bark, (adj_x, adj_y))

    def loop(self, dtime: float) -> float:
        if self.has_barked and self.cooldowns["bark"] <= 0:
            self.bark = None
            self.cooldowns["bark"] = 0
            self.has_barked = False
        return super().loop(dtime)

    def die(self) -> None:
        self.level.player.kills_this_level += 1
        super().die()

    def play_queued_message(self) -> float:
        start = time.perf_counter()
        if (isinstance(self.queued_message, dict)
                and self.queued_message.get("text") is not None
                and self.queued_message.get("audio") is not None):
            display_text(
                self.queued_message["text"], self.controller,
                audio=self.queued_message["audio"], should_type_text=False, retro=self.level.retro,
            )
        else:
            display_text(self.queued_message, self.controller,
                         should_type_text=False, retro=self.level.retro)
        self.queued_message = None
        return time.perf_counter() - start

    # ──────────────────────────────────────────────────────────────────────
    # Bark / text rendering
    # ──────────────────────────────────────────────────────────────────────

    def set_bark(self, output: list[str] | str | None) -> pygame.Surface | None:
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
