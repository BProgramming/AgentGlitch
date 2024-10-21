import math
import pygame
from os.path import join, isfile
from Object import Object
from Helpers import handle_exception, MovementDirection


class Block(Object):
    def __init__(self, x, y, width, height, image_master, is_stacked, coord_x=0, coord_y=0, name="Block"):
        super().__init__(x, y, width, height, name)
        self.sprite.blit(load_image(join("Assets", "Terrain", "Terrain.png"), width, height, image_master, coord_x, coord_y), (0, 0))
        self.mask = pygame.mask.from_surface(self.sprite)
        self.is_stacked = is_stacked

    def save(self):
        if self.hp != 0:
            super().save()
        else:
            return None

class BreakableBlock(Block):
    def __init__(self, x, y, width, height, image_master, is_stacked, coord_x=0, coord_y=0, name="BreakableBlock"):
        super().__init__(x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)

    def get_hit(self, obj):
        self.hp = 0


class MovingBlock(Block):
    VELOCITY_TARGET = 0.5

    def __init__(self, x, y, level_bounds, width, height, image_master, is_stacked, speed=VELOCITY_TARGET, path=None, coord_x=0, coord_y=0, name="MovingBlock"):
        super().__init__(x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.speed = speed
        self.patrol_path = path
        self.patrol_path_index = 0
        if self.patrol_path is not None:
            min_dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[0])
            for i in range(len(self.patrol_path)):
                dist = math.dist((self.rect.x, self.rect.y), self.patrol_path[i])
                if dist < min_dist:
                    self.patrol_path_index = i
            self.direction = self.facing = MovementDirection(math.copysign(1, self.patrol_path[self.patrol_path_index][0] - self.rect.x))
        self.objects = []
        self.level_bounds = level_bounds
        self.x_vel = self.y_vel = 0
        self.should_move_horiz = self.should_move_vert = True

    def increment_patrol_index(self):
        if self.patrol_path_index < 0:
            self.patrol_path_index -= 1
        elif self.patrol_path_index >= 0:
            self.patrol_path_index += 1
        if self.patrol_path_index == len(self.patrol_path):
            self.patrol_path_index = -1
        elif self.patrol_path_index == -(len(self.patrol_path) + 1):
            self.patrol_path_index = 0

    def patrol(self):
        self.should_move_horiz = self.should_move_vert = False
        if self.patrol_path is not None:
            should_increment = False
            if self.patrol_path_index >= 0 and self.direction == MovementDirection.LEFT:
                if self.rect.x > self.patrol_path[self.patrol_path_index][0]:
                    self.x_vel = self.direction * self.speed
                    self.should_move_horiz = True
                else:
                    should_increment = True
            elif self.patrol_path_index < 0 and self.direction == MovementDirection.RIGHT:
                if self.rect.x < self.patrol_path[self.patrol_path_index][0]:
                    self.x_vel = self.direction * self.speed
                    self.should_move_horiz = True
                else:
                    should_increment = True
            else:
                self.direction = self.direction.swap()

            if self.rect.y > self.patrol_path[self.patrol_path_index][1]:
                self.y_vel = -self.speed
                self.should_move_vert = True
            elif self.rect.y < self.patrol_path[self.patrol_path_index][1]:
                self.y_vel = self.speed
                self.should_move_vert = True
            elif should_increment:
                self.increment_patrol_index()


    def collide(self, obj):
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y"):
            obj.push_y = self.y_vel
        return True

    def move(self, dx, dy):
        if dx != 0:
            if self.rect.left + dx < self.level_bounds[0][0]:
                self.rect.left = self.rect.width
                self.x_vel = 0
            elif self.rect.right + dx > self.level_bounds[1][0]:
                self.rect.right = self.level_bounds[1][0] - self.rect.width
                self.x_vel = 0
            else:
                self.rect.x += dx

        if dy != 0:
            if self.rect.top + dy < self.level_bounds[0][1]:
                self.y_vel *= -0.5
            elif self.rect.top + dy > self.level_bounds[1][1]:
                self.x_vel = 0
            else:
                target = self.rect.y + dy
                if self.y_vel > 0 and target > self.patrol_path[self.patrol_path_index][1]:
                    self.rect.y = self.patrol_path[self.patrol_path_index][1]
                elif self.y_vel < 0 and target < self.patrol_path[self.patrol_path_index][1]:
                    self.rect.y = self.patrol_path[self.patrol_path_index][1]
                else:
                    self.rect.y = target

    def loop(self, dtime):
        if self.should_move_horiz:
            self.x_vel *= dtime
        else:
            self.x_vel = 0

        if not self.should_move_vert:
            self.y_vel = 0

        if self.x_vel != 0 or self.y_vel != 0:
            self.move(self.x_vel, self.y_vel * dtime)


class MovableBlock(Block):
    GRAVITY = 0.04

    def __init__(self, x, y, level_bounds, width, height, image_master, is_stacked, coord_x=0, coord_y=0, name="MovableBlock"):
        super().__init__(x, y, width, height, image_master, is_stacked, coord_x=coord_x, coord_y=coord_y, name=name)
        self.start_x, self.start_y = x, y
        self.objects = []
        self.level_bounds = level_bounds
        self.x_vel = self.y_vel = self.push_x = self.push_y = 0
        self.should_move_horiz = self.should_move_vert = True

    def collide(self, obj):
        if hasattr(obj, "push_x"):
            obj.push_x = self.x_vel
        if hasattr(obj, "push_y"):
            obj.push_y = self.y_vel
        return True

    def get_collisions(self):
        self.should_move_horiz = self.should_move_vert = True
        for obj in self.objects:
            if isinstance(obj, Block) and obj != self and pygame.sprite.collide_rect(self, obj):
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
            if self.rect.left + dx < self.level_bounds[0][0]:
                self.rect.left = self.rect.width
                self.x_vel = 0
            elif self.rect.right + dx > self.level_bounds[1][0]:
                self.rect.right = self.level_bounds[1][0] - self.rect.width
                self.x_vel = 0
            else:
                self.rect.x += dx

        if dy != 0:
            if self.rect.top + dy < self.level_bounds[0][1]:
                self.y_vel *= -0.5
            elif self.rect.top + dy > self.level_bounds[1][1]:
                self.rect.x = self.start_x
                self.rect.y = self.start_y
                self.x_vel = 0
            else:
                self.rect.y += dy

    def loop(self, dtime, objects, grav=GRAVITY):
        self.objects = objects
        self.push_x = self.push_y = 0
        self.get_collisions()
        if not self.should_move_horiz:
            self.x_vel = 0

        if self.should_move_vert:
            self.y_vel += dtime * grav
        else:
            self.y_vel = 0

        if self.x_vel + self.push_x != 0 or self.y_vel + self.push_y != 0:
            self.move(self.x_vel + self.push_x, self.y_vel + (self.push_y * dtime))


class Hazard(Block):
    ATTACK_DAMAGE = 99

    def __init__(self, x, y, width, height, image_master, difficulty, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="Hazard"):
        super().__init__(x, (y + width - height), width, height, image_master, False, coord_x=coord_x, coord_y=coord_y, name=name)
        self.attack_damage = attack_damage * difficulty

    def set_difficulty(self, scale):
        self.difficulty = scale
        self.attack_damage *= scale


class MovingHazard(MovingBlock, Hazard):
    VELOCITY_TARGET = 0.5
    ATTACK_DAMAGE = 99

    def __init__(self, x, y, level_bounds, width, height, image_master, difficulty, is_stacked, speed=VELOCITY_TARGET, path=None, coord_x=0, coord_y=0, attack_damage=ATTACK_DAMAGE, name="MovingHazard"):
        MovingBlock.__init__(self, x, y, level_bounds, width, height, image_master, is_stacked, speed=speed, path=path, coord_x=coord_x, coord_y=coord_y, name=name)
        self.attack_damage = attack_damage * difficulty


def load_image(path, width, height, image_master, coord_x, coord_y):
    if isfile(path):
        if image_master.get(path) is None:
            image_master[path] = pygame.image.load(path).convert_alpha()
        surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        rect = pygame.Rect(coord_x, coord_y, width, height)
        surface.blit(image_master[path], (0, 0), rect)
        return pygame.transform.scale2x(surface)
    else:
        handle_exception(FileNotFoundError(path))
