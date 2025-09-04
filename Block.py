import math
import random
import pygame
from os.path import join, isfile
from Object import Object
from Helpers import handle_exception, MovementDirection, load_sprite_sheets, set_sound_source


class Block(Object):
    def __init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=0, coord_y=0, is_blocking=True, name="Block"):
        super().__init__(level, controller, x, y, width, height, is_blocking=is_blocking, name=name)
        self.sprite = self.load_image(join("Assets", "Terrain", "Terrain.png"), width, height, image_master, coord_x, coord_y, grayscale=self.level.grayscale)
        self.mask = pygame.mask.from_surface(self.sprite)
        self.is_stacked = is_stacked
        self.audios = audios

    def save(self) -> dict | None:
        if self.hp != 0:
            return super().save()
        else:
            return None

    def play_sound(self, name) -> None:
        if self.audios.get(name.upper()) is not None:
            active_audio_channel = pygame.mixer.find_channel()
            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[name.upper()][random.randrange(len(self.audios[name.upper()]))])
                set_sound_source(self.rect, self.level.get_player().rect, self.controller.master_volume["non-player"], active_audio_channel)

    @staticmethod
    def load_image(path, width, height, image_master, coord_x, coord_y, grayscale=False) -> pygame.Surface | None:
        if isfile(path):
            if image_master.get(path) is None:
                image_master[path] = pygame.image.load(path).convert_alpha()
            surface = pygame.Surface((width // 2, height // 2), pygame.SRCALPHA)
            rect = pygame.Rect(coord_x, coord_y, width // 2, height // 2)
            surface.blit(image_master[path], (0, 0), rect)
            if grayscale:
                surface = pygame.transform.grayscale(surface)
            return pygame.transform.scale2x(surface)
        else:
            handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
            return None


class BreakableBlock(Block):
    GET_HIT_COOLDOWN = 1

    def __init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=0, coord_y=0, coord_x2=0, coord_y2=0, name="BreakableBlock"):
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.sprite_damaged = self.load_image(join("Assets", "Terrain", "Terrain.png"), width, height, image_master, coord_x2, coord_y2, grayscale=self.level.grayscale)
        self.cooldowns = {"get_hit": 0}

    def get_hit(self, obj) -> None:
        if self.cooldowns["get_hit"] <= 0:
            if self.hp == self.max_hp:
                self.hp = self.max_hp // 2
                self.sprite = self.sprite_damaged
                self.mask = pygame.mask.from_surface(self.sprite)
                self.cooldowns["get_hit"] += BreakableBlock.GET_HIT_COOLDOWN
            else:
                self.hp = 0
            self.play_sound("smash_box")


class MovingBlock(Block):
    VELOCITY_TARGET = 0.5
    PATH_STOP_TIME = 0.5

    def __init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, hold_for_collision=False, speed=VELOCITY_TARGET, path=None, coord_x=0, coord_y=0, is_blocking=True, name="MovingBlock"):
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=coord_x, coord_y=coord_y, is_blocking=is_blocking, name=name)
        self.speed = speed
        self.hold = hold_for_collision
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

    def increment_patrol_index(self) -> None:
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index >= len(self.patrol_path) - 1:
            self.patrol_path_index = -1
        elif self.patrol_path_index <= -len(self.patrol_path):
            self.patrol_path_index = 0

    def patrol(self, dtime) -> None:
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
                    self.cooldowns["wait"] = MovingBlock.PATH_STOP_TIME
                self.increment_patrol_index()

    def collide(self, obj) -> bool:
        if self.hold and obj == self.level.get_player():
            self.hold = False
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y"):
            obj.push_y = self.y_vel
        return self.is_blocking

    def move(self, dx, dy) -> None:
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

    def loop(self, fps, dtime) -> None:
        super().loop(fps, dtime)

        if not self.hold:
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

    def __init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, speed=VELOCITY_TARGET, direction=-1, is_locked=False, coord_x=0, coord_y=0, name="Door"):
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, speed=speed, coord_x=coord_x, coord_y=coord_y, name=name)
        self.patrol_path_open = [(x, y + (height * direction))]
        self.patrol_path_closed = [(x, y)]
        self.is_locked = is_locked
        self.is_open = False
        self.direction = self.facing = MovementDirection.LEFT

    def open(self) -> None:
        if not self.is_locked:
            self.patrol_path = self.patrol_path_open
            self.is_open = True
            self.play_sound("door")
        else:
            self.play_sound("door_locked")

    def close(self) -> None:
        self.patrol_path = self.patrol_path_closed
        self.is_open = False
        self.play_sound("door")

    def toggle_open(self) -> None:
        if self.is_open:
            self.close()
        elif not self.is_locked:
            self.open()

    def unlock(self) -> None:
        self.is_locked = False

    def lock(self) -> None:
        self.is_locked = True

    def toggle_lock(self) -> None:
        self.is_locked = not self.is_locked

    def collide(self, obj) -> bool:
        if hasattr(obj, "can_open_doors") and obj.can_open_doors and obj.rect.bottom > self.rect.top:
            self.open()
        return True

    def loop(self, fps, dtime) -> None:
        if not self.is_open and self.rect.y == self.patrol_path_closed[0][1]:
            return
        else:
            if math.dist((self.level.get_player().rect.centerx, self.level.get_player().rect.centery), (self.rect.centerx, self.rect.centery)) > math.sqrt(self.rect.height**2 + (1.5 * self.rect.width)**2):
                self.close()
            super().loop(fps, dtime)

class MovableBlock(Block):
    def __init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=0, coord_y=0, name="MovableBlock"):
        super().__init__(level, controller, x, y, width, height, image_master, audios, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.start_x, self.start_y = x, y
        self.x_vel = self.y_vel = self.push_x = self.push_y = 0.0
        self.should_move_horiz = self.should_move_vert = True

    def collide(self, obj) -> bool:
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y") and self.rect.top >= obj.rect.bottom:
            obj.push_y = self.y_vel
        return True

    def get_collisions(self) -> None:
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

    def move(self, dx, dy) -> None:
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

    def loop(self, fps, dtime) -> None:
        super().loop(fps, dtime)

        self.push_x *= 0.9
        if abs(self.push_x) < 0.01:
            self.push_x = 0
        self.push_y = 0
        self.get_collisions()
        if not self.should_move_horiz:
            self.x_vel = 0.0

        if self.should_move_vert:
            self.y_vel += dtime * MovableBlock.GRAVITY
        else:
            self.y_vel = 0.0

        if self.x_vel + self.push_x != 0 or self.y_vel + self.push_y != 0:
            self.move(self.x_vel + self.push_x, self.y_vel + (self.push_y * dtime))


class Hazard(Block):
    ATTACK_DAMAGE = 99
    ANIMATION_DELAY = 0.3

    def __init__(self, level, controller, x, y, width, height, image_master, sprite_master, audios, difficulty, hit_sides="UDLR", sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="Hazard"):
        super().__init__(level, controller, x, (y + width - height), width, height, image_master, audios, False, coord_x=coord_x, coord_y=coord_y, name=name)
        self.difficulty = difficulty
        self.attack_damage = attack_damage * difficulty
        self.is_attacking = True
        self.hit_sides = hit_sides.upper()
        if sprite is not None:
            self.sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, grayscale=self.level.grayscale)["ANIMATE"]
        else:
            self.sprites = [self.sprite]
        self.animation_count = 0
        self.sprite = None
        self.update_sprite(1)
        self.update_geo()

    def set_difficulty(self, scale) -> None:
        self.difficulty = scale
        self.attack_damage *= scale

    def update_sprite(self, fps) -> int:
        active_index = math.floor((self.animation_count // (1000 // (fps * Hazard.ANIMATION_DELAY))) % len(self.sprites))
        if active_index >= len(self.sprites):
            active_index = 0
            self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def update_geo(self) -> None:
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def loop(self, fps, dtime) -> None:
        self.animation_count += dtime
        super().loop(fps, dtime)

    def output(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            self.update_sprite(fps)
            self.update_geo()
            win.blit(self.sprite, (adj_x, adj_y))

class MovingHazard(MovingBlock, Hazard):
    VELOCITY_TARGET = 0.5
    ATTACK_DAMAGE = 99

    def __init__(self, level, controller, x, y, width, height, image_master, sprite_master, audios, difficulty, is_stacked, speed=VELOCITY_TARGET, path=None, hit_sides="UDLR", sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="MovingHazard"):
        MovingBlock.__init__(self, level, controller, x, y, width, height, image_master, audios, is_stacked, hold_for_collision=False, speed=speed, path=path, coord_x=coord_x, coord_y=coord_y, name=name)
        self.attack_damage = attack_damage * difficulty
        self.is_attacking = True
        self.hit_sides = hit_sides.upper()
        if sprite is not None:
            self.sprites = load_sprite_sheets("Sprites", sprite, sprite_master, direction=False, grayscale=self.level.grayscale)
        else:
            self.sprites = {"ANIMATE": self.sprite}
        self.animation_count = 0
        self.sprite = None
        self.update_sprite(1)

    def loop(self, fps, dtime) -> None:
        MovingBlock.loop(self, fps, dtime)


class FallingHazard(Hazard):
    ATTACK_DAMAGE = 99
    RESET_DELAY = 1
    ANIMATION_DELAY = 0.3

    def __init__(self, level, controller, x, y, width, height, image_master, sprite_master, audios, difficulty, hit_sides="D", drop_x=0, drop_y=0, fire_once=True, sprite=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="FallingHazard"):
        super().__init__(level, controller, x, y, width, height, image_master, sprite_master, audios, difficulty, hit_sides=hit_sides, sprite=sprite, coord_x=coord_x, coord_y=coord_y, attack_damage=attack_damage, name=name)
        self.start_x = self.rect.x
        self.start_y = self.rect.y
        self.drop_x = drop_x
        self.drop_y = drop_y
        self.fire_once = fire_once
        self.has_fired = False
        self.should_fire = False
        self.y_vel = 0
        self.cooldowns = {"reset_time": 0}

    def update_sprite(self, fps) -> int:
        if hasattr(self, "has_fired") and self.has_fired:
            if self.y_vel != 0:
                active_index = -2
            else:
                active_index = -1
        else:
            active_index = math.floor((self.animation_count // (1000 // (fps * FallingHazard.ANIMATION_DELAY))) % (len(self.sprites) - 2))
            if active_index >= len(self.sprites) - 2:
                active_index = 0
                self.animation_count = 0
        self.sprite = self.sprites[active_index]
        return active_index

    def loop(self, fps, dtime) -> bool:
        if not self.has_fired:
            if abs(self.level.get_player().rect.x - self.rect.x) <= self.drop_x and self.level.get_player().rect.top >= self.rect.bottom and abs(self.level.get_player().rect.y - self.rect.y) <= self.drop_y:
                self.should_fire = True

            if self.should_fire:
                self.has_fired = True
                self.play_sound("block_drop")
            else:
                self.animation_count += dtime
                return False

        should_reset = bool(self.cooldowns["reset_time"] > 0)
        super().loop(fps, dtime)
        should_reset = should_reset and bool(self.cooldowns["reset_time"] <= 0)

        if should_reset:
            self.should_fire = False
            if self.fire_once:
                self.hp = 0
                return True
            else:
                self.rect.x = self.start_x
                self.rect.y = self.start_y
                self.has_fired = False
                self.y_vel = 0

        collided = False
        if self.has_fired and self.cooldowns["reset_time"] <= 0:
            self.y_vel += dtime * FallingHazard.GRAVITY

            objs = self.level.get_objects_in_range((self.rect.x, self.rect.y + self.y_vel), blocks_only=True)
            # this part lets falling hazards hit each other and cause those to fall too
            x = int(self.rect.x / self.level.block_size)
            if self.level.falling_hazards.get(x) is not None:
                objs += self.level.falling_hazards[x]

            for obj in objs:
                if obj != self and pygame.sprite.collide_rect(self, obj) and pygame.sprite.collide_mask(self, obj):
                    self.rect.bottom = obj.rect.top
                    self.y_vel = 0
                    collided = True
                    self.play_sound("block_land")
                    if isinstance(obj, FallingHazard):
                        obj.should_fire = True
                    else:
                        self.cooldowns["reset_time"] += FallingHazard.RESET_DELAY
                    break

            self.rect.y += self.y_vel
            if self.rect.y > self.level.level_bounds[1][1]:
                self.cooldowns["reset_time"] += FallingHazard.RESET_DELAY
                collided = True

        return collided
