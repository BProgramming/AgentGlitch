import math
import pygame
import random
from enum import Enum
from Entity import Entity
from Projectile import Projectile
from Block import Hazard, MovableBlock, MovingBlock
from Objectives import Objective
from Helpers import load_sprite_sheets, MovementDirection, set_sound_source
from VisualEffects import VisualEffect


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

    def __str__(self) -> str:
        return self.name


class Actor(Entity):
    SIZE = 64
    VELOCITY_TARGET = 0.4
    VELOCITY_JUMP = 10
    GET_HIT_COOLDOWN = 1
    MAX_SHOOT_DISTANCE = 500
    ATTACK_DAMAGE = 10
    LAUNCH_PROJECTILE_COOLDOWN = 1
    RESIZE_COOLDOWN = 3
    RESIZE_DELAY = 0.5
    RESIZE_SCALE_LIMIT = 1.5
    RESIZE_EFFECT = 0.05
    HEAL_DELAY = 5
    DOUBLEJUMP_EFFECT_TRAIL = 0.08
    HORIZ_PUSH_DECAY_RATE = 0.03

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=False, can_resize=False, width=SIZE, height=SIZE, attack_damage=ATTACK_DAMAGE, sprite=None, proj_sprite=None, name=None):
        super().__init__(level, controller, x, y, width, height, name=name)
        self.cached_hp = self.hp
        self.is_hostile = False
        self.patrol_path = None
        self.x_vel = self.y_vel = 0.0
        self.target_vel = Actor.VELOCITY_TARGET
        self.drag_vel = 0.0
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
        self.update_geo()
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
        self.cached_x, self.cached_y = self.rect.x, self.rect.y
        self.cooldowns = {"get_hit": 0.0, "launch_projectile": 0.0, "resize": 0.0, "resize_delay": 0.0, "resize_effect": 0.0, "heal": 0.0, "attack": 0.0, "doublejump_effect_trail": 0.0}
        self.cached_cooldowns = self.cooldowns.copy()

    def save(self) -> dict:
        projectiles = []
        for proj in self.active_projectiles:
            projectiles.append(proj.save())
        return {self.name: {"hp": self.hp, "cached x y": (self.cached_x, self.cached_y), "cooldowns": self.cached_cooldowns, "size": self.size, "size_target": self.size, "can_wall_jump": self.can_wall_jump, "can_shoot": self.can_shoot, "can_resize": self.can_resize, "max_jumps": self.max_jumps, "projectiles": projectiles}}

    def load(self, ent) -> None:
        self.rect.x, self.rect.y = self.cached_x, self.cached_y = ent["cached x y"]
        self.cooldowns = self.cached_cooldowns = ent["cooldowns"]
        self.load_attribute(ent, "hp")
        self.cached_hp = self.hp
        self.load_attribute(ent, "size")
        self.load_attribute(ent, "size_target")
        self.load_attribute(ent, "can_wall_jump")
        self.load_attribute(ent, "can_shoot")
        self.load_attribute(ent, "can_resize")
        self.load_attribute(ent, "max_jumps")
        for proj in ent["projectiles"]:
            self.active_projectiles.append(Projectile(self.level, self.controller, self.rect.centerx + (self.rect.width * self.facing // 3), self.rect.centery, None, 0, self.attack_damage, self.difficulty, sprite=self.proj_sprite, name=(self.name + "'s projectile #" + str(len(self.active_projectiles) + 1))))
            self.active_projectiles[-1].load(list(proj.values())[0])
        self.update_sprite(1)
        self.update_geo()

    def set_difficulty(self, scale) -> None:
        self.difficulty = scale
        self.max_hp *= scale
        self.hp *= scale
        self.attack_damage *= scale
        for proj in self.active_projectiles:
            proj.set_difficulty(scale)
            proj.attack_damage = self.attack_damage

    def resize(self, target) -> None:
        if self.size_target != target:
            self.size_target = target
            self.attack_damage *= target
            self.cooldowns["resize"] = Actor.RESIZE_DELAY
            self.cooldowns["resize_delay"] = Actor.RESIZE_DELAY

    def grow(self) -> None:
        if self.can_resize and self.cooldowns["resize"] <= 0:
            self.resize(min(self.size_target * Actor.RESIZE_SCALE_LIMIT, Actor.RESIZE_SCALE_LIMIT))

    def shrink(self) -> None:
        if self.can_resize and self.cooldowns["resize"] <= 0:
            self.resize(max(self.size_target / Actor.RESIZE_SCALE_LIMIT, 1 / Actor.RESIZE_SCALE_LIMIT))

    def move(self, dx, dy) -> None:
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

    def cache(self) -> None:
        if self.cooldowns["get_hit"] <= 0 and self.state != MovementState.HIT and self.hp == self.max_hp and self.jump_count == 0 and self.y_vel == 0:
            self.cached_x, self.cached_y = self.rect.x, self.rect.y
            self.cached_hp = self.hp
            self.cached_size = self.size
            self.cached_size_target = self.size_target
            self.cached_cooldowns = self.cooldowns.copy()

    def revert(self) -> int:
        return 0

    def jump(self) -> None:
        if self.jump_count < self.max_jumps:
            self.y_vel = -Actor.VELOCITY_JUMP
            if self.jump_count > 0:
                self.cooldowns["doublejump_effect_trail"] = Actor.DOUBLEJUMP_EFFECT_TRAIL
                if self.level.visual_effects_manager.images.get("JUMPLINES") is not None:
                    rotation = (self.x_vel / self.y_vel) * 30
                    self.active_visual_effects["doublejump_effect_trail"] = VisualEffect(self, self.level.visual_effects_manager.images["JUMPLINES"], direction="BOTTOM" + str(self.direction), rotation=rotation, alpha=64, scale=(self.rect.width // 2, self.rect.height))
            self.jump_count += 1
            self.should_move_vert = True
            if self.is_wall_jumping:
                self.is_wall_jumping = False
                self.direction = self.direction.swap()
                self.facing = self.facing.swap()
                self.move(self.direction * self.rect.width // 4, 0)
        self.is_crouching = False

    def land(self) -> None:
        if self.y_vel > 20:
            self.hp -= 2 * self.y_vel
        self.y_vel = 0.0
        self.jump_count = 0
        self.should_move_vert = False
        self.is_wall_jumping = False

    def hit_head(self) -> None:
        self.y_vel *= -0.5

    def play_attack_audio(self, attack_type) -> None:
        if attack_type in self.audios:
            active_audio_channel = pygame.mixer.find_channel()
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[attack_type][random.randrange(len(self.audios[attack_type]))])
                if self == self.level.get_player():
                    active_audio_channel.set_volume(self.controller.master_volume["player"])
                else:
                    set_sound_source(self.rect, self.level.get_player().rect, self.controller.master_volume["non-player"], active_audio_channel)

    def shoot_at_target(self, target) -> None:
        if self.cooldowns["launch_projectile"] <= 0:
            self.is_attacking = True
            proj = Projectile(self.level, self.controller, self.rect.centerx, self.rect.centery, (target[0], self.rect.centery), Actor.MAX_SHOOT_DISTANCE, self.attack_damage, self.difficulty, sprite=self.proj_sprite, name=(self.name + "'s projectile #" + str(len(self.active_projectiles) + 1)))
            self.active_projectiles.append(proj)
            self.cooldowns["launch_projectile"] = Actor.LAUNCH_PROJECTILE_COOLDOWN
            self.play_attack_audio("ATTACK_RANGE")

    def get_hit(self, ent) -> None:
        self.cooldowns["get_hit"] = Actor.GET_HIT_COOLDOWN
        self.cooldowns["heal"] = Actor.HEAL_DELAY * self.difficulty
        self.hp -= ent.attack_damage

    def get_collisions(self) -> bool:
        collided = False

        if self == self.level.get_player():
            ents = self.level.get_entities_in_range((self.rect.x, self.rect.y))
        elif self.is_hostile:
            ents = [self.level.get_player()] + self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only=True)
        else:
            ents = self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only=True)
        for ent in ents:
            if self.rect.colliderect(ent.rect):
                if pygame.sprite.collide_mask(self, ent):
                    if isinstance(ent, Actor) or isinstance(ent, Objective):
                        overlap = self.mask.overlap_mask(ent.mask, (0, 0)).get_rect()
                    else:
                        overlap = self.rect.clip(ent.rect)
                    if isinstance(ent, Actor) and ent != self.level.get_player():
                        if ent.facing == (MovementDirection.RIGHT if self.rect.centerx - ent.rect.centerx >= 0 else MovementDirection.LEFT) and ent.is_attacking and self.cooldowns["get_hit"] <= 0:
                            self.get_hit(ent)
                    elif isinstance(ent, Hazard):
                        if ent.is_attacking and self.cooldowns["get_hit"] <= 0:
                            if overlap.width <= overlap.height and ((self.rect.x <= ent.rect.x and "L" in ent.hit_sides) or (self.rect.x >= ent.rect.x and "R" in ent.hit_sides)):
                                self.get_hit(ent)
                            if overlap.width >= overlap.height and ((self.rect.y <= ent.rect.y and "U" in ent.hit_sides) or (self.rect.y >= ent.rect.y and "D" in ent.hit_sides)):
                                self.get_hit(ent)
                    elif isinstance(ent, Objective) and self == self.level.get_player():
                        ent.get_hit(self)
                    if ent.collide(self):
                        self.collide(ent)
                        if overlap.width <= overlap.height and (self.x_vel == 0 or self.direction == (MovementDirection.RIGHT if self.x_vel >= 0 else MovementDirection.LEFT)):
                            if self.can_move_blocks and isinstance(ent, MovableBlock) and ent.should_move_horiz and self.direction == (MovementDirection.RIGHT if ent.rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT):
                                ent.push_x = self.x_vel * self.size
                            if (isinstance(ent, Actor) and ent.is_hostile) or not isinstance(ent, Actor):
                                if self.x_vel <= 0 and self.rect.centerx > ent.rect.centerx:
                                    self.rect.left = ent.rect.right - (self.rect.width // 5)
                                    self.x_vel = 0.0
                                elif self.x_vel >= 0 and self.rect.centerx <= ent.rect.centerx:
                                    self.rect.right = ent.rect.left + (self.rect.width // 5)
                                    self.x_vel = 0.0
                            collided = True

                        if overlap.width >= overlap.height:
                            if self.y_vel >= 0 and not ent.is_stacked and self.rect.bottom == overlap.bottom:
                                self.rect.bottom = ent.rect.top
                                self.land()
                            elif self.y_vel < 0 and self.rect.top == overlap.top:
                                self.rect.top = ent.rect.bottom
                                self.hit_head()

                        if collided and self.should_move_vert and not self.is_wall_jumping and self.direction == (MovementDirection.RIGHT if overlap.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT):
                            self.y_vel = min(self.y_vel, 0.0)
                            self.jump_count = 0
                            self.is_wall_jumping = True
                elif isinstance(ent, Objective) and self == self.level.get_player() and ent.sprite is None:
                    ent.get_hit(self)
            elif ent.rect.top <= self.rect.bottom <= ent.rect.bottom and self.rect.left + (self.rect.width // 4) <= ent.rect.right and self.rect.right - (self.rect.width // 4) >= ent.rect.left:
                if isinstance(ent, MovingBlock) or isinstance(ent, MovableBlock) :
                    ent.collide(self)
                if self.rect.centerx != ent.rect.centerx:
                    if math.degrees(math.atan(abs(self.rect.centery - ent.rect.centery) / abs(self.rect.centerx - ent.rect.centerx))) >= 45:
                        self.should_move_vert = False
                        if self.rect.bottom != ent.rect.top:
                            self.rect.bottom = ent.rect.top

        if self.x_vel != 0 and not collided and self.is_wall_jumping:
            self.is_wall_jumping = False
        return collided

    def die(self) -> None:
        return

    def update_state(self) -> None:
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
                    self.update_state()
                    return
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

    def update_sprite(self, fps) -> int:
        active_sprites = self.sprites[str(self.state) + "_" + str(self.facing)]
        active_index = math.floor((self.animation_count // (1000 // (fps * Actor.ANIMATION_DELAY))) % len(active_sprites))
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

    def update_geo(self) -> None:
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def loop(self, dtime) -> bool:
        self.animation_count += dtime

        if self.hp <= 0:
            self.die()
        super().loop(dtime)

        if self.can_heal and self.hp < self.max_hp and self.cooldowns["heal"] <= 0:
            self.hp = min(self.max_hp, self.hp + ((self.max_hp * dtime) / (50000 * self.difficulty)))

        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                if proj.hp <= 0:
                    self.active_projectiles.remove(proj)
                else:
                    proj.loop(dtime)

        if (self == self.level.get_player() or self.patrol_path is not None) and self.state != MovementState.WIND_UP and self.state != MovementState.WIND_DOWN:
            if self.push_x > 0:
                self.push_x = max(self.push_x - Actor.HORIZ_PUSH_DECAY_RATE * dtime, 0)
            elif self.push_x < 0:
                self.push_x = min(self.push_x + Actor.HORIZ_PUSH_DECAY_RATE * dtime, 0)
            self.push_y = 0

            self.should_move_vert = True
            collided = self.get_collisions()

            if self.cooldowns["resize_delay"] <= 0:
                if self.size != self.size_target:
                    if self.size > self.size_target:
                        self.rect.y += self.rect.height // 3
                    else:
                        self.rect.y -= self.rect.height // 2

                    scale_factor = self.size_target * 1.25
                    if self.size_target == 1:
                        if self.size < self.size_target:
                            scale_factor *= 1.5
                        else:
                            scale_factor /= 1.5

                    self.size = self.size_target

                    self.cooldowns["resize_effect"] = Actor.RESIZE_EFFECT
                    if self.level.visual_effects_manager.images.get("RESIZEBURST") is not None:
                        self.active_visual_effects["resize_effect"] = VisualEffect(self, self.level.visual_effects_manager.images["RESIZEBURST"], direction="", alpha=128, scale=(self.rect.width * scale_factor, self.rect.height * scale_factor), linked_to_source=True)

                if self.should_move_horiz:
                    scaled_target = dtime * self.target_vel
                    if abs(self.x_vel) < scaled_target:
                        self.x_vel = self.direction * min(scaled_target, (abs(self.x_vel) * self.drag_vel) + (scaled_target * float(1 - self.drag_vel)))
                else:
                    self.x_vel = 0.0

                if self.should_move_vert:
                    self.y_vel += dtime * Actor.GRAVITY * self.size / (1 + (3 if self.is_wall_jumping and self.y_vel > 0 else 0))

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

    def draw(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x_image = self.rect.x - offset_x
        adj_y_image = self.rect.y - offset_y
        #adj_x_audio = self.level.get_player().rect.x - self.rect.x
        #adj_y_audio = self.level.get_player().rect.y - self.rect.y
        window_width = win.get_width()
        window_height = win.get_height()
        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                proj.draw(win, offset_x, offset_y, master_volume, fps)
        if -self.rect.width < adj_x_image <= window_width and -self.rect.height < adj_y_image <= window_height:
            for effect in self.active_visual_effects.keys():
                self.active_visual_effects[effect].draw(win, offset_x, offset_y)
            self.update_sprite(fps)
            self.update_geo()
            win.blit(self.sprite, (adj_x_image, adj_y_image))

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
