import pygame
import pickle
from os.path import isfile
from Actor import Actor
from Block import BreakableBlock


def save_player_profile(controller, level=None):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
    else:
        data = None

    if level is None:
        if data is not None and data.get("level") is not None:
            cur_level = data["level"]
        else:
            cur_level = "__START__"
    else:
        cur_level = level.name

    data = {"level": cur_level, "master volume": controller.master_volume, "keyboard layout": controller.active_keyboard_layout, "gamepad layout": controller.active_gamepad_layout, "is fullscreen": pygame.display.is_fullscreen(), "difficulty": controller.difficulty, "selected sprite": controller.player_sprite_selected, "player abilities": controller.player_abilities}
    pickle.dump(data, open("GameData/profile.p", "wb"))


def load_player_profile(controller):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
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
    if hud is not None:
        hud.save_icon_timer = 1.0

    data = {"level": level.name, "time": level.time}
    for obj in [level.get_player()] + level.get_objects() + level.objectives_collected:
        obj_data = obj.save()
        if obj_data is not None:
            data.update(obj_data)
    pickle.dump(data, open("GameData/save.p", "wb"))


def load_part1():
    if not isfile("GameData/save.p"):
        return None
    else:
        data = pickle.load(open("GameData/save.p", "rb"))
        if data is None:
            return None
        else:
            return data


def load_part2(data, level):
    if data is None or level is None:
        return False
    else:
        level.time = (0 if data.get("time") is None else data["time"])
        for obj in [level.get_player()] + level.get_objects():
            obj_data = data.get(obj.name)
            if obj_data is not None:
                if hasattr(obj, "has_fired") and obj.has_fired:
                    level.queue_purge(obj)
                else:
                    obj.load(obj_data)
            elif isinstance(obj, Actor) or isinstance(obj, BreakableBlock):
                level.queue_purge(obj)
        level.purge()
        return True
