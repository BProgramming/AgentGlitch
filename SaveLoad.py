from __future__ import annotations
from typing import TYPE_CHECKING
import pygame
import pickle

from Helpers import GAME_DATA_FOLDER

if TYPE_CHECKING:
    from Controller import Controller
    from HUD import HUD
    from Level import Level


def save_player_profile(
        controller: Controller,
        level:      Level | None,
) -> None:
    """Persist the player's profile (settings and current level) to disk."""
    profile_file = GAME_DATA_FOLDER / "profile.p"

    if level is not None:
        cur_level = level.name
    else:
        cur_level = controller.start_level
        if profile_file.is_file():
            with open(profile_file, "rb") as f:
                data = pickle.load(f)
            if data is not None and data.get("level") is not None:
                cur_level = data["level"]

    data = {
        "level":           cur_level,
        "master volume":   controller.master_volume,
        "keyboard layout": controller.active_keyboard_layout,
        "gamepad layout":  controller.active_gamepad_layout,
        "is fullscreen":   pygame.display.is_fullscreen(),
        "difficulty":      controller.difficulty,
        "selected sprite": controller.player_sprite_selected,
        "force retro":     controller.force_retro,
    }
    with open(profile_file, "wb") as f:
        pickle.dump(data, f)
    return None


def load_player_profile(
        controller: Controller,
) -> str:
    """Load the player's profile from disk, apply its settings, and return the saved level name."""
    profile_file = GAME_DATA_FOLDER / "profile.p"
    if profile_file.is_file():
        with open(profile_file, "rb") as f:
            data = pickle.load(f)
        if data.get("master volume"):
            controller.master_volume = data["master volume"]
        if data.get("keyboard layout"):
            controller.set_keyboard_layout(data["keyboard layout"])
        if data.get("difficulty"):
            controller.difficulty = data["difficulty"]
        if data.get("selected sprite"):
            controller.player_sprite_selected = data["selected sprite"]
        if data.get("force retro"):
            controller.force_retro = (
                controller.has_dlc.get("gumshoe") is not None
                and controller.has_dlc["gumshoe"]
                and data["force retro"]
            )
        if data.get("is fullscreen") and not data["is fullscreen"]:
            pygame.display.toggle_fullscreen()
        if data.get("level"):
            return data["level"]
        else:
            return ""
    else:
        return ""


def save(
        level:      Level | None,
        hud:        HUD | None,
        controller: Controller,
) -> None:
    """Serialize the current level state and all entities to the save file."""
    if level is None:
        return None

    if hud is not None:
        hud.save_icon_timer = 1.0

    data = {"level": level.name, "time": level.time, "objective": controller.active_objective}
    for ent in level.entities + level.objectives_collected:
        ent_data = ent.save()
        if ent_data is not None:
            data.update(ent_data)

    save_file = GAME_DATA_FOLDER / "save.p"
    with open(save_file, "wb") as f:
        pickle.dump(data, f)
    return None


def load_part1() -> dict | None:
    """Load and return the raw save-file data, or None if there is no valid save."""
    save_file = GAME_DATA_FOLDER / "save.p"
    if save_file.is_file():
        with open(save_file, "rb") as f:
            data = pickle.load(f)
        if data is None:
            return None
        else:
            return data
    else:
        return None


def load_part2(
        data:       dict | None,
        level:      Level | None,
        controller: Controller,
) -> bool:
    """Apply saved data to a built level, restoring or purging entities, and report success."""
    if data is None or level is None:
        return False
    else:
        level.time                  = 0 if data.get("time") is None else data["time"]
        controller.active_objective = None if data.get("objective") is None else data["objective"]
        for ent in level.entities:
            ent_data = data.get(ent.name)
            if ent_data is not None:
                if hasattr(ent, "has_fired") and ent.has_fired:
                    level.queue_purge(ent)
                else:
                    ent.load(ent_data)
            elif ent.purgeable_on_load:
                level.queue_purge(ent)
        level.purge()
        return True
