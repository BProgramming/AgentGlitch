import pygame


class Object(pygame.sprite.Sprite):
    def __init__(self, level, x, y, width, height, name="Object"):
        super().__init__()
        self.level = level
        self.sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mask = pygame.mask.from_surface(self.sprite)
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.name = name + " (" + str(x) + ", " + str(y) + ")"
        self.max_hp = self.hp = 100
        self.is_stacked = False # this property is only used by blocks, but needed here for generic checks
        self.cooldowns = None

    def save(self):
        return {self.name: {"hp": self.hp}}

    def load(self, obj):
        self.load_attribute(obj, "hp")

    def load_attribute(self, obj, attribute):
        if obj.get(attribute):
            setattr(self, attribute, obj[attribute])

    def update_cooldowns(self, dtime):
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= (dtime / 1000)
            elif self.cooldowns[key] < 0:
                self.cooldowns[key] = 0

    def loop(self, fps, dtime):
        if self.cooldowns is not None:
            self.update_cooldowns(dtime)
        if self.hp <= 0:
            self.level.queue_purge(self)

    def output(self, win, offset_x, offset_y, master_volume):
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            win.blit(self.sprite, (adj_x, adj_y))

    def collide(self, obj):
        return True

    def get_hit(self, obj):
        return

    def set_difficulty(self, scale):
        return
