import math
import pygame
from Actor import Actor, MovementState
from Helpers import DifficultyScale, MovementDirection


class Enemy(Actor):
    VELOCITY_TARGET = 0.25
    PLAYER_SPOT_RANGE = 288
    PLAYER_SPOT_COOLDOWN = 2

    def __init__(self, x, y, level_bounds, sprite_master, audios, difficulty, path=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE, sprite=None, proj_sprite=None, name="Enemy"):
        super().__init__(x, y, level_bounds, sprite_master, audios, difficulty, can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name=name)
        self.patrol_path = path
        self.spot_range = spot_range
        if path is None:
            self.max_jumps = 0
            self.spot_range *= 2
        self.patrol_path_index = 0
        if self.patrol_path is not None:
            min_dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[0])
            for i in range(len(self.patrol_path)):
                dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[i])
                if dist < min_dist:
                    self.patrol_path_index = i
            self.direction = self.facing = MovementDirection(math.copysign(1, self.patrol_path[self.patrol_path_index][0] - self.rect.x))
        self.max_hp = self.hp = self.cached_hp = hp * self.difficulty
        self.cooldowns.update({"spot_player": 0})
        self.cached_cooldowns = self.cooldowns.copy()

    def increment_patrol_index(self):
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index == len(self.patrol_path):
            self.patrol_path_index = -1
        elif self.patrol_path_index == -(len(self.patrol_path) + 1):
            self.patrol_path_index = 0

    def patrol(self, vel=VELOCITY_TARGET):
        self.should_move_horiz = False
        if self.patrol_path is None:
            self.direction = self.facing = MovementDirection(math.copysign(1, self.player.rect.centerx - self.rect.centerx))
            if self.cooldowns["spot_player"] <= 0:
                self.spot_player()
        elif self.cooldowns["get_hit"] <= 0:
            if self.spot_player() and self.cooldowns["spot_player"] > 0:
                dist = math.dist(self.player.rect.center, self.rect.center)
                self.should_move_horiz = True
                if self.can_shoot:
                    self.direction = MovementDirection(math.copysign(1, self.rect.centerx - self.player.rect.centerx))
                    self.facing = self.direction.swap()
                    if dist < self.spot_range // 2:
                        self.x_vel = self.direction * vel
                    else:
                        self.x_vel = 0
                else:
                    self.direction = self.facing = MovementDirection(math.copysign(1, self.player.rect.centerx - self.rect.centerx))
                    self.x_vel = self.direction * min(vel, abs(dist - (3 * self.width // 4)))
            elif self.cooldowns["spot_player"] <= 0:
                self.facing = self.direction
                if self.patrol_path_index >= 0 and self.direction == MovementDirection.LEFT:
                    if self.rect.x > self.patrol_path[self.patrol_path_index][0]:
                        self.x_vel = self.direction * vel
                        self.should_move_horiz = True
                    else:
                        self.increment_patrol_index()
                elif self.patrol_path_index < 0 and self.direction == MovementDirection.RIGHT:
                    if self.rect.x < self.patrol_path[self.patrol_path_index][0]:
                        self.x_vel = self.direction * vel
                        self.should_move_horiz = True
                    else:
                        self.increment_patrol_index()
                else:
                    self.direction = self.direction.swap()
                    self.facing = self.facing.swap()
    def spot_player(self, spot_cd=PLAYER_SPOT_COOLDOWN):
        if self.player.is_crouching:
            self.spot_range /= 2
        dist = math.dist(self.player.rect.center, self.rect.center)
        if dist <= self.spot_range and (self.facing == MovementDirection(math.copysign(1, self.player.rect.centerx - self.rect.centerx)) or dist <= self.width // 2):
            for i in range(round(dist)):
                for obj in self.objects:
                    if obj.rect.collidepoint(self.rect.centerx + (self.facing * ((self.rect.width // 2) + i)), self.rect.y):
                        return False
            self.cooldowns["spot_player"] = spot_cd
            if self.state in [MovementState.IDLE, MovementState.CROUCH, MovementState.RUN, MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK] and self.can_shoot and dist > self.spot_range // 3:
                self.shoot_at_target(self.player.rect.center)
            return True
        return False

    def collide(self, obj):
        if obj != self.player and not obj.is_stacked and self.direction == MovementDirection(math.copysign(1, obj.rect.centerx - self.rect.centerx)):
            self.jump()
        elif self.cooldowns["spot_player"] <= 0 and self.patrol_path is not None:
            self.increment_patrol_index()
        return True

    def output(self, win, offset_x, offset_y, player, master_volume):
        if self.difficulty <= DifficultyScale.EASY:
            adj_x_image = self.rect.x - offset_x
            adj_y_image = self.rect.y - offset_y
            window_width = win.get_width()
            window_height = win.get_height()
            if player.is_crouching:
                self.spot_range /= 2
            if -self.spot_range < adj_x_image <= window_width and -self.rect.height < adj_y_image <= window_height:
                vision = pygame.surface.Surface((self.spot_range + (self.rect.width // 2), self.rect.height // 4), pygame.SRCALPHA)
                gradient_max = 256
                num_chunks = vision.get_width() // gradient_max
                chunk = pygame.surface.Surface((num_chunks, vision.get_height()), pygame.SRCALPHA)
                if self.cooldowns["spot_player"] <= 0:
                    chunk.fill((0, 255, 0))
                else:
                    chunk.fill((255, 0, 0))
                for i in range(gradient_max):
                    if self.facing == MovementDirection.LEFT:
                        chunk.set_alpha(i)
                    else:
                        chunk.set_alpha(gradient_max - i)
                    vision.blit(chunk, (i * num_chunks, 0))
                if self.facing == MovementDirection.LEFT:
                    adj_x_image -= self.spot_range - self.rect.width
                else:
                    adj_x_image += (self.rect.width // 2)
                adj_y_image += 7 * self.rect.height // 24
                win.blit(vision, (adj_x_image, adj_y_image))
        super().output(win, offset_x, offset_y, player, master_volume)