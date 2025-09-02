import pygame
from Helpers import load_images, display_text


class VisualEffectsManager():
    def __init__(self, controller) -> None:
        display_text("Loading cool effects...", controller, min_pause_time=0, should_sleep=False)
        self.images = load_images("VisualEffects", None)
        for key in self.images.keys():
            self.images[key] = {"LEFT": pygame.transform.flip(self.images[key], True, False), "RIGHT": self.images[key]}


class VisualEffect():
    def __init__(self, source_rect, images, direction, offset=(0, 0), scale=(1, 1)) -> None:
        self.image = images[direction]
        if scale != (1, 1):
            self.image = pygame.transform.smoothscale(self.image, scale)

        self.rect = self.image.get_rect()
        if "LEFT" in direction:
            self.rect.left = source_rect.left + offset[0]
        elif "RIGHT" in direction:
            self.rect.right = source_rect.right - offset[0]
        else:
            self.rect.centerx = source_rect.centerx
        if "BOTTOM" in direction:
            self.rect.bottom = source_rect.bottom - offset[1]
        elif "TOP" in direction:
            self.rect.top = source_rect.top + offset[1]
        else:
            self.rect.centery = source_rect.centery

    def output(self, win, offset_x, offset_y, master_volume, fps) -> None:
        adj_x = self.rect.x - offset_x
        adj_y = self.rect.y - offset_y
        win.blit(self.image, (adj_x, adj_y))
