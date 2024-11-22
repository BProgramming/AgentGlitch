import random
import pygame
from Actor import Actor, MovementState
from Object import Object
from Enemy import Enemy
from Block import BreakableBlock
from Helpers import MovementDirection, load_sprite_sheets


class Player(Actor):
    ATTACK_PUSHBACK = 0.2
    VELOCITY_TARGET = 0.5
    VELOCITY_DRAG = 0.9
    GRAVITY = 0.02
    MULTIPLIER_TELEPORT = 384
    TELEPORT_COOLDOWN = 3
    TELEPORT_DELAY = 0.5
    BLOCK_COOLDOWN = 3
    BLOCK_TIME_ACTIVE = 2
    BULLET_TIME_COOLDOWN = 3
    BULLET_TIME_ACTIVE = 2

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=False, sprite=None, retro_sprite=None, proj_sprite=None):
        super().__init__(level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name="Player")
        self.sprites_set = (self.sprites.copy(), load_sprite_sheets("Sprites", retro_sprite, sprite_master, direction=True, grayscale=True) if retro_sprite is not None else None)
        self.is_retro = False
        if self.level.grayscale:
            self.toggle_retro()
            self.update_sprite(1)
        self.cooldowns.update({"teleport": 0, "teleport_delay": 0, "block": 0, "block_attempt": 0, "bullet_time": 0, "bullet_time_active": 0})
        self.cached_cooldowns = self.cooldowns.copy()
        self.can_open_doors = True
        self.can_move_blocks = True
        self.can_block = True
        self.is_blocking = False
        self.can_wall_jump = True
        self.can_teleport = False
        self.can_bullet_time = False
        self.is_slow_time = False
        self.can_resize = False
        self.can_heal = True
        self.max_jumps = 2
        self.attack_damage *= 2
        self.max_hp = self.hp = self.cached_hp = 100 / self.difficulty

    def toggle_retro(self):
        if self.is_retro:
            self.sprites = self.sprites_set[0]
            self.is_retro = False
        else:
            self.sprites = self.sprites_set[1]
            self.is_retro = True

    def save(self):
        data = super().save()
        data[self.name].update({"can_teleport": self.can_teleport, "can_bullet_time": self.can_bullet_time})
        return data

    def load(self, obj):
        self.load_attribute(obj, "can_teleport")
        self.load_attribute(obj, "can_bullet_time")
        super().load(obj)

    def set_difficulty(self, scale):
        self.difficulty = scale
        self.max_hp /= scale
        self.hp /= scale
        self.attack_damage /= scale

    def toggle_crouch(self):
        self.is_crouching = not self.is_crouching

    def stop(self):
        self.should_move_horiz = False

    def block(self, block_time=BLOCK_TIME_ACTIVE, block_cd=BLOCK_COOLDOWN):
        if self.can_block:
            if self.cooldowns["block"] > 0:
                pass
            elif not self.is_blocking:
                self.is_blocking = True
                self.cooldowns["block_attempt"] = block_time
                self.cooldowns["block"] = block_cd
            elif self.cooldowns["block_attempt"] <= 0:
                self.is_blocking = False
                self.cooldowns["block"] = block_cd

    def get_hit(self, obj, block_cd=BLOCK_COOLDOWN, _=None):
        if isinstance(obj, Enemy) and self.cooldowns["block"] <= 0 and self.is_blocking:
            self.cooldowns["block"] = block_cd
            self.is_blocking = False
        else:
            super().get_hit(obj)

    def move_left(self):
        self.should_move_horiz = True
        if self.direction != MovementDirection.LEFT:
            self.direction = self.facing = MovementDirection.LEFT

    def move_right(self):
        self.should_move_horiz = True
        if self.direction != MovementDirection.RIGHT:
            self.direction = self.facing = MovementDirection.RIGHT

    def revert(self):
        self.should_move_vert = False
        self.rect.x, self.rect.y = self.cached_x, self.cached_y
        self.hp = self.cached_hp
        self.size = self.cached_size
        self.size_target = self.cached_size_target
        self.cooldowns = self.cached_cooldowns

    def teleport(self, vel=(VELOCITY_TARGET * MULTIPLIER_TELEPORT), delay=TELEPORT_DELAY, cd=TELEPORT_COOLDOWN):
        if self.can_teleport and self.cooldowns["teleport"] <= 0:
            for i in range(int(vel) + 1, 0, -1):
                cast = Object(self.level, self.controller, self.rect.x + (self.direction * i), self.rect.y, self.rect.width, self.rect.height - 1)
                collision = False
                for obj in self.level.get_objects_in_range((cast.rect.x, cast.rect.y)):
                    if pygame.sprite.collide_rect(cast, obj):
                        collision = True
                        break
                if not collision:
                    self.teleport_distance = self.direction * i
                    self.cooldowns["teleport_delay"] = delay
                    self.cooldowns["teleport"] = cd
                    return

    def attack(self, push=ATTACK_PUSHBACK):
        if self.state in [MovementState.IDLE, MovementState.CROUCH, MovementState.RUN, MovementState.FALL, MovementState.JUMP, MovementState.DOUBLE_JUMP, MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK, MovementState.FALL_ATTACK, MovementState.JUMP_ATTACK, MovementState.DOUBLE_JUMP_ATTACK]:
            self.is_attacking = True
            for obj in self.level.get_objects_in_range((self.rect.x, self.rect.y)):
                if isinstance(obj, Enemy) and pygame.sprite.collide_rect(self, obj):
                    obj.get_hit(self)
                    if obj.patrol_path is not None:
                        obj.rect.x -= self.direction * push
                    self.play_melee_attack_audio()
                elif isinstance(obj, BreakableBlock) and pygame.sprite.collide_rect(self, obj):
                    obj.get_hit(self)
                    self.play_melee_attack_audio()

    def bullet_time(self, active_time=BULLET_TIME_ACTIVE, cd=BULLET_TIME_COOLDOWN):
        if self.can_bullet_time:
            if self.is_slow_time:
                self.is_slow_time = False
                self.cooldowns["bullet_time_active"] = 0
                self.cooldowns["bullet_time"] = min(cd, self.cooldowns["bullet_time"])
            elif self.cooldowns["bullet_time"] <= 0:
                self.is_slow_time = True
                self.cooldowns["bullet_time_active"] = active_time
                self.cooldowns["bullet_time"] = cd + active_time
                if self.audios.get("BULLET_TIME") is not None:
                    active_audio_channel = pygame.mixer.find_channel()
                    if active_audio_channel is not None:
                        active_audio_channel.play(self.audios["BULLET_TIME"][random.randrange(len(self.audios["BULLET_TIME"]))])
                        active_audio_channel.set_volume(self.controller.master_volume["player"])

    def get_triggers(self):
        fired_triggers = 0
        next_level = None
        for trigger in self.level.triggers:
            if pygame.sprite.collide_rect(self, trigger):
                result = trigger.collide()
                fired_triggers += result[0]
                next_level = result[1]
                if trigger.fire_once:
                    self.level.queue_purge(trigger)
        return [fired_triggers, next_level]

    def loop(self, fps, dtime, target=VELOCITY_TARGET, drag=VELOCITY_DRAG, grav=GRAVITY):
        if self.teleport_distance != 0:
            self.animation_count += dtime
            if self.cooldowns["teleport_delay"] <= 0:
                self.move(self.teleport_distance, 0)
                self.teleport_distance = 0
            self.update_cooldowns(dtime)
            self.update_state()
        else:
            if self.is_slow_time and self.cooldowns["bullet_time_active"] <= 0:
                self.is_slow_time = False
            super().loop(fps, dtime, target=target, drag=drag, grav=grav)

        return self.get_triggers()
