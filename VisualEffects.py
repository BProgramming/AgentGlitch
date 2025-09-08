import pygame
from Helpers import load_images, display_text

class VisualEffectsManager:
    def __init__(self, controller) -> None:
        display_text("Loading cool effects...", controller, min_pause_time=0, should_sleep=False)
        self.images = load_images("VisualEffects", None)
        for key in self.images.keys():
            self.images[key] = {"LEFT": pygame.transform.flip(self.images[key], True, False), "RIGHT": self.images[key]}


class VisualEffect:
    def __init__(self, source, images: dict[str, pygame.Surface], direction: str="", rotation: float=0, alpha: int=255, offset: tuple[float, float]=(0.0, 0.0), scale: tuple[float, float]=(1.0, 1.0), linked_to_source: bool=False) -> None:
        self.image = images["LEFT" if "LEFT" in direction else "RIGHT"]
        if scale != (1, 1):
            self.image = pygame.transform.smoothscale(self.image, scale)
        if alpha != 255:
            self.image.set_alpha(alpha)
        if rotation != 0:
            self.image = pygame.transform.rotate(self.image, rotation)
        self.rect = self.image.get_rect()

        self.is_linked_to_source = linked_to_source
        self.source = source
        self.offset = offset
        self.direction = direction

        if not self.is_linked_to_source:
            self.__align__()

    def __align__(self):
        if "LEFT" in self.direction:
            self.rect.left = self.source.rect.left + self.offset[0]
        elif "RIGHT" in self.direction:
            self.rect.right = self.source.rect.right - self.offset[0]
        else:
            self.rect.centerx = self.source.rect.centerx
        if "BOTTOM" in self.direction:
            self.rect.bottom = self.source.rect.bottom - self.offset[1]
        elif "TOP" in self.direction:
            self.rect.top = self.source.rect.top + self.offset[1]
        else:
            self.rect.centery = self.source.rect.centery

    def draw(self, win, offset_x: float, offset_y: float) -> None:
        if self.is_linked_to_source:
            self.__align__()
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        win.blit(self.image, (adj_x, adj_y))
