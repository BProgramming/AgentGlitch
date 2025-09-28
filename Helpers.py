import random
import sys
import time
import traceback

import pygame
import csv
import json
from tkinter import messagebox
from os import listdir
from os.path import isfile, isdir, join
from enum import Enum, IntEnum


ASSETS_FOLDER: str = "Assets"
GAME_DATA_FOLDER: str = "GameData"
FIRST_LEVEL_NAME: str = "__START__"


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

    def __str__(self) -> str:
        return self.name.replace("_", " ")


def handle_exception(msg) -> None:
    pygame.quit()
    cur_time = time.gmtime(time.time())
    filename_time = time.strftime("%Y%m%d_%H%M%S", cur_time)
    printable_time = time.strftime("%Y-%m-%d, %H:%M:%S", cur_time)
    log_file = join(GAME_DATA_FOLDER, "glitch_" + filename_time + ".log")
    with open(log_file, "w") as log:
        print(f"Error encountered at GMT {printable_time}:", file=log)
        traceback.print_exc(file=log)
    messagebox.showerror(title="Even the agent couldn't glitch out of this!", message="ERROR: " + msg + "\nMore info available in " + log_file)
    sys.exit()


def validate_file_list(dir, lst, ext=None) -> list | None:
    out = []
    for name in lst:
        if ext is None or name[-len(ext):].upper() == ext.upper():
            file = join(ASSETS_FOLDER, dir, name)
            if isfile(file):
                out.append(file)
    if len(out) > 0:
        return out
    else:
        return None


def load_picker_sprites(dir) -> tuple | None:
    images = {"normal": [], "retro": []}
    values = []
    path = join(ASSETS_FOLDER, dir)
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
                    images["normal"].append(surface)
                    values.append([folder])
                    retro_path = join(path, "Retro" + folder, "picker.png")
                    if isfile(retro_path):
                        asset = pygame.transform.grayscale(pygame.transform.smoothscale_by(pygame.image.load(retro_path).convert_alpha(), 4))
                        surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
                        rect = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
                        surface.blit(asset, (0, 0), rect)
                        images["retro"].append(surface)
                        values[-1].append("Retro" + folder)
                    else:
                        images["retro"].append(None)
                        values[-1].append(None)
        if len(images) == 0:
            handle_exception("No sprite images found in " + str(FileNotFoundError(path)) + ".")
        return images, values
    else:
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def load_level_images(dir) -> tuple | None:
    images = []
    values = []
    path = join(ASSETS_FOLDER, dir)
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
            handle_exception("No level images found in " + str(FileNotFoundError(path)) + ".")
        return images, values
    else:
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def make_image_from_text(width, height, header, body, border=5) -> pygame.Surface:
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



def load_images(dir1, dir2) -> dict | None:
    path = join(ASSETS_FOLDER, dir1, dir2) if dir2 is not None else join(ASSETS_FOLDER, dir1)
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
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def flip(sprites) -> list:
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, sprite_master, direction=False, grayscale=False) -> dict:
    if sprite_master.get(dir2) is None:
        path = join(ASSETS_FOLDER, dir1, dir2)

        if not isdir(path):
            options = []
            for dir in listdir(join(ASSETS_FOLDER, dir1)):
                if len(dir2) < len(dir) and dir2.upper() == dir[:len(dir2)].upper():
                    options.append(dir)
            if len(options) > 0:
                i = random.randint(0, len(options) - 1)
                dir2 = options[i]
                path = join(ASSETS_FOLDER, dir1, dir2)
            else:
                handle_exception("File " + str(FileNotFoundError(path)) + " not found.")

        images = [f for f in listdir(path) if isfile(join(path, f))]

        all_sprites = {}
        for image in images:
            sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
            if grayscale:
                sprite_sheet = pygame.transform.grayscale(sprite_sheet)
            width = height = sprite_sheet.get_height()

            sprites = []
            for i in range(sprite_sheet.get_width() // width):
                surface = pygame.Surface((width, height), pygame.SRCALPHA)
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


def load_json_dict(dir, file) -> dict | None:
    path = join(ASSETS_FOLDER, dir, file)
    try:
        with open(path, "r") as file:
            ref = json.loads(file.read())
        if bool(ref):
            return ref
        else:
            return {}
    except FileNotFoundError:
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def load_object_dicts(dir) -> dict | None:
    path = join(ASSETS_FOLDER, dir)
    if isdir(path):
        files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith(".agd")]
        dicts = {}
        for f in files:
            dicts[str.upper(f.replace(".agd", ""))] = load_json_dict(dir, f)
        return dicts
    else:
        handle_exception("File or folder " + str(FileNotFoundError(path)) + " not found.")
        return None


def load_levels(dir) -> dict | None:
    path = join(ASSETS_FOLDER, dir)
    if isdir(path):
        files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith(".agl")]
        files.sort()

        levels = {}
        for f in files:
            with open(join(path, f)) as level:
                reader = csv.reader(level, delimiter=",", quotechar='"')
                levels[str.upper(f.replace(".agl", ""))] = [row for row in reader]

        return levels
    else:
        handle_exception("File or folder " + str(FileNotFoundError(path)) + " not found.")
        return None


def __load_single_audio__(dir1, dir2) -> dict | None:
    path = join(ASSETS_FOLDER, "SoundEffects", dir1, dir2)
    if isdir(path):
        sounds = {}
        for file in [f for f in listdir(path) if isfile(join(path, f))]:
            if sounds.get(dir2.upper()) is None:
                sounds[dir2.upper()] = []
            sounds[dir2.upper()].append(path + "\\" + file)
        return sounds
    else:
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def load_audios(dir, dir2=None) -> dict | None:
    if dir2 is None:
        path = join(ASSETS_FOLDER, "SoundEffects", dir)
    else:
        path = join(ASSETS_FOLDER, "SoundEffects", dir, dir2)
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
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def set_sound_source(source_rect, player_rect, sound_type, channel) -> None:
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
    channel.set_volume(left_vol * sound_type, right_vol * sound_type)


def load_text_from_file(file) -> list | None:
    path = join(ASSETS_FOLDER, "Text", file)
    if isfile(path):
        text = []
        with open(path, "r") as file:
            for line in file:
                text.append(line.replace("\n", ""))
        return text
    else:
        handle_exception("File " + str(FileNotFoundError(path)) + " not found.")
        return None


def display_text(output: list | str, controller, should_type_text=False, min_pause_time=80, should_sleep=True, audio=None) -> None:
    if output is None or output == "":
        return
    else:
        win = controller.win
        if not isinstance(output, list):
            output = [output]
        clear = pygame.display.get_surface().copy()
        for j in range(len(output)):
            line = output[j]
            if should_type_text:
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
                        while pause_dtime < min_pause_time:
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    controller.quit()
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

            if should_sleep:
                if audio is not None and isinstance(audio, list) and len(output) == len(audio) and audio[j] is not None:
                    sleep_time = audio[j].get_length() * 1000
                    channel = pygame.mixer.find_channel(force=True)
                    channel.set_volume(controller.master_volume["cinematics"])
                    channel.play(audio[j])
                else:
                    sleep_time = max((len(text) // 20), 1) * 1000
                pause_dtime = 0
                while pause_dtime < sleep_time:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            controller.quit()
                    if should_type_text and controller.handle_any_key():
                        break
                    if controller.goto_load or controller.goto_main:
                        return
                    time.sleep(0.01)
                    pause_dtime += 10


def glitch(odds, screen) -> list:
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


def load_path(path_in, i, j, block_size) -> list:
    path = []
    for k in range(0, len(path_in), 2):
        if k >= 2 and path_in[k] == path_in[k - 2] and path_in[k + 1] == path_in[k - 1]:
            path[-1].append(True)
        else:
            path.append([(path_in[k] + j) * block_size, (path_in[k + 1] + i) * block_size])
    return path


def set_property(triggering_entity, prop_to_set) -> None:
    if prop_to_set is not None:
        target, property, value = prop_to_set["target"], prop_to_set["property"], prop_to_set["value"]
        if len(target) == len(property) == len(value):
            for i in range(len(target)):
                if isinstance(value[i], str):
                    if value[i].upper() in ("TRUE", "FALSE"):
                        value[i] = bool(value[i].upper() == "TRUE")
                    elif value[i].isnumeric():
                        value[i] = float(value[i])
                        if value[i] == int(value[i]):
                            value[i] = int(value[i])
                for ent in [triggering_entity.level.get_player()] + triggering_entity.level.get_entities():
                    if (ent.name.split()[0] == target[i] or ent.name == target[i]) and hasattr(ent, property[i]):
                        setattr(ent, property[i], value[i])
                        if triggering_entity.controller.player_abilities.get(property[i]) is not None:
                            triggering_entity.controller.player_abilities[property[i]] = value[i]
