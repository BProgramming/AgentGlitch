import pygame


class Object(pygame.sprite.Sprite):
    GRAVITY = 0.02
    ANIMATION_DELAY = 0.3

    def __init__(self, level, controller, x, y, width, height, is_blocking=True, name="Object"):
        super().__init__()
        self.level = level
        self.controller = controller
        self.sprite = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mask = pygame.mask.from_surface(self.sprite)
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.is_blocking = is_blocking
        self.name = name + " (" + str(x) + ", " + str(y) + ")"
        self.max_hp = self.hp = 100
        self.is_stacked = False # this property is only used by blocks, but needed here for generic checks
        self.cooldowns = None
        self.active_visual_effects = {}

    def save(self) -> dict:
        return {self.name: {"hp": self.hp}}

    def load(self, obj) -> None:
        self.load_attribute(obj, "hp")

    def load_attribute(self, obj, attribute) -> None:
        if obj.get(attribute):
            setattr(self, attribute, obj[attribute])

    def update_cooldowns(self, dtime) -> None:
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= (dtime / 1000)
            elif self.cooldowns[key] < 0:
                self.cooldowns[key] = 0.0

    def __cleanup_vfx__(self):
        for effect in list(self.active_visual_effects.keys()):
            if self.cooldowns[effect] <= 0:
                del self.active_visual_effects[effect]

    def loop(self, dtime) -> None:
        if self.cooldowns is not None:
            self.update_cooldowns(dtime)
        if self.active_visual_effects:
            self.__cleanup_vfx__()
        if self.hp <= 0:
            self.level.queue_purge(self)

    def draw(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            for effect in self.active_visual_effects.keys():
                self.active_visual_effects[effect].draw(win, offset_x, offset_y)
            win.blit(self.sprite, (adj_x, adj_y))

    def collide(self, obj) -> bool:
        return self.is_blocking

    def get_hit(self, obj) -> None:
        return

    def set_difficulty(self, scale) -> None:
        return
