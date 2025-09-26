import pygame
import pickle
from os.path import join, isfile
from Actor import Actor
from Block import BreakableBlock
from Helpers import GAME_DATA_FOLDER, FIRST_LEVEL_NAME


def save_player_profile(controller, level):
    profile_file = join(GAME_DATA_FOLDER, "profile.p")
    if isfile(profile_file):
        data = pickle.load(open(profile_file, "rb"))
    else:
        data = None

    if level is None:
        if data is not None and data.get("level") is not None:
            cur_level = data["level"]
        else:
            cur_level = FIRST_LEVEL_NAME
    else:
        cur_level = level.name

    data = {"level": cur_level, "master volume": controller.master_volume, "keyboard layout": controller.active_keyboard_layout, "gamepad layout": controller.active_gamepad_layout, "is fullscreen": pygame.display.is_fullscreen(), "difficulty": controller.difficulty, "selected sprite": controller.player_sprite_selected, "player abilities": controller.player_abilities}
    pickle.dump(data, open(profile_file, "wb"))


def load_player_profile(controller):
    profile_file = join(GAME_DATA_FOLDER, "profile.p")
    if isfile(profile_file):
        data = pickle.load(open(profile_file, "rb"))
        controller.master_volume = data["master volume"]
        controller.set_keyboard_layout(data["keyboard layout"])
        controller.difficulty = data["difficulty"]
        controller.player_sprite_selected = data["selected sprite"]
        controller.player_abilities = data["player abilities"]
        if not data["is fullscreen"]:
            pygame.display.toggle_fullscreen()
        return data["level"]
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
        save_file = join(GAME_DATA_FOLDER, "save.p")
        pickle.dump(data, open(save_file, "wb"))


def load_part1():
    save_file = join(GAME_DATA_FOLDER, "save.p")
    if not isfile(save_file):
        return None
    else:
        data = pickle.load(open(save_file, "rb"))
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
