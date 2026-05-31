from __future__ import annotations
from typing import Any, TYPE_CHECKING
import csv
import json
import pygame
import random
import re
import sys
import time
import traceback
from enum import (
    Enum,
    IntEnum,
)
from pathlib import Path
from tkinter import messagebox

if TYPE_CHECKING:
    from Controller import Controller
    from Entity import Entity
    from Trigger import Trigger


ASSETS_FOLDER:    Path = Path(__file__).parent / "Assets"
GAME_DATA_FOLDER: Path = Path.home() / ".agentglitch"
GAME_DATA_FOLDER.mkdir(parents=True, exist_ok=True)

DLC_APP_ID: int = 0

NORMAL_WHITE:   tuple[int, int, int, int]  = (255, 255, 255, 255)
RETRO_WHITE:    tuple[int, int, int, int]  = (250, 215, 195, 255)
NORMAL_BLACK:   tuple[int, int, int, int]  = (33, 31, 48, 255)
RETRO_BLACK:    tuple[int, int, int, int]  = (0, 0, 0, 255)
GLITCH_COLOURS: list[tuple[int, int, int]] = [(42, 128, 65), (32, 93, 179), (129, 49, 176), (222, 60, 152), (102, 42, 40)]

TEXT_BOX_BORDER_RADIUS: int = 4

RUMBLE_EFFECT_HIGH:     float | int = 0.5
RUMBLE_EFFECT_LOW:      float | int = 0.1
RUMBLE_EFFECT_DURATION: int         = 500 # if this is 0, it will rumble until stop_rumble() is called (so don't set it to 0!)


class MovementDirection(IntEnum):
    LEFT  = -1
    RIGHT =  1

    def __str__(
            self: MovementDirection,
    ):
        return self.name

    def swap(
            self: MovementDirection,
    ):
        return MovementDirection(self.value * -1)


class DifficultyScale(float, Enum):
    EASIEST = 0.25
    EASY    = 0.50
    MEDIUM  = 1.00
    HARD    = 1.50
    HARDEST = 2.00

    def __str__(
            self: DifficultyScale,
    ) -> str:
        return self.name.replace("_", " ")


def handle_exception(
        msg: str,
) -> None:
    if pygame.get_init():
        pygame.quit()

    cur_time       = time.gmtime(time.time())
    filename_time  = time.strftime("%Y%m%d_%H%M%S", cur_time)
    printable_time = time.strftime("%Y-%m-%d, %H:%M:%S", cur_time)

    log_file = Path(Path(GAME_DATA_FOLDER) / f"glitch_{filename_time}.log").resolve()

    with open(log_file, "w") as log:
        print(f"Error encountered at GMT {printable_time}:", file = log)
        traceback.print_exc(file = log)

    messagebox.showerror(
        title   = "Even the agent couldn't glitch out of this!",
        message = f"ERROR: {msg}\nMore info available in {log_file}.",
    )
    sys.exit()


def link_trigger(
        to_link:      list[str],
        to_be_linked: list[Trigger],
) -> list[Trigger]:
    triggers = []

    for active_triggers in to_link:
        for possible_triggers in to_be_linked:
            if possible_triggers.name.casefold().startswith(active_triggers.casefold()):
                triggers.append(possible_triggers)
                break

    return triggers


def validate_file_list(
        directory: str,
        files:     list[str],
        ext:       str | None = None,
) -> list[str]:
    out = []

    for name in files:
        file = ASSETS_FOLDER / directory / name
        if file.is_file() and (not ext or file.suffix.casefold() == ext):
            out.append(file.resolve())

    return out


def image_to_retro(
        img: pygame.Surface,
) -> pygame.Surface:

    img           = pygame.transform.grayscale(img)
    tint_color    = RETRO_WHITE
    color_surface = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    color_surface.fill(tint_color)
    img.blit(color_surface, (0, 0), special_flags = pygame.BLEND_RGBA_MULT)

    return img


def load_picker_sprites(
        directory: str,
) -> tuple[dict[str, list[Any]], list[Any]] | None:
    images = {"normal": [], "retro": []}
    values = []
    path   = ASSETS_FOLDER / directory

    if not path.is_dir():
        handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    for folder in [f for f in path.iterdir() if Path(path / f).is_dir()]:
        if folder.name.casefold().startswith("player"):
            lower_path = folder / "picker.png"
            if lower_path.is_file():
                asset   = pygame.transform.smoothscale_by(pygame.image.load(lower_path).convert_alpha(), 4)
                surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
                rect    = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
                surface.blit(asset, (0, 0), rect)
                images["normal"].append(surface)
                values.append(folder.name[-1])
                retro_path = path / f"Retro{folder}" / "picker.png"
                if retro_path.is_file():
                    asset   = image_to_retro(pygame.transform.smoothscale_by(pygame.image.load(retro_path).convert_alpha(), 4))
                    surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
                    rect    = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
                    surface.blit(asset, (0, 0), rect)
                    images["retro"].append(surface)
                else:
                    images["retro"].append(None)

    if not images or not values:
        handle_exception(f"No sprite images found in {FileNotFoundError(path.resolve())}.")
        return None

    return images, values


def load_level_images(
        directory: str,
) -> tuple | None:
    images = []
    values = []
    path   = ASSETS_FOLDER / directory

    if not path.is_dir():
        handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    for file in sorted([f for f in path.iterdir() if Path(path / f).is_file() and f.suffix.casefold() == ".png"]):
        asset   = pygame.transform.smoothscale_by(pygame.image.load(Path(path) / file).convert_alpha(), 4)
        surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
        rect    = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
        surface.blit(asset, (0, 0), rect)
        images.append(surface)
        values.append(file.stem.upper())

    if not images or not values:
        handle_exception(f"No level images found in {FileNotFoundError(path.resolve())}.")
        return None

    return images, values


def make_image_from_text(
        width:  float | int,
        height: float | int,
        header: str,
        body:   list[str],
        border: int  = 5,
        retro:  bool = False,
) -> pygame.Surface:
    text_header = pygame.font.SysFont("courier", 32).render(header, True, RETRO_WHITE if retro else NORMAL_WHITE)

    max_width:  float | int = text_header.get_width()
    max_height: float | int = text_header.get_height()

    boxes_body  = []
    for line in body:
        text_body = pygame.font.SysFont("courier", 16).render(line, True, RETRO_WHITE if retro else NORMAL_WHITE)
        box_body  = pygame.Surface((text_body.get_width() + (border * 2), text_body.get_height()), pygame.SRCALPHA)
        box_body.blit(text_body, (border, 0))
        max_width  =  max(width, box_body.get_width())
        max_height += box_body.get_height()
        boxes_body.append(box_body)

    box = pygame.Surface((max(width, max_width), max(height, max_height)), pygame.SRCALPHA)
    box.blit(text_header, ((box.get_width() - text_header.get_width()) / 2, (box.get_height() - max_height) / 2))

    for i, body_box in enumerate(boxes_body):
        box.blit(body_box, ((box.get_width() - max_width) / 2, ((box.get_height() - max_height) / 2) + text_header.get_height() + (i * body_box.get_height())))

    return box


def load_images(
        dir1: str,
        dir2: str,
) -> dict | None:
    path = ASSETS_FOLDER / dir1 / dir2 if dir2 else ASSETS_FOLDER / dir1

    if not path.is_dir():
        handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    images = {}
    for image in [f for f in path.iterdir() if Path(path / f).is_file() and f.suffix.casefold() == ".png"]:
        asset   = pygame.image.load(Path(path) / image).convert_alpha()
        surface = pygame.Surface((asset.get_width(), asset.get_height()), pygame.SRCALPHA)
        rect    = pygame.Rect(0, 0, asset.get_width(), asset.get_height())
        surface.blit(asset, (0, 0), rect)
        images[image.stem.upper()] = surface

    if not images:
        handle_exception(f"No images found in {FileNotFoundError(path.resolve())}.")

    return images


def flip(
        sprites: list[pygame.Surface],
) -> list[pygame.Surface]:
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(
        dir1:          str,
        dir2:          str,
        sprite_master: dict[str, dict[str, list[pygame.Surface]]],
        direction:     bool = False,
        retro:         bool = False,
) -> dict[str, list[pygame.Surface]]:
    if not sprite_master.get(dir2):
        path = ASSETS_FOLDER / dir1 / dir2

        if not path.is_dir():
            options = []

            for directory in Path(ASSETS_FOLDER / dir1).iterdir():
                if len(dir2) < len(directory.name) and directory.name.casefold().startswith(dir2.casefold()):
                    options.append(directory)

            if not options:
                handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
                return {}

            i = random.randint(0, len(options) - 1)
            dir2 = options[i]
            path = ASSETS_FOLDER / dir1 / dir2

        all_sprites = {}
        for image in [f for f in path.iterdir() if Path(path / f).is_file()]:
            sprite_sheet = pygame.image.load(path / image).convert_alpha()
            if retro:
                sprite_sheet = image_to_retro(sprite_sheet)
            width = height = sprite_sheet.get_height()

            sprites = []
            for i in range(sprite_sheet.get_width() // width):
                surface = pygame.Surface((width, height), pygame.SRCALPHA)
                rect    = pygame.Rect(i * width, 0, width, height)
                surface.blit(sprite_sheet, (0, 0), rect)
                sprites.append(pygame.transform.scale2x(surface))

            if direction:
                all_sprites[f"{image.stem.upper()}_RIGHT"] = sprites
                all_sprites[f"{image.stem.upper()}_LEFT"] = flip(sprites)
            else:
                all_sprites[image.stem.upper()] = sprites

        sprite_master[dir2] = all_sprites

    return sprite_master[dir2]


def load_json_dict(
        directory: str,
        file:      str,
) -> dict | None:
    path = ASSETS_FOLDER / directory / file

    try:
        with open(path, "r") as file:
            return json.loads(file.read())
    except FileNotFoundError:
        handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None


def load_object_dicts(
        directory: str,
) -> dict | None:
    path = ASSETS_FOLDER / directory

    if not path.is_dir():
        handle_exception(f"File or folder {FileNotFoundError(path.resolve())} not found.")
        return None

    dicts = {}
    for f in [f for f in path.iterdir() if Path(path / f).is_file() and f.suffix.casefold() == ".agd"]:
        dicts[f.stem.upper()] = load_json_dict(directory, f.name)

    return dicts


def load_levels(
        directory: str,
) -> dict | None:
    path = ASSETS_FOLDER / directory

    if not path.is_dir():
        handle_exception(f"File or folder {FileNotFoundError(path.resolve())} not found.")
        return None

    levels = {}
    for f in sorted([f for f in path.iterdir() if Path(path / f).is_file() and f.suffix.casefold() == ".agl"]):
        with open(path / f) as level:
            reader = csv.reader(level, delimiter=",", quotechar='"')
            levels[f.stem.upper()] = [row for row in reader]

    return levels


def __load_single_audio__(
        path:           Path,
        suppress_error: bool = False,
) -> dict | None:
    if not path.is_dir():
        if not suppress_error:
            handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    sounds = {}
    for file in [f for f in path.iterdir() if f.is_file() and f.suffix.casefold() in (".mp3", ".wav", ".wave")]:
        if not sounds.get(path.stem.upper()):
            sounds[path.name.upper()] = []
        sounds[path.name.upper()].append(Path(path / file).resolve())

    return sounds


def load_audios(
        dir1:           str,
        dir2:           str | None = None,
        suppress_error: bool       = False,
) -> dict | None:
    path = ASSETS_FOLDER / "SoundEffects" / dir1
    if dir2:
        path = path / dir2

    if not path.is_dir():
        if not suppress_error:
            handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    sounds = {}
    for sub_dir in [d for d in path.iterdir() if Path(Path(path) / d).is_dir()]:
        audio = __load_single_audio__(sub_dir, suppress_error = suppress_error)
        if audio:
            sounds.update(audio)

    sound_master = {}
    for key in sounds:
        for i, sound in enumerate(sounds[key]):
            file = sound

            if not sound_master.get(file):
                sound_master[file] = {"file": file, "sound": pygame.mixer.Sound(file)}

            if sound_master[file].get("sound"):
                sounds[key][i] = sound_master[file]["sound"]

    return sounds


def set_sound_source(
        source_rect:  pygame.Rect | None,
        player_rect:  pygame.Rect | None,
        vol_modifier: float | int | None,
        channel:      pygame.mixer.Channel | None,
) -> None:
    if not source_rect or not player_rect or not vol_modifier or not channel:
        return None

    height_vol = max(1 - (abs(source_rect.y - player_rect.y) / 1000), 0)

    strength_x = (source_rect.x - player_rect.x) / 1000
    if abs(strength_x) > 1:
        left_vol  = right_vol = 0
    elif strength_x > 0:
        right_vol = max(1 - strength_x, 0) * height_vol
        left_vol  = right_vol ** 2
    elif strength_x < 0:
        left_vol  = max(1 + strength_x, 0) * height_vol
        right_vol = left_vol  ** 2
    else:
        left_vol  = right_vol = 1

    channel.set_volume(left_vol * vol_modifier, right_vol * vol_modifier)

    return None


def load_text_from_file(
        file: str,
) -> list[str] | None:
    path = ASSETS_FOLDER / "Text" / file

    if not path.is_file():
        handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    text = []
    with open(path, "r") as file:
        for line in file:
            text.append(line.replace("\n", ""))

    return text


def process_text(
        line: str,
        controller: Controller,
) -> tuple[str, bool, bool]:
    if "<b>" in line:
        line = line.replace("<b>", "")
        is_bold = True
    else:
        is_bold = False

    if "<i>" in line:
        line = line.replace("<i>", "")
        is_italics = True
    else:
        is_italics = False

    if "<key=" in line:
        keys_to_replace = re.findall(r"<key=\w+>", line)
        for i, key in enumerate(keys_to_replace):
            key_partial = key[5:-1]
            keys_out    = []

            if controller.active_keyboard_layout and controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout].get(key_partial):
                keys_out += controller.KEYBOARD_LAYOUTS[controller.active_keyboard_layout][key_partial]
            elif controller.active_gamepad_layout and controller.GAMEPAD_LAYOUTS[controller.active_gamepad_layout].get(key_partial):
                keys_out += controller.GAMEPAD_LAYOUTS[controller.active_gamepad_layout][key_partial]
            elif i == 0:
                keys_out = ["KEY NOT FOUND"]

            if len(keys_out) > 2:
                txt = f"{", ".join([pygame.key.name(int(k)).title() for k in keys_out[:-1]])}, or {pygame.key.name(int(keys_out[-1])).title()}"
            elif len(keys_out) > 1:
                txt = f"{pygame.key.name(int(keys_out[0])).title()} or {pygame.key.name(int(keys_out[1])).title()}"
            elif len(keys_out) == 1:
                if keys_out[0] == "KEY NOT FOUND":
                    txt = f"{keys_out[0]}"
                else:
                    txt = f"{pygame.key.name(int(keys_out[0])).title()}"
            else:
                txt = ""

            line = line.replace(key, txt)

    return line, is_bold, is_italics


def display_text(
        output:           list | str,
        controller:       Controller,
        should_type_text: bool =False,
        min_pause_time:   float | int = 0.08,
        should_sleep:     bool = True,
        audio:            list[pygame.mixer.Sound] | None = None,
        retro:            bool = False,
        background:       bool = False,
) -> None:
    if not output:
        return None

    text_colour = RETRO_WHITE if retro else NORMAL_WHITE
    box_colour  = RETRO_BLACK if retro else NORMAL_BLACK
    box_colour  = (box_colour[0], box_colour[1], box_colour[2], 128)
    win         = controller.win
    clear       = pygame.display.get_surface().copy()

    if not isinstance(output, list):
        output = [output]

    if retro and not should_type_text:
        if background:
            box_wide = pygame.Surface((win.get_width(), win.get_height() * 0.06))
            box_tall = pygame.Surface((win.get_width() * 0.06, win.get_height()))
            box_wide.fill(RETRO_BLACK)
            box_tall.fill(RETRO_BLACK)
            clear.blit(box_wide, (0, 0))
            clear.blit(box_wide, (0, win.get_height() - box_wide.get_height()))
            clear.blit(box_tall, (0, 0))
            clear.blit(box_tall, (win.get_width() - box_tall.get_width(), 0))
        else:
            clear.fill(RETRO_BLACK)

        line1 = pygame.Surface((win.get_width() * 0.75, 2), pygame.SRCALPHA)
        line2 = pygame.Surface((win.get_width() * 0.5, 2), pygame.SRCALPHA)
        line1.fill(RETRO_WHITE)
        line2.fill(RETRO_WHITE)
        clear.blit(line1, ((win.get_width() - line1.get_width()) // 2, win.get_height() * 0.06))
        clear.blit(line1, ((win.get_width() - line1.get_width()) // 2, win.get_height() * 0.94))
        clear.blit(line2, ((win.get_width() - line2.get_width()) // 2, win.get_height() * 0.05))
        clear.blit(line2, ((win.get_width() - line2.get_width()) // 2, win.get_height() * 0.95))

    for j in range(len(output)):
        line, is_bold, is_italics = process_text(output[j], controller)

        if should_type_text:
            text = []
            for i in range(len(line)):
                text.append(line[i])

                if (i == 0 and line[0] == "\"") or (i < len(line) - 1 and line[i + 1] == "\""):
                    pass
                else:
                    text_line = pygame.font.SysFont("courier", 32, bold=is_bold, italic=is_italics).render("".join(text), True, text_colour)
                    text_box  = pygame.Surface((text_line.get_width() + 10, text_line.get_height() + 10), pygame.SRCALPHA)

                    pygame.draw.rect(text_box, box_colour, pygame.Rect(0, 0, text_box.get_width(), text_box.get_height()), border_radius=TEXT_BOX_BORDER_RADIUS)
                    text_box.blit(text_line, (5, 5))
                    win.blit(clear, (0, 0))
                    win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, win.get_height() - (text_box.get_height() + 100)))

                    pygame.display.update()

                    pause_dtime: float | int = 0.0
                    while pause_dtime < min_pause_time:
                        for event in pygame.event.get():
                            match event.type:
                                case pygame.QUIT:
                                    controller.quit()
                                case pygame.KEYDOWN:
                                    pause_dtime += controller.handle_pause_unpause(event.key)
                                case pygame.JOYBUTTONDOWN:
                                    pause_dtime += controller.handle_pause_unpause(event.button)
                                case _:
                                    pass

                        if controller.goto_load or controller.goto_main:
                            return None

                        time.sleep(0.01)
                        pause_dtime += 0.01
        else:
            text      = line
            text_line = pygame.font.SysFont("courier", 32, bold=is_bold, italic=is_italics).render("".join(text), True, text_colour)
            text_box  = pygame.Surface((text_line.get_width() + 10, text_line.get_height() + 10), pygame.SRCALPHA)

            pygame.draw.rect(text_box, box_colour, pygame.Rect(0, 0, text_box.get_width(), text_box.get_height()), border_radius=TEXT_BOX_BORDER_RADIUS)
            text_box.blit(text_line, (5, 5))
            win.blit(clear, (0, 0))

            if retro:
                win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, ((win.get_height() - text_box.get_height()) // 2)))
            else:
                win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, win.get_height() - (text_box.get_height() + 100)))

            pygame.display.update()

        if should_sleep:
            if audio and isinstance(audio, list) and len(output) == len(audio) and audio[j] is not None:
                sleep_time = audio[j].get_length()
                channel    = pygame.mixer.find_channel(force=True)
                channel.set_volume(controller.master_volume["cinematics"])
                channel.play(audio[j])
            else:
                sleep_time = max((len(text) // 20), 1)

            pause_dtime = 0
            while pause_dtime < sleep_time:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.quit()
                if should_type_text and controller.handle_any_key():
                    break
                if controller.goto_load or controller.goto_main:
                    return None
                time.sleep(0.01)
                pause_dtime += 0.01

    return None


def glitch(
        odds:   float | int,
        screen: pygame.Surface,
) -> list:
    color    = GLITCH_COLOURS
    screen   = screen.copy()
    glitches = []

    for i in range(random.randint(0, round(odds * screen.get_height() / 10))):
        width  = random.randint(10, min(200, screen.get_width()))
        height = random.randint(1, min(50, screen.get_height()))

        x = random.randint(0, screen.get_width() - width)
        y = random.randint(0, screen.get_height() - height)

        copy = screen.subsurface(
            pygame.Rect(min(max(x + random.randint(-2, 2), 0), screen.get_width() - width),
                        min(max(y + random.randint(-2, 2), 0), screen.get_height() - height),
                        width,
                        height,
                        ),
        )
        spot = pygame.Surface((width, height), pygame.SRCALPHA)
        spot.fill(color[random.randint(0, len(color) - 1)])
        spot.set_alpha(50)
        copy.blit(spot, (0, 0))

        glitches.append([copy, (x, y)])

    return glitches


def load_path(
        path_in:    list[str] | tuple[str] | None,
        i:          float | int,
        j:          float | int,
        block_size: float | int,
) -> list[list[tuple[float | int, float | int] | bool]] | None:
    if not path_in:
        return None

    path: list[list[tuple[float | int, float | int] | bool]] = []

    for k in range(len(path_in)):
        if k > 0 and path_in[k] == path_in[k - 1]:
            path[-1].append(True)
        else:
            try:
                x = (int(path_in[k][0]) + j) * block_size
                y = (int(path_in[k][1]) + i) * block_size
                path.append([(x, y)])
            except ValueError:
                handle_exception(f"Path {path_in[k]} could not be resolved.")
                return None

    return path if path else None


def set_property(
        triggering_entity: Entity,
        prop_to_set:       dict[str, Any]
) -> None:
    if prop_to_set:
        targs, props, vals = prop_to_set["target"], prop_to_set["property"], prop_to_set["value"]

        if not isinstance(targs, list):
            targs = [targs]
        if not isinstance(props, list):
            props = [props]
        if not isinstance(vals, list):
            vals = [vals]

        if len(targs) == len(props) == len(vals):
            for i in range(len(targs)):
                targ = targs[i]
                prop = props[i]
                val  = vals[i]

                if isinstance(val, str):
                    if val.casefold() in ("true", "false"):
                        val = bool(val.casefold() == "true")
                    elif val.isnumeric():
                        val = float(val)
                        if val == int(val):
                            val = int(val)

                for ent in triggering_entity.level.entities:
                    if ent.name.casefold().startswith(targ.casefold()):
                        if hasattr(ent, prop):
                            setattr(ent, prop, val)
                        elif prop.casefold().startswith("can_") and hasattr(ent, "abilities") and isinstance(ent.abilities, dict):
                            ent.abilities[prop.casefold()] = val
    return None
