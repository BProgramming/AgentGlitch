import math
import pygame
import random
from enum import Enum
from Object import Object
from Projectile import Projectile
from Block import Hazard, MovableBlock, MovingBlock
from Helpers import load_sprite_sheets, MovementDirection, set_sound_source


class MovementState(Enum):
    IDLE = 0
    RUN = 1
    CROUCH = 2
    JUMP = 3
    DOUBLE_JUMP = 4
    WALL_JUMP = 5
    FALL = 6
    HIT = 7
    TELEPORT = 8
    RESIZE = 9
    SHOOT = 10
    IDLE_ATTACK = 11
    CROUCH_ATTACK = 12
    RUN_ATTACK = 13
    FALL_ATTACK = 14
    JUMP_ATTACK = 15
    DOUBLE_JUMP_ATTACK = 16
    WIND_UP = 17
    ATTACK_ANIM = 18
    WIND_DOWN = 19

    def __str__(self):
        return self.name


class Actor(Object):
    SIZE = 64
    VELOCITY_TARGET = 0.4
    VELOCITY_JUMP = 10
    ANIMATION_DELAY = 0.3
    GRAVITY = 0.02
    GET_HIT_COOLDOWN = 1
    MAX_SHOOT_DISTANCE = 500
    ATTACK_DAMAGE = 10
    LAUNCH_PROJECTILE_COOLDOWN = 1
    RESIZE_COOLDOWN = 3
    RESIZE_DELAY = 0.5
    RESIZE_SCALE_LIMIT = 1.5
    HEAL_DELAY = 5

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=False, can_resize=False, width=SIZE, height=SIZE, attack_damage=ATTACK_DAMAGE, sprite=None, proj_sprite=None, name=None):
        super().__init__(level, controller, x, y, width, height, name=name)
        self.patrol_path = None
        self.x_vel = self.y_vel = 0.0
        self.push_x = self.push_y = 0.0
        self.should_move_horiz = False
        self.should_move_vert = True
        self.teleport_distance = 0
        self.is_crouching = False
        self.can_open_doors = False
        self.can_move_blocks = False
        self.can_wall_jump = False
        self.is_wall_jumping = False
        self.jump_count = 0
        self.max_jumps = 1
        self.can_shoot = False
        self.state = MovementState.IDLE
        self.state_changed = False
        self.idle_count = 0
        self.direction = self.facing = MovementDirection.RIGHT
        self.animation_count = 0
        self.is_final_anim_frame = False
        self.is_animated_attack = False
        self.size = self.size_target = self.cached_size = self.cached_size_target = 1
        self.sprite_name = ("UnarmedAgent" if sprite is None else sprite)
        self.sprites = load_sprite_sheets("Sprites", ("UnarmedAgent" if sprite is None else sprite), sprite_master, direction=True, grayscale=self.level.grayscale)
        self.sprite = None
        self.audios = audios
        self.update_sprite(1)
        self.__update_geo__()
        self.rect.x += (block_size - self.rect.width) // 2
        self.rect.y += (block_size - self.rect.height)
        self.audio_trigger_frames = {"TELEPORT": [0], "RUN": [4, 10], "JUMP": [0], "DOUBLE_JUMP": [0], "CROUCH": [0], "HIT": [0], "RESIZE": [0]}
        self.active_audio = None
        self.active_audio_time = 0
        self.active_audio_channel = None
        self.difficulty = difficulty
        self.is_attacking = False
        self.attack_damage = attack_damage * difficulty
        self.can_shoot = can_shoot
        self.can_resize = can_resize
        self.can_heal = False
        self.proj_sprite = load_sprite_sheets("Projectiles", ("Bullet" if proj_sprite is None else proj_sprite), sprite_master, grayscale=self.level.grayscale)[("Bullet" if proj_sprite is None else proj_sprite).upper()][0]
        self.active_projectiles = []
        self.cached_x, self.cached_y = x, y
        self.cooldowns = {"get_hit": 0, "launch_projectile": 0, "resize": 0, "resize_delay": 0, "heal": 0, "attack": 0}
        self.cached_cooldowns = self.cooldowns.copy()

    def save(self):
        projectiles = []
        for proj in self.active_projectiles:
            projectiles.append(proj.save())
        return {self.name: {"hp": self.hp, "cached x y": (self.cached_x, self.cached_y), "cooldowns": self.cached_cooldowns, "size": self.size, "can_wall_jump": self.can_wall_jump, "can_shoot": self.can_shoot, "can_resize": self.can_resize, "max_jumps": self.max_jumps, "projectiles": projectiles}}

    def load(self, obj):
        self.rect.x, self.rect.y = self.cached_x, self.cached_y = obj["cached x y"]
        self.cooldowns = self.cached_cooldowns = obj["cooldowns"]
        self.load_attribute(obj, "hp")
        self.cached_hp = self.hp
        self.load_attribute(obj, "size")
        self.load_attribute(obj, "can_wall_jump")
        self.load_attribute(obj, "can_shoot")
        self.load_attribute(obj, "can_resize")
        self.load_attribute(obj, "max_jumps")
        for proj in obj["projectiles"]:
            self.active_projectiles.append(Projectile(self.level, self.controller, self.rect.centerx + (self.rect.width * self.facing // 3), self.rect.centery, None, 0, self.attack_damage, self.difficulty, sprite=self.proj_sprite, name=(self.name + "'s projectile #" + str(len(self.active_projectiles) + 1))))
            self.active_projectiles[-1].load(list(proj.values())[0])
        self.update_sprite(1)
        self.__update_geo__()

    def set_difficulty(self, scale):
        self.difficulty = scale
        self.max_hp *= scale
        self.hp *= scale
        self.attack_damage *= scale
        for proj in self.active_projectiles:
            proj.set_difficulty(scale)
            proj.attack_damage = self.attack_damage

    def grow(self, resize_cd=RESIZE_COOLDOWN, delay_cd=RESIZE_DELAY, max_scale=RESIZE_SCALE_LIMIT):
        if self.can_resize and self.cooldowns["resize"] <= 0:
            target = min(self.size_target * max_scale, max_scale)
            if self.size_target != target:
                self.size_target = target
                self.cooldowns["resize"] = resize_cd
                self.cooldowns["resize_delay"] = delay_cd
                self.attack_damage *= target

    def shrink(self, resize_cd=RESIZE_COOLDOWN, delay_cd=RESIZE_DELAY, max_scale=RESIZE_SCALE_LIMIT):
        if self.can_resize and self.cooldowns["resize"] <= 0:
            target = max(self.size_target / max_scale, 1 / max_scale)
            if self.size_target != target:
                self.size_target = target
                self.cooldowns["resize"] = resize_cd
                self.cooldowns["resize_delay"] = delay_cd
                self.attack_damage *= target

    def move(self, dx, dy):
        if dx != 0:
            if self.rect.left + dx < self.level.level_bounds[0][0] - (self.rect.width // 5):
                self.rect.left = -self.rect.width // 5
            elif self.rect.right + dx > self.level.level_bounds[1][0] + (self.rect.width // 5):
                self.rect.right = self.level.level_bounds[1][0] + (self.rect.width // 5)
            else:
                self.rect.x += dx

        if dy != 0:
            if self.rect.top + dy < self.level.level_bounds[0][1]:
                self.hit_head()
            elif self.rect.top + dy > self.level.level_bounds[1][1]:
                self.hp = 0
            else:
                self.rect.y += dy

    def cache(self):
        if self.cooldowns["get_hit"] <= 0 and self.state != MovementState.HIT and self.hp == self.max_hp and self.jump_count == 0 and self.y_vel == 0:
            self.cached_x, self.cached_y = self.rect.x, self.rect.y
            self.cached_hp = self.hp
            self.cached_size = self.size
            self.cached_size_target = self.size_target
            self.cached_cooldowns = self.cooldowns.copy()

    def revert(self):
        pass

    def jump(self, target=VELOCITY_JUMP):
        if self.jump_count < self.max_jumps:
            self.y_vel = -target
            self.jump_count += 1
            self.should_move_vert = True
            if self.is_wall_jumping:
                self.is_wall_jumping = False
                self.direction = self.direction.swap()
                self.facing = self.facing.swap()
                self.move(self.direction * self.rect.width // 4, 0)
        self.is_crouching = False

    def land(self):
        if self.y_vel > 20:
            self.hp -= 2 * self.y_vel
        self.y_vel = 0.0
        self.jump_count = 0
        self.should_move_vert = False
        self.is_wall_jumping = False

    def hit_head(self):
        self.y_vel *= -0.5

    def play_attack_audio(self, attack_type):
        if attack_type in self.audios:
            active_audio_channel = pygame.mixer.find_channel()
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[attack_type][random.randrange(len(self.audios[attack_type]))])
                if self == self.level.get_player():
                    active_audio_channel.set_volume(self.controller.master_volume["player"])
                else:
                    set_sound_source(self.rect, self.level.get_player().rect, self.controller.master_volume["non-player"], active_audio_channel)

    def shoot_at_target(self, target, max_dist=MAX_SHOOT_DISTANCE, proj_cd=LAUNCH_PROJECTILE_COOLDOWN):
        if self.cooldowns["launch_projectile"] <= 0:
            self.is_attacking = True
            proj = Projectile(self.level, self.controller, self.rect.centerx, self.rect.centery, (target[0], self.rect.centery), max_dist, self.attack_damage, self.difficulty, sprite=self.proj_sprite, name=(self.name + "'s projectile #" + str(len(self.active_projectiles) + 1)))
            self.active_projectiles.append(proj)
            self.cooldowns["launch_projectile"] = proj_cd
            self.play_attack_audio("ATTACK_RANGE")

    def get_hit(self, obj, hit_cd=GET_HIT_COOLDOWN, heal_delay=HEAL_DELAY):
        self.cooldowns["get_hit"] = hit_cd
        self.cooldowns["heal"] = heal_delay * self.difficulty
        self.hp -= obj.attack_damage

    def get_collisions(self):
        collided = False

        for obj in self.level.get_objects_in_range((self.rect.x, self.rect.y)) if self == self.level.get_player() else [self.level.get_player()] + self.level.get_objects_in_range((self.rect.x, self.rect.y), blocks_only=True):
            if pygame.sprite.collide_rect(self, obj):
                if pygame.sprite.collide_mask(self, obj):
                    if isinstance(obj, Actor):
                        overlap = self.mask.overlap_mask(obj.mask, (0, 0)).get_rect()
                    else:
                        overlap = self.rect.clip(obj.rect)
                    if (isinstance(obj, Actor) and obj != self.level.get_player()):
                        if obj.is_attacking and self.cooldowns["get_hit"] <= 0:
                            self.get_hit(obj)
                    elif isinstance(obj, Hazard):
                        if obj.is_attacking and self.cooldowns["get_hit"] <= 0:
                            if overlap.width <= overlap.height and ((self.rect.x <= obj.rect.x and "L" in obj.hit_sides) or (self.rect.x >= obj.rect.x and "R" in obj.hit_sides)):
                                self.get_hit(obj)
                            if overlap.width >= overlap.height and ((self.rect.y <= obj.rect.y and "U" in obj.hit_sides) or (self.rect.y >= obj.rect.y and "D" in obj.hit_sides)):
                                self.get_hit(obj)
                    if obj.collide(self):
                        self.collide(obj)
                        if overlap.width <= overlap.height and (self.x_vel == 0 or self.direction == (MovementDirection.RIGHT if self.x_vel >= 0 else MovementDirection.LEFT)):
                            if self.can_move_blocks and isinstance(obj, MovableBlock) and obj.should_move_horiz and self.direction == (MovementDirection.RIGHT if obj.rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT):
                                obj.push_x = self.x_vel * self.size
                            if self.x_vel <= 0 and self.rect.centerx > obj.rect.centerx:
                                self.rect.left = obj.rect.right - (self.rect.width // 5)
                                self.x_vel = 0.0
                            elif self.x_vel >= 0 and self.rect.centerx <= obj.rect.centerx:
                                self.rect.right = obj.rect.left + (self.rect.width // 5)
                                self.x_vel = 0.0
                            collided = True

                        if overlap.width >= overlap.height:
                            if self.y_vel >= 0 and not obj.is_stacked and self.rect.bottom == overlap.bottom:
                                self.rect.bottom = obj.rect.top
                                self.land()
                            elif self.y_vel < 0 and self.rect.top == overlap.top:
                                self.rect.top = obj.rect.bottom
                                self.hit_head()

                        if collided and self.should_move_vert and not self.is_wall_jumping and self.direction == (MovementDirection.RIGHT if overlap.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT):
                            self.y_vel = min(self.y_vel, 0.0)
                            self.jump_count = 0
                            self.is_wall_jumping = True

            elif obj.rect.top <= self.rect.bottom <= obj.rect.bottom and self.rect.left + (self.rect.width // 4) <= obj.rect.right and self.rect.right - (self.rect.width // 4) >= obj.rect.left:
                if isinstance(obj, MovingBlock) or isinstance(obj, MovableBlock):
                    obj.collide(self)
                if self.rect.centerx != obj.rect.centerx:
                    if math.degrees(math.atan(abs(self.rect.centery - obj.rect.centery) / abs(self.rect.centerx - obj.rect.centerx))) >= 45:
                        self.should_move_vert = False
                        if self.rect.bottom != obj.rect.top:
                            self.rect.bottom = obj.rect.top

        if self.x_vel != 0 and not collided and self.is_wall_jumping:
            self.is_wall_jumping = False
        return collided

    def die(self):
        pass

    def update_state(self):
        old = self.state
        if self.size_target != self.size:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
            if self.state != MovementState.RESIZE:
                self.state = MovementState.RESIZE
                self.animation_count = 0
        # this is for boss enemies with complex attack animations
        elif self.is_animated_attack and self.is_attacking:
            if self.state not in [MovementState.WIND_UP, MovementState.ATTACK_ANIM, MovementState.WIND_DOWN]:
                self.state = MovementState.WIND_UP
                self.animation_count = 0
            elif self.is_final_anim_frame:
                if self.state == MovementState.WIND_UP:
                    self.state = MovementState.ATTACK_ANIM
                    self.animation_count = 0
                elif self.state == MovementState.ATTACK_ANIM:
                    self.state = MovementState.WIND_DOWN
                    self.animation_count = 0
                else:
                    self.is_attacking = False
                    return self.update_state()
        elif self.cooldowns["get_hit"] > 0:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
            if self.state != MovementState.HIT:
                self.state = MovementState.HIT
                self.animation_count = 0
        else:
            if self.teleport_distance != 0:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
                if self.state != MovementState.TELEPORT:
                    self.state = MovementState.TELEPORT
                    self.animation_count = 0
            elif self.should_move_vert:
                if self.can_wall_jump and self.is_wall_jumping:
                    if self.state != MovementState.WALL_JUMP:
                        self.state = MovementState.WALL_JUMP
                        self.animation_count = 0
                else:
                    if self.y_vel > 1:
                        if self.is_attacking and self.state != MovementState.FALL_ATTACK:
                            if self.state != MovementState.FALL:
                                self.animation_count = 0
                            self.state = MovementState.FALL_ATTACK
                        elif not self.is_attacking and self.state != MovementState.FALL:
                            if self.state != MovementState.FALL_ATTACK:
                                self.animation_count = 0
                            self.state = MovementState.FALL
                    elif self.y_vel < 0:
                        if self.jump_count <= 1:
                            if self.is_attacking and self.state != MovementState.JUMP_ATTACK:
                                if self.state != MovementState.JUMP:
                                    self.animation_count = 0
                                self.state = MovementState.JUMP_ATTACK
                            elif not self.is_attacking and self.state != MovementState.JUMP:
                                if self.state != MovementState.JUMP_ATTACK:
                                    self.animation_count = 0
                                self.state = MovementState.JUMP
                        elif self.jump_count > 1:
                            if self.is_attacking and self.state != MovementState.DOUBLE_JUMP_ATTACK:
                                if self.state != MovementState.DOUBLE_JUMP:
                                    self.animation_count = 0
                                self.state = MovementState.DOUBLE_JUMP_ATTACK
                            elif not self.is_attacking and self.state != MovementState.DOUBLE_JUMP:
                                if self.state != MovementState.DOUBLE_JUMP_ATTACK:
                                    self.animation_count = 0
                                self.state = MovementState.DOUBLE_JUMP
            elif self.should_move_horiz:
                if self.is_crouching:
                    if self.is_attacking and self.state != MovementState.CROUCH_ATTACK:
                        if self.state != MovementState.CROUCH:
                            self.animation_count = 0
                        self.state = MovementState.CROUCH_ATTACK
                    elif not self.is_attacking and self.state != MovementState.CROUCH:
                        if self.state != MovementState.CROUCH_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.CROUCH
                elif not self.is_crouching:
                    if self.is_attacking and self.state != MovementState.RUN_ATTACK:
                        if self.state != MovementState.RUN:
                            self.animation_count = 0
                        self.state = MovementState.RUN_ATTACK
                    elif not self.is_attacking and self.state != MovementState.RUN:
                        if self.state != MovementState.RUN_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.RUN
            else:
                if self.is_attacking and self.state != MovementState.IDLE_ATTACK:
                    if self.state != MovementState.IDLE:
                        self.animation_count = 0
                    self.state = MovementState.IDLE_ATTACK
                elif not self.is_attacking and self.state != MovementState.IDLE:
                    if self.state != MovementState.IDLE_ATTACK:
                        self.animation_count = 0
                    self.state = MovementState.IDLE
            if str(self.state) + "_" + str(self.facing) not in self.sprites:
                self.state = old
        self.state_changed = bool(old != self.state)

    def update_sprite(self, fps, delay=ANIMATION_DELAY):
        active_sprites = self.sprites[str(self.state) + "_" + str(self.facing)]
        active_index = math.floor((self.animation_count // (1000 // (fps * delay))) % len(active_sprites))
        if active_index == len(active_sprites) - 1:
            self.is_final_anim_frame = True
        else:
            self.is_final_anim_frame = False
            if active_index >= len(active_sprites):
                active_index = 0
                self.animation_count = 0
        self.sprite = active_sprites[active_index]
        if self.size != 1:
            self.sprite = pygame.transform.smoothscale_by(self.sprite, self.size)

        if self.audios is not None and (self.state_changed or self.state == MovementState.RUN) and self.audio_trigger_frames.get(str(self.state)) is not None:
            if self.audios.get(str(self.state).replace("_ATTACK", "")) is not None and active_index in self.audio_trigger_frames[str(self.state).replace("_ATTACK", "")]:
                self.active_audio = self.audios[str(self.state).replace("_ATTACK", "")][random.randrange(len(self.audios[str(self.state).replace("_ATTACK", "")]))]
                if self.active_audio_channel is not None:
                    self.active_audio_channel.stop()
                    self.active_audio_channel = None

        return active_index

    def __update_geo__(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def loop(self, fps, dtime, target=VELOCITY_TARGET, drag=0, grav=GRAVITY):
        self.animation_count += dtime

        if self.hp <= 0:
            self.die()
        super().loop(fps, dtime)

        if self.can_heal and self.hp < self.max_hp and self.cooldowns["heal"] <= 0:
            self.hp = min(self.max_hp, self.hp + (dtime * fps / (10000 * self.difficulty)))

        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                if proj.hp <= 0:
                    self.active_projectiles.remove(proj)
                else:
                    proj.loop(fps, dtime)

        if self.patrol_path is not None and self.state != MovementState.WIND_UP and self.state != MovementState.WIND_DOWN:
            self.should_move_vert = True
            self.push_x *= 0.9
            if abs(self.push_x) < 0.01:
                self.push_x = 0
            self.push_y = 0
            collided = self.get_collisions()

            if self.cooldowns["resize_delay"] <= 0:
                if self.size != self.size_target:
                    if self.size > self.size_target:
                        self.rect.y += self.rect.height // 3
                    else:
                        self.rect.y -= self.rect.height // 2
                    self.size = self.size_target

                if self.should_move_horiz:
                    scaled_target = dtime * target
                    if abs(self.x_vel) < scaled_target:
                        self.x_vel = self.direction * min(scaled_target, (abs(self.x_vel) * drag) + (scaled_target * float(1 - drag)))
                else:
                    self.x_vel = 0.0

                if self.should_move_vert:
                    self.y_vel += dtime * grav * self.size / (1 + (3 if self.is_wall_jumping and self.y_vel > 0 else 0))

                if (self.x_vel + self.push_x != 0 or self.y_vel + self.push_y != 0) and self.hp > 0:
                    if self.level.get_player().is_slow_time and self != self.level.get_player():
                        self.x_vel /= 2
                        self.y_vel /= 2

                    if self.state == MovementState.CROUCH:
                        self.x_vel /= 2

                    self.move(self.x_vel + self.push_x, self.y_vel + (self.push_y * dtime))
            else:
                self.move(self.push_x, (self.push_y * dtime))
        else:
            collided = False

        self.cache()
        self.update_state()
        return collided

    def output(self, win, offset_x, offset_y, master_volume, fps):
        adj_x_image = self.rect.x - offset_x
        adj_y_image = self.rect.y - offset_y
        #adj_x_audio = self.level.get_player().rect.x - self.rect.x
        #adj_y_audio = self.level.get_player().rect.y - self.rect.y
        window_width = win.get_width()
        window_height = win.get_height()
        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                proj.output(win, offset_x, offset_y, master_volume, fps)
        if self == self.level.get_player() or -self.rect.width < adj_x_image <= window_width and -self.rect.height < adj_y_image <= window_height:
            self.update_sprite(fps)
            self.__update_geo__()
            win.blit(self.sprite, (adj_x_image, adj_y_image))
            if self.cooldowns.get("block_attempt") is not None and self.cooldowns["block_attempt"] > 0:
                radius = math.dist((self.rect.x, self.rect.y), (self.rect.centerx, self.rect.centery))
                surf = pygame.Surface((2 * radius, 2 * radius))
                surf.set_colorkey((0, 0, 0))
                surf.set_alpha(128)
                pygame.draw.circle(surf, (65, 235, 245, 50), (radius, radius), radius)
                win.blit(surf, (adj_x_image - (radius - (self.rect.width // 2)), adj_y_image - (radius - (self.rect.height // 2))))

        if self.active_audio is not None:
            if self.active_audio_channel is None:
                self.active_audio_channel = pygame.mixer.find_channel()
                if self.active_audio_channel is not None:
                    self.active_audio_channel.play(self.active_audio)
            if self.active_audio_channel is not None and self.active_audio_channel.get_busy():
                if self == self.level.get_player():
                    self.active_audio_channel.set_volume(master_volume["player"])
                else:
                    set_sound_source(self.rect, self.level.get_player().rect, self.controller.master_volume["non-player"], self.active_audio_channel)
            else:
                self.active_audio = None
                self.active_audio_channel = None
