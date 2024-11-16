import math
import pygame
from os.path import join, isfile
from Object import Object
from Helpers import handle_exception, MovementDirection, load_sprite_sheets


class Block(Object):
    def __init__(self, level, x, y, width, height, image_master, is_stacked, coord_x=0, coord_y=0, name="Block"):
        super().__init__(level, x, y, width, height, name)
        self.sprite.blit(load_image(join("Assets", "Terrain", "Terrain.png"), width, height, image_master, coord_x, coord_y, grayscale=self.level.grayscale), (0, 0))
        self.mask = pygame.mask.from_surface(self.sprite)
        self.is_stacked = is_stacked

    def save(self):
        if self.hp != 0:
            super().save()
        else:
            return None

class BreakableBlock(Block):
    GET_HIT_COOLDOWN = 1

    def __init__(self, level, x, y, width, height, image_master, is_stacked, coord_x=0, coord_y=0, coord_x2=0, coord_y2=0, name="BreakableBlock"):
        super().__init__(level, x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.sprite_damaged = load_image(join("Assets", "Terrain", "Terrain.png"), width, height, image_master, coord_x2, coord_y2, grayscale=self.level.grayscale)
        self.cooldowns = {"get_hit": 0}

    def get_hit(self, obj, cd=GET_HIT_COOLDOWN):
        if self.cooldowns["get_hit"] <= 0:
            if self.hp == self.max_hp:
                self.hp = self.max_hp // 2
                self.sprite.blit(self.sprite_damaged, (0, 0))
                self.mask = pygame.mask.from_surface(self.sprite)
                self.cooldowns["get_hit"] += cd
            else:
                self.hp = 0


class MovingBlock(Block):
    VELOCITY_TARGET = 0.5
    PATH_STOP_TIME = 0.5

    def __init__(self, level, x, y, width, height, image_master, is_stacked, speed=VELOCITY_TARGET, path=None, coord_x=0, coord_y=0, name="MovingBlock"):
        super().__init__(level, x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.speed = speed
        self.patrol_path = path
        self.patrol_path_index = 0
        if self.patrol_path is not None:
            min_dist = math.dist((self.rect.x, self.rect.y), (self.patrol_path[0][0], self.patrol_path[0][1]))
            for i in range(len(self.patrol_path)):
                dist = math.dist((self.rect.x, self.rect.y), (self.patrol_path[i][0], self.patrol_path[i][1]))
                if dist < min_dist:
                    self.patrol_path_index = i
            self.direction = self.facing = (MovementDirection.RIGHT if self.patrol_path[self.patrol_path_index][0] - self.rect.x > 0 else MovementDirection.LEFT)
        self.x_vel = self.y_vel = 0.0
        self.should_move_horiz = self.should_move_vert = True
        self.cooldowns = {"wait": 0.0}

    def increment_patrol_index(self):
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index >= len(self.patrol_path) - 1:
            self.patrol_path_index = -1
        elif self.patrol_path_index <= -len(self.patrol_path):
            self.patrol_path_index = 0

    def patrol(self, dtime, path_stop_time=PATH_STOP_TIME):
        self.should_move_horiz = self.should_move_vert = False
        if self.patrol_path is not None and self.cooldowns["wait"] <= 0:
            target_x = self.patrol_path[self.patrol_path_index][0] - self.rect.x
            if target_x != 0:
                self.direction = (MovementDirection.RIGHT if target_x >= 0 else MovementDirection.LEFT)
                self.x_vel = min(abs(target_x / dtime), abs(self.speed)) * self.direction
                self.should_move_horiz = True

            target_y = self.patrol_path[self.patrol_path_index][1] - self.rect.y
            if target_y != 0:
                self.y_vel = min(abs(target_y / dtime), abs(self.speed)) * (1 if target_y >= 0 else -1)
                self.should_move_vert = True

            if not self.should_move_horiz and not self.should_move_vert:
                if len(self.patrol_path[self.patrol_path_index]) > 2 and self.patrol_path[self.patrol_path_index][2]:
                    self.cooldowns["wait"] = path_stop_time
                self.increment_patrol_index()

    def collide(self, obj):
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y"):
            obj.push_y = self.y_vel
        return True

    def move(self, dx, dy):
        if dx != 0:
            if self.rect.left + dx < self.level.level_bounds[0][0]:
                self.rect.left = self.rect.width
                self.x_vel = 0.0
            elif self.rect.right + dx > self.level.level_bounds[1][0]:
                self.rect.right = self.level.level_bounds[1][0] - self.rect.width
                self.x_vel = 0.0
            else:
                self.rect.x += dx

        if dy != 0:
            if self.rect.top + dy < self.level.level_bounds[0][1]:
                self.y_vel *= -0.5
            elif self.rect.top + dy > self.level.level_bounds[1][1]:
                self.x_vel = 0.0
            else:
                target = self.rect.y + dy
                if self.y_vel > 0 and target > self.patrol_path[self.patrol_path_index][1]:
                    self.rect.y = self.patrol_path[self.patrol_path_index][1]
                elif self.y_vel < 0 and target < self.patrol_path[self.patrol_path_index][1]:
                    self.rect.y = self.patrol_path[self.patrol_path_index][1]
                else:
                    self.rect.y = target

    def loop(self, fps, dtime):
        super().loop(fps, dtime)

        if self.should_move_horiz:
            self.x_vel *= dtime
        else:
            self.x_vel = 0.0

        if not self.should_move_vert:
            self.y_vel = 0.0

        if self.x_vel != 0 or self.y_vel != 0:
            if self.level.get_player().is_slow_time:
                self.x_vel /= 2
                self.y_vel /= 2

            self.move(self.x_vel, self.y_vel * dtime)


class Door(MovingBlock):
    VELOCITY_TARGET = 0.5

    def __init__(self, level, x, y, width, height, image_master, is_stacked, speed=VELOCITY_TARGET, direction=-1, is_locked=False, coord_x=0, coord_y=0, name="Door"):
        super().__init__(level, x, y, width, height, image_master, is_stacked, speed=speed, coord_x=coord_x, coord_y=coord_y, name=name)
        self.patrol_path_open = [(x, y + (height * direction))]
        self.patrol_path_closed = [(x, y)]
        self.is_locked = is_locked
        self.is_open = False
        self.direction = self.facing = MovementDirection.LEFT

    def open(self):
        if not self.is_locked:
            self.patrol_path = self.patrol_path_open
            self.is_open = True

    def close(self):
        self.patrol_path = self.patrol_path_closed
        self.is_open = False

    def toggle_open(self):
        if self.is_open:
            self.close()
        elif not self.is_locked:
            self.open()

    def unlock(self):
        self.is_locked = False

    def lock(self):
        self.is_locked = True

    def toggle_lock(self):
        self.is_locked = not self.is_locked

    def collide(self, obj):
        if hasattr(obj, "can_open_doors") and obj.can_open_doors and obj.rect.bottom > self.rect.top:
            self.open()
        return True

    def loop(self, fps, dtime):
        if not self.is_open and self.rect.y == self.patrol_path_closed[0][1]:
            return
        else:
            if math.dist((self.level.get_player().rect.centerx, self.level.get_player().rect.centery), (self.rect.centerx, self.rect.centery)) > math.sqrt(self.rect.height**2 + (1.5 * self.rect.width)**2):
                self.close()
            super().loop(fps, dtime)

class MovableBlock(Block):
    GRAVITY = 0.04

    def __init__(self, level, x, y, width, height, image_master, is_stacked, coord_x=0, coord_y=0, name="MovableBlock"):
        super().__init__(level, x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.start_x, self.start_y = x, y
        self.x_vel = self.y_vel = self.push_x = self.push_y = 0.0
        self.should_move_horiz = self.should_move_vert = True

    def collide(self, obj):
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y") and self.rect.top >= obj.rect.bottom:
            obj.push_y = self.y_vel
        return True

    def get_collisions(self):
        self.should_move_horiz = self.should_move_vert = True
        for obj in self.level.get_objects_in_range((self.rect.x, self.rect.y), blocks_only=True):
            if obj != self and pygame.sprite.collide_rect(self, obj):
                if pygame.sprite.collide_mask(self, obj) and obj.collide(self):
                    self.collide(obj)

                    overlap = self.rect.clip(obj.rect)
                    if overlap.width < overlap.height:
                        if self.x_vel <= 0 and self.rect.centerx > obj.rect.centerx:
                            self.rect.left = obj.rect.right + self.rect.width
                            self.should_move_horiz = False
                        elif self.x_vel >= 0 and self.rect.centerx < obj.rect.centerx:
                            self.rect.right = obj.rect.left - self.rect.width
                            self.should_move_horiz = False
                    if overlap.width >= overlap.height:
                        if self.y_vel >= 0 and self.rect.bottom == overlap.bottom:
                            if self.y_vel > 1:
                                self.rect.bottom = obj.rect.top
                            self.should_move_vert = False
                        elif self.y_vel < 0 and self.rect.top == overlap.top:
                            self.rect.top = obj.rect.bottom
                            self.y_vel *= -0.5
            if not self.should_move_horiz and not self.should_move_vert:
                break

    def move(self, dx, dy):
        if dx != 0:
            if self.rect.left + dx < self.level.level_bounds[0][0]:
                self.rect.left = self.rect.width
                self.x_vel = 0.0
            elif self.rect.right + dx > self.level.level_bounds[1][0]:
                self.rect.right = self.level.level_bounds[1][0] - self.rect.width
                self.x_vel = 0.0
            else:
                self.rect.x += dx

        if dy != 0:
            if self.rect.top + dy < self.level.level_bounds[0][1]:
                self.y_vel *= -0.5
            elif self.rect.top + dy > self.level.level_bounds[1][1]:
                self.rect.x = self.start_x
                self.rect.y = self.start_y
                self.x_vel = 0.0
            else:
                self.rect.y += dy

    def loop(self, fps, dtime, grav=GRAVITY):
        super().loop(fps, dtime)

        self.push_x *= 0.9
        if abs(self.push_x) < 0.01:
            self.push_x = 0
        self.push_y = 0
        self.get_collisions()
        if not self.should_move_horiz:
            self.x_vel = 0.0

        if self.should_move_vert:
            self.y_vel += dtime * grav
        else:
            self.y_vel = 0.0

        if self.x_vel + self.push_x != 0 or self.y_vel + self.push_y != 0:
            self.move(self.x_vel + self.push_x, self.y_vel + (self.push_y * dtime))


class Hazard(Block):
    ATTACK_DAMAGE = 99
    ANIMATION_DELAY = 0.3

    def __init__(self, level, x, y, width, height, image_master, sprite_master, difficulty, sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="Hazard"):
        super().__init__(level, x, (y + width - height), width, height, image_master, False, coord_x=coord_x, coord_y=coord_y, name=name)
        self.attack_damage = attack_damage * difficulty
        self.is_attacking = True
        if sprite is not None:
            self.sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, grayscale=self.level.grayscale)["ANIMATE"]
        else:
            self.sprites = [self.sprite]
        self.rects = []
        self.masks = []
        for s in self.sprites:
            self.rects.append(self.sprite.get_rect(topleft=(self.rect.x, self.rect.y)))
            self.masks.append(pygame.mask.from_surface(s))
        self.animation_count = 0
        self.sprite = None
        self.update_sprite(1)

    def set_difficulty(self, scale):
        self.difficulty = scale
        self.attack_damage *= scale

    def update_sprite(self, fps, delay=ANIMATION_DELAY):
        active_index = math.floor((self.animation_count // (1000 // (fps * delay))) % len(self.sprites))
        if active_index >= len(self.sprites):
            active_index = 0
            self.animation_count = 0
        self.sprite = self.sprites[active_index]
        self.rect = self.rects[active_index]
        self.mask = self.masks[active_index]

    def loop(self, fps, dtime):
        self.animation_count += dtime
        super().loop(fps, dtime)

    def output(self, win, offset_x, offset_y, master_volume, fps):
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            self.update_sprite(fps)
            win.blit(self.sprite, (adj_x, adj_y))

class MovingHazard(MovingBlock, Hazard):
    VELOCITY_TARGET = 0.5
    ATTACK_DAMAGE = 99

    def __init__(self, level, x, y, width, height, image_master, sprite_master, difficulty, is_stacked, speed=VELOCITY_TARGET, path=None, sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="MovingHazard"):
        MovingBlock.__init__(self, level, x, y, width, height, image_master, is_stacked, speed=speed, path=path, coord_x=coord_x, coord_y=coord_y, name=name)
        self.attack_damage = attack_damage * difficulty
        self.is_attacking = True
        if sprite is not None:
            self.sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, grayscale=self.level.grayscale)
        else:
            self.sprites = {"ANIMATE": self.sprite}
        self.animation_count = 0
        self.sprite = None
        self.update_sprite(1)

    def loop(self, fps, dtime):
        MovingBlock.loop(fps, dtime)


class FallingHazard(Hazard):
    GRAVITY = 0.02
    ATTACK_DAMAGE = 99
    RESET_DELAY = 1

    def __init__(self, level, x, y, width, height, image_master, sprite_master, difficulty, drop_x=0, drop_y=0, fire_once=True, sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="FallingHazard"):
        super().__init__(level, x, y, width, height, image_master, sprite_master, difficulty, sprite=sprite, coord_x=coord_x, coord_y=coord_y, attack_damage=attack_damage, name=name)
        self.start_x = self.rect.x
        self.start_y = self.rect.y
        self.drop_x = drop_x
        self.drop_y = drop_y
        self.fire_once = fire_once
        self.has_fired = False
        self.y_vel = 0
        self.cooldowns = {"reset_time": 0}

    def loop(self, fps, dtime, grav=GRAVITY, cd=RESET_DELAY):
        if not self.has_fired:
            return False

        should_reset = bool(self.cooldowns["reset_time"] > 0)
        super().loop(fps, dtime)
        should_reset = should_reset and bool(self.cooldowns["reset_time"] <= 0)

        if should_reset:
            if self.fire_once:
                self.hp = 0
                return True
            else:
                self.rect.x = self.start_x
                self.rect.y = self.start_y
                self.has_fired = False
                self.y_vel = 0

        if not self.has_fired and abs(self.level.get_player().rect.x - self.rect.x) <= self.drop_x and self.level.get_player().rect.top >= self.rect.bottom and abs(self.level.get_player().rect.y - self.rect.y) <= self.drop_y:
            self.has_fired = True

        collided = False
        if self.has_fired and self.cooldowns["reset_time"] <= 0:
            self.y_vel += dtime * grav
            for obj in self.level.get_objects_in_range((self.rect.x, self.rect.y + self.y_vel), blocks_only=True):
                if self.rect.centery <= obj.rect.centery and pygame.sprite.collide_rect(self, obj) and pygame.sprite.collide_mask(self, obj):
                    self.rect.bottom = obj.rect.top
                    self.y_vel = 0
                    self.cooldowns["reset_time"] += cd
                    collided = True
                    break

            self.rect.y += self.y_vel
            if self.rect.y > self.level.level_bounds[1][1]:
                self.cooldowns["reset_time"] += cd
                collided = True

        return collided


def load_image(path, width, height, image_master, coord_x, coord_y, grayscale=False):
    if isfile(path):
        if image_master.get(path) is None:
            image_master[path] = pygame.image.load(path).convert_alpha()
        surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        rect = pygame.Rect(coord_x, coord_y, width, height)
        surface.blit(image_master[path], (0, 0), rect)
        if grayscale:
            surface = pygame.transform.grayscale(surface)
        return pygame.transform.scale2x(surface)
    else:
        handle_exception(FileNotFoundError(path))
