import math
import pygame
from Actor import Actor, MovementState
from Helpers import DifficultyScale, MovementDirection


class Enemy(Actor):
    VELOCITY_TARGET = 0.25
    PLAYER_SPOT_RANGE = 288
    PLAYER_SPOT_COOLDOWN = 2

    def __init__(self, level, x, y, sprite_master, audios, difficulty, path=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE, sprite=None, proj_sprite=None, name="Enemy"):
        super().__init__(level, x, y, sprite_master, audios, difficulty, can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name=name)
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
        vision_hidden = pygame.surface.Surface((256, 10), pygame.SRCALPHA)
        vision_spotted = vision_hidden.copy()
        chunk = pygame.surface.Surface((1, 10), pygame.SRCALPHA)
        chunk.fill((0, 255, 0))
        for i in range(256):
            chunk.set_alpha(i)
            vision_hidden.blit(chunk, (i, 0))
        chunk.fill((255, 0, 0))
        for i in range(256):
            chunk.set_alpha(i)
            vision_spotted.blit(chunk, (i, 0))
        if self.level.grayscale:
            vision_hidden = pygame.transform.grayscale(vision_hidden)
            vision_spotted = pygame.transform.grayscale(vision_spotted)
        self.vision = {"hidden": {MovementDirection.LEFT: vision_hidden, MovementDirection.RIGHT: pygame.transform.flip(vision_hidden, True, False)}, "spotted": {MovementDirection.LEFT: vision_spotted, MovementDirection.RIGHT: pygame.transform.flip(vision_spotted, True, False)}}

    def increment_patrol_index(self):
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index == len(self.patrol_path):
            self.patrol_path_index = -1
        elif self.patrol_path_index == -(len(self.patrol_path) + 1):
            self.patrol_path_index = 0

    def find_floor(self, dist):
        for block in self.level.blocks:
            if block.rect.collidepoint(self.rect.centerx + dist, self.rect.bottom + 1):
                return True
        return False

    def patrol(self, vel=VELOCITY_TARGET):
        self.should_move_horiz = False
        if self.cooldowns["get_hit"] <= 0:
            if self.patrol_path is None:
                self.direction = self.facing = MovementDirection(math.copysign(1, self.level.get_player().rect.centerx - self.rect.centerx))
                if self.cooldowns["spot_player"] <= 0:
                    self.spot_player()
            else:
                if self.spot_player() and self.cooldowns["spot_player"] > 0:
                    dist = math.dist(self.level.get_player().rect.center, self.rect.center)
                    if self.can_shoot:
                        self.direction = MovementDirection(math.copysign(1, self.rect.centerx - self.level.get_player().rect.centerx))
                        self.facing = self.direction.swap()
                        if dist >= self.spot_range // 2:
                            self.is_attacking = True
                            self.x_vel = 0.0
                        else:
                            self.is_attacking = False
                            self.x_vel = self.direction * vel
                    else:
                        self.direction = self.facing = MovementDirection(math.copysign(1, self.level.get_player().rect.centerx - self.rect.centerx))
                        if pygame.sprite.collide_mask(self, self.level.get_player()):
                            self.is_attacking = True
                            self.x_vel = 0.0
                        else:
                            self.is_attacking = False
                            self.x_vel = self.direction * min(vel, dist)
                    self.should_move_horiz = self.find_floor(self.x_vel)
                else:
                    self.is_attacking = False
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

                    if self.jump_count < self.max_jumps and self.state in [MovementState.FALL, MovementState.FALL_ATTACK]:
                        self.jump()

    def __adj_spot_range__(self):
        return self.spot_range * self.level.get_player().size / (1.5 if self.level.get_player().is_crouching else 1)

    def spot_player(self, spot_cd=PLAYER_SPOT_COOLDOWN):
        dist = math.dist(self.level.get_player().rect.center, self.rect.center)
        if dist <= self.__adj_spot_range__() and (self.facing == MovementDirection(math.copysign(1, self.level.get_player().rect.centerx - self.rect.centerx)) or self.cooldowns["get_hit"] > 0):
            for i in range(round(dist)):
                for obj in self.level.blocks:
                    if obj.rect.collidepoint(self.rect.centerx + (self.facing * ((self.rect.width // 2) + i)), self.rect.y):
                        return False
            self.cooldowns["spot_player"] = spot_cd
            if self.state in [MovementState.IDLE, MovementState.CROUCH, MovementState.RUN, MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK] and self.can_shoot and dist > self.spot_range // 3:
                self.shoot_at_target(self.level.get_player().rect.center)
            return True
        return False

    def collide(self, obj):
        if obj != self.level.get_player() and not obj.is_stacked and self.direction == MovementDirection(math.copysign(1, obj.rect.centerx - self.rect.centerx)):
            self.jump()
        elif self.cooldowns["spot_player"] <= 0 and self.patrol_path is not None:
            self.increment_patrol_index()
        return True

    def output(self, win, offset_x, offset_y, master_volume):
        if self.difficulty <= DifficultyScale.EASY:
            adj_x_image = self.rect.centerx - offset_x - (self.__adj_spot_range__() if self.facing == MovementDirection.LEFT else 0)
            adj_y_image = self.rect.y - offset_y + (7 * self.rect.height // 24)
            window_width = win.get_width()
            window_height = win.get_height()
            if -self.__adj_spot_range__() < adj_x_image <= window_width and -self.rect.height < adj_y_image <= window_height:
                if self.cooldowns["spot_player"] > 0:
                    vision = self.vision["spotted"][self.facing]
                else:
                    vision = self.vision["hidden"][self.facing]
                win.blit(pygame.transform.scale(vision, (self.__adj_spot_range__(), self.rect.height // 4)), (adj_x_image, adj_y_image))
        super().output(win, offset_x, offset_y, master_volume)