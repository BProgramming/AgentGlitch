import pygame


class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name="Object"):
        super().__init__()
        self.sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.name = name + " (" + str(x) + ", " + str(y) + ")"
        self.max_hp = self.hp = 100
        self.is_stacked = False # this property is only used by blocks, but needed here for generic checks
        self.player = None

    def save(self):
        return {self.name: {"hp": self.hp}}

    def load(self, obj):
        self.load_attribute(obj, "hp")

    def load_attribute(self, obj, attribute):
        if obj.get(attribute):
            setattr(self, attribute, obj[attribute])

    def output(self, win, offset_x, offset_y, player, master_volume):
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
