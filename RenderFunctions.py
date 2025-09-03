import pygame
import time
import sys
from os.path import join, isfile


def get_offset(level, offset_x, offset_y, width, height):
    scroll_area_width = width * 0.375
    scroll_area_height = height * 0.25

    if level.get_player().rect.right - scroll_area_width < offset_x:
        offset_x = level.get_player().rect.right - scroll_area_width
    elif level.get_player().rect.left + scroll_area_width > offset_x + width:
        offset_x = level.get_player().rect.left - (width - scroll_area_width)
    if offset_x < level.level_bounds[0][0]:
        offset_x = level.level_bounds[0][0]
    elif offset_x > level.level_bounds[1][0] - width:
        offset_x = level.level_bounds[1][0] - width

    if level.get_player().rect.bottom - (2 * scroll_area_height) < offset_y:
        offset_y = level.get_player().rect.bottom - (2 * scroll_area_height)
    elif level.get_player().rect.top - (height - scroll_area_height) > offset_y:
        offset_y = level.get_player().rect.top - (height - scroll_area_height)
    if offset_y < level.level_bounds[0][1]:
        offset_y = level.level_bounds[0][1]
    elif offset_y > level.level_bounds[1][1] - height:
        offset_y = level.level_bounds[1][1] - height
    return offset_x, offset_y

def get_background(level):
    file = join("Assets", "Background", level.background)
    if not isfile(file):
        file = join("Assets", "Background", "Blue.png")
    image = pygame.image.load(file).convert_alpha()
    if level.grayscale:
        image = pygame.transform.grayscale(image)
    _, _, width, height = image.get_rect()

    tiles = []
    for i in range(max((level.level_bounds[1][0] // width), 1)):
        for j in range(max((level.level_bounds[1][1] // height), 1)):
            tiles.append((i * width, j * height))

    return tiles, image


def get_foreground(level):
    if level.foreground is None:
        return None
    else:
        file = join("Assets", "Foreground", level.foreground)
        if isfile(file):
            image = pygame.image.load(file).convert_alpha()
            if level.grayscale:
                image = pygame.transform.grayscale(image)
            return image
        else:
            return None


def fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win, direction="in"):
    black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
    black.fill((0, 0, 0))
    for i in range(64):
        draw(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller.master_volume, 1, win)
        if direction == "in":
            black.set_alpha(255 - (4 * i))
            volume = (i + 1) / 64
        elif direction == "out":
            black.set_alpha(4 * i)
            volume = 1 - ((i + 1) / 64)
        else:
            volume = 1
        win.blit(black, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                controller.save_player_profile(controller)
                pygame.quit()
                sys.exit()
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume((controller.master_volume["background"]) * volume)
        time.sleep(0.01)


def fade_in(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win):
    fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win=win, direction="in")


def fade_out(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win):
    fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win=win, direction="out")
    win.fill((0, 0, 0))


def draw(background, bg_image, fg_image, level, hud, offset_x, offset_y, master_volume, fps, win, glitches=None):
    screen = pygame.Rect(offset_x, offset_y, win.get_width(), win.get_height())

    if len(background) == 1:
        win.blit(bg_image.subsurface(screen), (0, 0))
    else:
        for tile in background:
            win.blit(bg_image, (tile[0] - offset_x, tile[1] - offset_y))

    level.output(win, offset_x, offset_y, master_volume, fps)

    if fg_image is not None:
        win.blit(fg_image.subsurface(screen), (0, 0))

    hud.output(level.get_formatted_time())

    if glitches is not None:
        for spot in glitches:
            win.blit(spot[0], spot[1])
