import math
import pygame
import time
from Actor import Actor, MovementState
from Block import Door
from Helpers import DifficultyScale, MovementDirection, load_text_from_file, load_audios, display_text
from os.path import isfile, join


class NonPlayer(Actor):
    VELOCITY_TARGET = 0.25
    PLAYER_SPOT_RANGE = 3
    PLAYER_SPOT_COOLDOWN = 2

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, path=None, is_hostile=True, collision_message=None, hp=100, can_shoot=False, spot_range=PLAYER_SPOT_RANGE, sprite=None, proj_sprite=None, name="Enemy"):
        super().__init__(level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name=name)
        self.is_hostile = is_hostile
        if collision_message is not None:
            if type(collision_message) == dict and collision_message.get("text") is not None and collision_message.get("audio") is not None:
                audio_file = join("Assets", "SoundEffects", "Text", collision_message["audio"])
                if isfile(audio_file):
                    self.collision_message = {"text": load_text_from_file(collision_message["text"]), "audio": pygame.mixer.Sound(audio_file)}
                else:
                    self.collision_message = load_text_from_file(collision_message["text"])
            else:
                self.collision_message = load_text_from_file(collision_message)
        else:
            self.collision_message = None
        self.queued_message = None
        self.patrol_path = path
        self.spot_range = spot_range * block_size
        if path is None:
            self.max_jumps = 0
            self.spot_range *= 2
        self.patrol_path_index = 0
        if self.patrol_path is not None:
            for point in self.patrol_path:
                point[0] += (block_size - self.rect.width) // 2
                point[1] += (block_size - self.rect.height)
            min_dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[0])
            for i in range(len(self.patrol_path)):
                dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[i])
                if dist < min_dist:
                    self.patrol_path_index = i
            self.direction = self.facing = (MovementDirection.RIGHT if self.patrol_path[self.patrol_path_index][0] - self.rect.x >= 0 else MovementDirection.LEFT)
        self.max_hp = self.hp = self.cached_hp = hp * self.difficulty
        self.cooldowns.update({"spot_player": 0})
        self.cached_cooldowns = self.cooldowns.copy()
        vision_hidden = pygame.Surface((256, 10), pygame.SRCALPHA)
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
        if self.level.grayscale:
            vision_hidden = pygame.transform.grayscale(vision_hidden)
            vision_spotted = pygame.transform.grayscale(vision_spotted)
        self.vision = {"hidden": {MovementDirection.LEFT: vision_hidden, MovementDirection.RIGHT: pygame.transform.flip(vision_hidden, True, False)}, "spotted": {MovementDirection.LEFT: vision_spotted, MovementDirection.RIGHT: pygame.transform.flip(vision_spotted, True, False)}}

    def __increment_patrol_index__(self) -> None:
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index >= len(self.patrol_path) - 1:
            self.patrol_path_index = -1
        elif self.patrol_path_index <= -len(self.patrol_path):
            self.patrol_path_index = 0

    def __find_floor__(self, dist) -> bool:
        for block in self.level.get_objects_in_range((self.rect.x + dist, self.rect.bottom), blocks_only=True):
            if block.rect.collidepoint(self.rect.centerx + dist, self.rect.bottom):
                return True
        return False

    def play_queued_message(self) -> int:
        start = time.perf_counter_ns()
        if type(self.queued_message) == dict and self.queued_message.get("text") is not None and self.queued_message.get("audio") is not None:
            display_text(self.queued_message["text"], self.controller, audio=self.queued_message["audio"],
                         type=True)
        else:
            display_text(self.queued_message, self.controller, type=True)
        self.queued_message = None
        return (time.perf_counter_ns() - start) // 1000000

    def patrol(self, dtime, vel=VELOCITY_TARGET) -> None:
        self.should_move_horiz = False
        if self.cooldowns["get_hit"] <= 0 and self.state != MovementState.WIND_UP and self.state != MovementState.WIND_DOWN:
            if self.patrol_path is None:
                self.should_move_vert = False
                self.direction = self.facing = (MovementDirection.RIGHT if self.level.get_player().rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT)
                if self.is_hostile and self.cooldowns["spot_player"] <= 0:
                    _ = self.__spot_player__()
                    if math.dist(self.level.get_player().rect.center, self.rect.center) >= self.spot_range // 3:
                        self.is_attacking = True
                    elif not self.is_animated_attack:
                        self.is_attacking = False
            else:
                if self.is_hostile and (self.__spot_player__() or self.cooldowns["spot_player"] > 0):
                    dist = math.dist(self.level.get_player().rect.center, self.rect.center)
                    if self.can_shoot:
                        if dist < self.spot_range // 3:
                            if abs(self.rect.x - self.level.get_player().rect.x) > 5:
                                self.direction = (MovementDirection.RIGHT if self.rect.centerx - self.level.get_player().rect.centerx >= 0 else MovementDirection.LEFT)
                                self.facing = self.direction.swap()
                                self.x_vel = self.direction * vel
                                self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)
                            if not self.is_animated_attack:
                                self.is_attacking = False
                        else:
                            self.is_attacking = True
                            self.x_vel = 0.0
                    else:
                        if pygame.sprite.collide_rect(self, self.level.get_player()):
                            self.is_attacking = True
                            if abs(self.rect.x - self.level.get_player().rect.x) <= 5 or pygame.sprite.collide_mask(self, self.level.get_player()):
                                self.x_vel = 0.0
                                if not self.is_animated_attack:
                                    self.play_attack_audio("ATTACK_MELEE")
                            else:
                                self.direction = self.facing = (MovementDirection.RIGHT if self.level.get_player().rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT)
                                self.x_vel = self.direction * min(vel, dist / dtime)
                                self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)
                        else:
                            if dist < self.rect.width:
                                self.direction = self.facing = (MovementDirection.RIGHT if self.level.get_player().rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT)
                            if not self.is_animated_attack:
                                self.is_attacking = False
                            self.x_vel = self.direction * min(vel, dist / dtime)
                            self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)
                else:
                    if self.is_attacking and not self.is_animated_attack:
                        self.is_attacking = False
                    target_x = self.patrol_path[self.patrol_path_index][0] - self.rect.x
                    if abs(target_x) > 5:
                        self.direction = self.facing = (MovementDirection.RIGHT if target_x >= 0 else MovementDirection.LEFT)
                        self.x_vel = self.direction * min(vel, abs(target_x) / dtime)
                        self.should_move_horiz = self.__find_floor__(self.x_vel * dtime)

                    target_y = self.patrol_path[self.patrol_path_index][1] - self.rect.y
                    if self.should_move_horiz and self.jump_count < self.max_jumps and target_y < -5:
                        self.jump()
                        self.should_move_vert = True

                    if not self.should_move_horiz and not self.should_move_vert:
                        self.__increment_patrol_index__()

    def __adj_spot_range__(self) -> float:
        return self.spot_range * self.level.get_player().size / (1.5 if self.level.get_player().is_crouching else 1)

    def __spot_player__(self, spot_cd=PLAYER_SPOT_COOLDOWN) -> bool:
        dist = math.dist(self.level.get_player().rect.center, self.rect.center)
        if dist <= self.__adj_spot_range__() and (self.facing == (MovementDirection.RIGHT if self.level.get_player().rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT) or self.cooldowns["get_hit"] > 0):
            for i in range(round(dist)):
                for obj in self.level.get_objects_in_range((self.rect.centerx + (self.facing * ((self.rect.width // 2) + i)), self.rect.y), blocks_only=True):
                    if obj.rect.collidepoint(self.rect.centerx + (self.facing * ((self.rect.width // 2) + i)), self.rect.y):
                        return False
            self.cooldowns["spot_player"] = spot_cd
            if self.state in [MovementState.IDLE, MovementState.CROUCH, MovementState.RUN, MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK] and self.can_shoot and dist > self.spot_range // 3:
                self.shoot_at_target(self.level.get_player().rect.center)
            return True
        return False

    def collide(self, obj) -> bool:
        if obj != self.level.get_player():
            if self.direction == (MovementDirection.RIGHT if obj.rect.centerx - self.rect.centerx > 0 else MovementDirection.LEFT):
                if obj.is_stacked or isinstance(obj, Door):
                    if self.patrol_path is not None:
                        for point in range(len(self.patrol_path)):
                            self.__increment_patrol_index__()
                            if self.direction == MovementDirection.RIGHT and self.rect.centerx > self.patrol_path[self.patrol_path_index][0]:
                                self.direction = self.facing = self.direction.swap()
                                break
                            elif self.direction == MovementDirection.LEFT and self.rect.centerx < self.patrol_path[self.patrol_path_index][0]:
                                self.direction = self.facing = self.direction.swap()
                                break
                else:
                    self.jump()
            elif self.cooldowns["spot_player"] <= 0 and self.patrol_path is not None:
                self.__increment_patrol_index__()
        elif self.collision_message is not None:
            self.queued_message = self.collision_message
            self.collision_message = None
        return True

    def output(self, win, offset_x, offset_y, master_volume, fps) -> None:
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
        super().output(win, offset_x, offset_y, master_volume, fps)