import random
import sys
import time
import pygame
import csv
import json
from tkinter import messagebox
from os import listdir
from os.path import isfile, isdir, join
from enum import Enum, IntEnum


class MovementDirection(IntEnum):
    LEFT = -1
    RIGHT = 1

    def __str__(self):
        return self.name

    def swap(self):
        return MovementDirection(self.value * -1)


class DifficultyScale(float, Enum):
    EASIEST = 0.25
    EASY = 0.5
    MEDIUM = 1
    HARD = 1.5
    HARDEST = 2

    def __str__(self):
        return self.name.replace("_", " ")


def handle_exception(e):
    pygame.quit()
    messagebox.showerror(title="An error occurred", message="Even the agent couldn't glitch out of this!\n\nFile " + str(e) + " not found.")
    sys.exit()


def validate_file_list(dir, list, ext=None):
    out = []
    for name in list:
        if ext is None or name[-len(ext):].upper() == ext.upper():
            file = join("Assets", dir, name)
            if isfile(file):
                out.append(file)
    if len(out) > 0:
        return out
    else:
        return None


def load_picker_sprites(dir):
    images = []
    values = []
    path = join("Assets", dir)
    if isdir(path):
        folders = [f for f in listdir(path) if isdir(join(path, f))]
        for folder in folders:
            if str(folder).upper()[:6] == "PLAYER":
                lower_path = join(path, folder, "picker.png")
                if isfile(lower_path):
                    asset = pygame.transform.smoothscale_by(pygame.image.load(lower_path).convert_alpha(), 4)
                    surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
                    rect = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
                    surface.blit(asset, (0, 0), rect)
                    images.append(surface)
                    values.append([folder, "Retro" + folder if isfile(join(path, "Retro" + folder, "picker.png")) else None])
        if len(images) == 0:
            handle_exception(FileNotFoundError("No sprite images found in " + path))
        return images, values
    else:
        handle_exception(FileNotFoundError(path))


def load_level_images(dir):
    images = []
    values = []
    path = join("Assets", dir)
    if isdir(path):
        files = [f for f in listdir(path) if isfile(join(path, f)) and f[-4:].lower()==".png"]
        for file in sorted(files):
            asset = pygame.transform.smoothscale_by(pygame.image.load(join(path, file)).convert_alpha(), 4)
            surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
            rect = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
            surface.blit(asset, (0, 0), rect)
            images.append(surface)
            values.append(file.replace(".png", "").upper())
        if len(images) == 0:
            handle_exception(FileNotFoundError("No level images found in " + path))
        return images, values
    else:
        handle_exception(FileNotFoundError(path))


def make_image_from_text(width, height, header, body, border=5):
    text_header = pygame.font.SysFont("courier", 32).render(header, True, (255, 255, 255))
    box_header = pygame.Surface((text_header.get_width() + (border * 2), text_header.get_height() + (border * 2)), pygame.SRCALPHA)
    box_header.blit(text_header, (border, border))
    max_width = box_header.get_width()
    max_height = box_header.get_height()
    boxes_body = []
    for line in body:
        text_body = pygame.font.SysFont("courier", 16).render(line, True, (255, 255, 255))
        box_body = pygame.Surface((text_body.get_width() + (border * 2), text_body.get_height()), pygame.SRCALPHA)
        box_body.blit(text_body, (border, 0))
        max_width = max(width, box_body.get_width())
        max_height += box_body.get_height()
        boxes_body.append(box_body)
    box = pygame.Surface((max(width, max_width), max(height, max_height)), pygame.SRCALPHA)
    box.blit(box_header, ((box.get_width() - box_header.get_width()) // 2, (box.get_height() - max_height) // 2))
    for i in range(len(boxes_body)):
        box.blit(boxes_body[i], ((box.get_width() - max_width) // 2, ((box.get_height() - max_height) // 2) + box_header.get_height() + (i * boxes_body[i].get_height())))
    return box



def load_images(dir1, dir2):
    path = join("Assets", dir1, dir2)
    if isdir(path):
        images = [f for f in listdir(path) if isfile(join(path, f)) and f[-4:].lower()==".png"]

        all_images = {}
        for image in images:
            asset = pygame.image.load(join(path, image)).convert_alpha()
            surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
            rect = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
            surface.blit(asset, (0, 0), rect)
            all_images[str.upper(image.replace(".png", ""))] = surface

        return all_images
    else:
        handle_exception(FileNotFoundError(path))


def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, sprite_master, direction=False, grayscale=False):
    if sprite_master.get(dir2) is None:
        path = join("Assets", dir1, dir2)

        if not isdir(path):
            options = []
            for dir in listdir(join("Assets", dir1)):
                if len(dir2) < len(dir) and dir2.upper() == dir[:len(dir2)].upper():
                    options.append(dir)
            if len(options) > 0:
                i = random.randint(0, len(options) - 1)
                dir2 = options[i]
                path = join("Assets", dir1, dir2)
            else:
                handle_exception(FileNotFoundError(path))

        images = [f for f in listdir(path) if isfile(join(path, f))]

        all_sprites = {}
        for image in images:
            sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
            if grayscale:
                sprite_sheet = pygame.transform.grayscale(sprite_sheet)
            width = height = sprite_sheet.get_height()

            sprites = []
            for i in range(sprite_sheet.get_width() // width):
                surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
                rect = pygame.Rect(i * width, 0, width, height)
                surface.blit(sprite_sheet, (0, 0), rect)
                sprites.append(pygame.transform.scale2x(surface))

            if direction:
                all_sprites[str.upper(image.replace(".png", "")) + "_RIGHT"] = sprites
                all_sprites[str.upper(image.replace(".png", "")) + "_LEFT"] = flip(sprites)
            else:
                all_sprites[str.upper(image.replace(".png", ""))] = sprites
        sprite_master[dir2] = all_sprites
    return sprite_master[dir2]


def load_json_dict(dir, file):
    path = join("Assets", dir, file)
    try:
        with open(path, "r") as file:
            ref = json.loads(file.read())
        if bool(ref):
            return ref
        else:
            return {}
    except FileNotFoundError:
        handle_exception(FileNotFoundError(path))


def load_levels(dir):
    path = join("Assets", dir)
    if isdir(path):
        files = [f for f in listdir(path) if isfile(join(path, f))]
        files.sort()

        levels = {}
        for f in files:
            with open(join(path, f)) as level:
                reader = csv.reader(level, delimiter=",", quotechar='"')
                levels[str.upper(f.replace(".csv", "").replace(".txt", ""))] = [row for row in reader]

        return levels
    else:
        handle_exception(FileNotFoundError(path))


def __load_single_audio__(dir1, dir2):
    path = join("Assets", "SoundEffects", dir1, dir2)
    if isdir(path):
        sounds = {}
        for file in [f for f in listdir(path) if isfile(join(path, f))]:
            if sounds.get(dir2.upper()) is None:
                sounds[dir2.upper()] = []
            sounds[dir2.upper()].append(path + "\\" + file)
        return sounds
    else:
        handle_exception(FileNotFoundError(path))


def load_audios(dir):
    path = join("Assets", "SoundEffects", dir)
    if isdir(path):
        sounds = {}
        for sub_dir in [d for d in listdir(path) if isdir(path)]:
            sounds.update(__load_single_audio__(dir, sub_dir))

        sound_master = {}
        for key in sounds:
            for i in range(len(sounds[key])):
                file = sounds[key][i]
                if sound_master.get(file) is None:
                    sound_master[file] = {"file": file, "sound": pygame.mixer.Sound(file)}
                sounds[key][i] = sound_master[file]["sound"]

        return sounds
    else:
        handle_exception(FileNotFoundError(path))


def set_sound_source(source_rect, player_rect, type, channel):
    height_vol = max(1 - (abs(source_rect.y - player_rect.y) / 1000), 0)
    str_x = (source_rect.x - player_rect.x) / 1000
    if abs(str_x) > 1:
        left_vol = right_vol = 0
    elif str_x > 0:
        right_vol = max(1 - str_x, 0) * height_vol
        left_vol = right_vol ** 2
    elif str_x < 0:
        left_vol = max(1 + str_x, 0) * height_vol
        right_vol = left_vol ** 2
    else:
        left_vol = right_vol = 1
    channel.set_volume(left_vol * type, right_vol * type)


def load_text_from_file(file):
    path = join("Assets", "Text", file)
    if isfile(path):
        text = []
        with open(path, "r") as file:
            for line in file:
                text.append(line.replace("\n", ""))
        return text
    else:
        handle_exception(FileNotFoundError(path))


def display_text(output, win, controller, type=True):
    if output is None or output == "":
        return
    else:
        if not isinstance(output, list):
            output = [output]
        clear = pygame.display.get_surface().copy()
        for line in output:
            if type:
                text = []
                for i in range(len(line)):
                    text.append(line[i])
                    if (i == 0 and line[0] == "\"") or (i < len(line) - 1 and line[i + 1] == "\""):
                        pass
                    else:
                        text_line = pygame.font.SysFont("courier", 32).render("".join(text), True, (255, 255, 255))
                        text_box = pygame.Surface((text_line.get_width() + 10, text_line.get_height() + 10), pygame.SRCALPHA)
                        text_box.fill((0, 0, 0, 128))
                        text_box.blit(text_line, (5, 5))
                        win.blit(clear, (0, 0))
                        win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, win.get_height() - (text_box.get_height() + 100)))
                        pygame.display.update()
                        pause_dtime = 0
                        while pause_dtime < 80:
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    controller.save_profile(controller)
                                    pygame.quit()
                                    sys.exit()
                                elif event.type == pygame.KEYDOWN:
                                    pause_dtime += controller.handle_pause_unpause(event.key)
                                elif event.type == pygame.JOYBUTTONDOWN:
                                    pause_dtime += controller.handle_pause_unpause(event.button)
                            if controller.goto_load or controller.goto_main:
                                return
                            time.sleep(0.01)
                            pause_dtime += 10
            else:
                text = line
                text_line = pygame.font.SysFont("courier", 32).render("".join(text), True, (255, 255, 255))
                text_box = pygame.Surface((text_line.get_width() + 10, text_line.get_height() + 10), pygame.SRCALPHA)
                text_box.fill((0, 0, 0, 128))
                text_box.blit(text_line, (5, 5))
                win.blit(clear, (0, 0))
                win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, win.get_height() - (text_box.get_height() + 100)))
                pygame.display.update()

            sleep_time = max((len(text) // 20), 1) * 1000
            pause_dtime = 0
            while pause_dtime < sleep_time:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.save_profile(controller)
                        pygame.quit()
                        sys.exit()
                if type and controller.handle_anykey():
                    break
                if controller.goto_load or controller.goto_main:
                    return
                time.sleep(0.01)
                pause_dtime += 10


def glitch(odds, screen):
    color = [(42, 128, 65), (32, 93, 179), (129, 49, 176), (222, 60, 152), (102, 42, 40)]
    screen = screen.copy()
    glitches = []
    for i in range(random.randint(0, round(odds * screen.get_height() / 10))):
        width = random.randint(10, min(200, screen.get_width()))
        height = random.randint(1, min(50, screen.get_height()))
        x = random.randint(0, screen.get_width() - width)
        y = random.randint(0, screen.get_height() - height)
        copy = screen.subsurface(pygame.Rect(min(max(x + random.randint(-2, 2), 0), screen.get_width() - width), min(max(y + random.randint(-2, 2), 0), screen.get_height() - height), width, height))
        spot = pygame.Surface((width, height), pygame.SRCALPHA)
        spot.fill(color[random.randint(0, len(color) - 1)])
        spot.set_alpha(50)
        copy.blit(spot, (0, 0))
        glitches.append([copy, (x, y)])
    return glitches


def load_path(path_in, i, j, block_size):
    path = []
    for k in range(0, len(path_in), 2):
        if k >= 2 and path_in[k] == path_in[k - 2] and path_in[k + 1] == path_in[k - 1]:
            path[-1].append(True)
        else:
            path.append([(path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size])
    return path


def set_property(entity, input):
    if input is not None:
        target, property, value = input["target"], input["property"], input["value"]
        if len(target) == len(property) == len(value):
            for i in range(len(target)):
                if isinstance(value[i], str):
                    if value[i].upper() in ("TRUE", "FALSE"):
                        value[i] = bool(value[i].upper() == "TRUE")
                    elif value[i].isnumeric():
                        value[i] = float(value[i])
                        if value[i] == int(value[i]):
                            value[i] = int(value[i])
                for obj in [entity.level.get_player()] + entity.level.get_objects():
                    if obj.name.split()[0] == target[i] and hasattr(obj, property[i]):
                        setattr(obj, property[i], value[i])
                        if entity.controller.player_abilities.get(property[i]) is not None:
                            entity.controller.player_abilities[property[i]] = value[i]
