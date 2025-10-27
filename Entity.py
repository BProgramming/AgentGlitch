import pygame


class Entity(pygame.sprite.Sprite):
    GRAVITY = 0.02

    def __init__(self, level, controller, x: float, y: float, width: float, height: float, is_blocking: bool=True, name: str="Entity"):
        super().__init__()
        self.attack_damage = None
        self.level = level
        self.controller = controller
        self.sprite: pygame.Surface | None = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mask: pygame.Mask | None = pygame.mask.from_surface(self.sprite)
        self.rect: pygame.Rect | None = pygame.Rect(x, y, width, height)
        self.width: float = width
        self.height: float = height
        self.is_blocking: bool = is_blocking
        self.name: str = f'{name} ({x}, {y})'
        self.max_hp: float = 100
        self.hp: float = 100
        self.is_stacked: bool = False # this property is only used by blocks, but needed here for generic checks
        self.cooldowns: dict | None = None

    def save(self) -> dict:
        return {self.name: {"hp": self.hp}}

    def load(self, data: dict) -> None:
        self.load_attribute(data, "hp")

    def load_attribute(self, data: dict, attribute: str) -> None:
        if data.get(attribute):
            setattr(self, attribute, data[attribute])

    def update_cooldowns(self, dtime: float) -> None:
        for key in self.cooldowns:
            if self.cooldowns[key] > 0:
                self.cooldowns[key] -= (dtime / 1000)
            elif self.cooldowns[key] < 0:
                self.cooldowns[key] = 0.0

    def loop(self, dtime: float) -> None:
        if self.cooldowns is not None:
            self.update_cooldowns(dtime)
        if self.hp <= 0:
            self.level.queue_purge(self)

    def draw(self, win: pygame.Surface, offset_x: float, offset_y: float, master_volume: dict) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        if -self.rect.width < adj_x <= win.get_width() and -self.rect.height < adj_y <= win.get_height():
            win.blit(self.sprite, (adj_x, adj_y))

    def collide(self, ent: 'Entity') -> bool:
        return self.is_blocking

    def get_hit(self, ent: 'Entity') -> None:
        return

    def set_difficulty(self, scale: float) -> None:
        return
