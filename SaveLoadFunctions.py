import pygame
import pickle
from os.path import join, isfile
from Actor import Actor
from Block import BreakableBlock
from Helpers import GAME_DATA_FOLDER, FIRST_LEVEL_NAME


def save_player_profile(controller, level):
    profile_file = join(GAME_DATA_FOLDER, "profile.p")
    with open(profile_file, "rb") as f:
        data = pickle.load(open(profile_file, "rb"))

    if level is not None:
        cur_level = level.name
    elif data is not None and data.get("level") is not None:
        cur_level = data["level"]
    else:
        cur_level = FIRST_LEVEL_NAME

    data = {"level": cur_level, "master volume": controller.master_volume, "keyboard layout": controller.active_keyboard_layout, "gamepad layout": controller.active_gamepad_layout, "is fullscreen": pygame.display.is_fullscreen(), "difficulty": controller.difficulty, "selected sprite": controller.player_sprite_selected, "player abilities": controller.player_abilities, "force grayscale": controller.force_grayscale}
    with open(profile_file, "wb") as f:
        pickle.dump(data, f)


def load_player_profile(controller):
    profile_file = join(GAME_DATA_FOLDER, "profile.p")
    if isfile(profile_file):
        with open(profile_file, "rb") as f:
            data = pickle.load(f)
        if data.get("master volume") is not None:
            controller.master_volume = data["master volume"]
        if data.get("keyboard layout") is not None:
            controller.set_keyboard_layout(data["keyboard layout"])
        if data.get("difficulty") is not None:
            controller.difficulty = data["difficulty"]
        if data.get("selected sprite") is not None:
            controller.player_sprite_selected = data["selected sprite"]
        if data.get("player abilities") is not None:
            controller.player_abilities = data["player abilities"]
        if data.get("force grayscale") is not None:
            controller.force_grayscale = controller.has_dlc.get("gumshoe") is not None and controller.has_dlc["gumshoe"] and data["force grayscale"]
        if data.get("is fullscreen") is not None and not data["is fullscreen"]:
            pygame.display.toggle_fullscreen()
        if data.get("level") is not None:
            return data["level"]
        else:
            return []
    else:
        return []


def save(level, hud):
    if level is None:
        return
    else:
        if hud is not None:
            hud.save_icon_timer = 1.0

        data = {"level": level.name, "time": level.time}
        for ent in [level.get_player()] + level.get_entities() + level.objectives_collected:
            ent_data = ent.save()
            if ent_data is not None:
                data.update(ent_data)
        with open(join(GAME_DATA_FOLDER, "save.p"), "wb") as f:
            pickle.dump(data, f)


def load_part1():
    save_file = join(GAME_DATA_FOLDER, "save.p")
    if not isfile(save_file):
        return None
    else:
        with open(save_file, "rb") as f:
            data = pickle.load(f)
        if data is None:
            return None
        else:
            return data


def load_part2(data, level):
    if data is None or level is None:
        return False
    else:
        level.time = (0 if data.get("time") is None else data["time"])
        for ent in [level.get_player()] + level.get_entities():
            ent_data = data.get(ent.name)
            if ent_data is not None:
                if hasattr(ent, "has_fired") and ent.has_fired:
                    level.queue_purge(ent)
                else:
                    ent.load(ent_data)
            elif isinstance(ent, Actor) or isinstance(ent, BreakableBlock):
                level.queue_purge(ent)
        level.purge()
        return True
