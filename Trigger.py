import time
import pygame
from os.path import join, isfile
from Helpers import display_text, load_text_from_file, load_path, set_property, ASSETS_FOLDER, handle_exception
from Entity import Entity
from Block import Block, BreakableBlock, MovableBlock, Hazard, MovingBlock, MovingHazard, Door, FallingHazard
from Objective import Objective
from NonPlayer import NonPlayer
from Boss import Boss

class Trigger(Entity):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="Trigger"):
        super().__init__(level, controller, x, y, width, height, name=name)
        self.fire_once = fire_once
        self.has_fired = False
        self.value = self.__load_input__(input)

    def save(self) -> dict | None:
        if self.has_fired:
            return {self.name: {"has_fired": self.has_fired}}
        else:
            return None

    def load(self, ent) -> None:
        self.has_fired = ent["has_fired"]

    @staticmethod
    def __unpack_input__(input: dict) -> tuple:
        return input['ref'], input['input']

    def __load_input__(self, input):
        return input

    def collide(self, ent: Entity | None) -> float:
        return 0.0

    def draw(self, win, offset_x, offset_y, master_volume) -> None:
        pass

class TextTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="TextTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> dict[str, list | None] | None:
        message_audios, input_unpacked = self.__unpack_input__(input)
        audio = None
        if input_unpacked.get("audio") is not None:
            if message_audios.get(input_unpacked["audio"]) is None:
                handle_exception(f'Audio file {input_unpacked["audio"]} not found.')
                return None
            else:
                audio = message_audios.get(input_unpacked["audio"])
        if input_unpacked.get("type") is None:
            should_type = True
        else:
            should_type = input_unpacked["type"]
        text = load_text_from_file(input_unpacked["file"])
        return {"text": text, "should_type": should_type, "audio": audio}

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            display_text(self.value["text"], self.controller, audio=self.value["audio"], should_type_text=self.value["should_type"], retro=self.level.retro)
            return time.perf_counter() - start

class SoundTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="SoundTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> pygame.mixer.Sound | None:
        path = join(ASSETS_FOLDER, "SoundEffects", "triggers", input)
        if not isfile(path) or len(input) < 4 or (input[-4:] != ".wav" and input[-4:] != ".mp3"):
            return None
        else:
            return pygame.mixer.Sound(path)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            if self.value is not None:
                pygame.mixer.find_channel(force=True).play(self.value)
            return time.perf_counter() - start

class SpawnTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="SpawnTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> Entity | None:
        refs, input_unpacked = self.__unpack_input__(input)
        objects_dict = refs['objects_dict']
        sprite_master = refs['sprite_master']
        enemy_audios = refs['enemy_audios']
        block_audios = refs['block_audios']
        message_audios = refs['message_audios']
        image_master = refs['image_master']
        block_size = refs['block_size']
        element = input_unpacked["name"]
        if len(element) > 0 and objects_dict.get(element) is not None:
            j, i = tuple(map(int, input_unpacked["coords"].split(' ')))
            entry = objects_dict[element]
            data = entry["data"]

            def __convert_coords__(coord: int) -> int:
                actual_size = block_size // 2
                if coord < actual_size:
                    return coord * actual_size
                else:
                    return coord

            match entry["type"].upper():
                case "OBJECTIVE":
                    return Objective(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, sprite_master, block_audios, is_active=(False if data.get("is_active") is None else data["is_active"]), sprite=(None if data.get("sprite") is None else data["sprite"]), sound=("objective" if data.get("sound") is None else data["sound"].lower()), text=(None if data.get("text") is None else data["text"]), trigger=(None if data.get("trigger") is None else data["trigger"]), is_blocking=(False if data.get("is_blocking") is None else data["is_blocking"]), achievement=(None if data.get("achievement") is None else data["achievement"]), name=(element if data.get("name") is None else data["name"]))
                case "BLOCK":
                    is_stacked = False
                    return Block(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=(True if data.get("is_blocking") is None else data["is_blocking"]), name=(element if data.get("name") is None else data["name"]))
                case "BREAKABLEBLOCK":
                    is_stacked = False
                    return BreakableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), coord_x2=__convert_coords__(data["coord_x2"]), coord_y2=__convert_coords__(data["coord_y2"]), name=(element if data.get("name") is None else data["name"]))
                case "MOVINGBLOCK":
                    if data["path"] is None:
                        path = None
                    else:
                        path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                    is_stacked = False
                    return MovingBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, is_enabled=(True if data.get("is_enabled") is None else data["is_enabled"]), hold_for_collision=(False if data.get("hold_for_collision") is None else data["hold_for_collision"]), speed=data["speed"], path=path, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), is_blocking=(True if data.get("is_blocking") is None else data["is_blocking"]), name=(element if data.get("name") is None else data["name"]))
                case "DOOR":
                    is_stacked = False
                    return Door(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, speed=data["speed"], direction=data["direction"], is_locked=(False if data.get("is_locked") is None else data["is_locked"]), coord_x=(0 if data.get("coord_x") is None else __convert_coords__(data["coord_x"])), coord_y=(0 if data.get("coord_y") is None else __convert_coords__(data["coord_y"])), locked_coord_x=(None if data.get("locked_coord_x") is None else __convert_coords__(data["locked_coord_x"])), locked_coord_y=(None if data.get("locked_coord_y") is None else __convert_coords__(data["locked_coord_y"])), unlocked_coord_x=(None if data.get("unlocked_coord_x") is None else __convert_coords__(data["unlocked_coord_x"])), unlocked_coord_y=(None if data.get("unlocked_coord_y") is None else __convert_coords__(data["unlocked_coord_y"])), name=(element if data.get("name") is None else data["name"]))
                case "MOVABLEBLOCK":
                    is_stacked = False
                    return MovableBlock(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, block_audios, is_stacked, coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]))
                case "HAZARD":
                    return Hazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                case "MOVINGHAZARD":
                    if data["path"] is None:
                        path = None
                    else:
                        path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                    is_stacked = False
                    return MovingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, is_stacked, speed=data["speed"], path=path, hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                case "FALLINGHAZARD":
                    return FallingHazard(self.level, self.controller, j * block_size, i * block_size, block_size, block_size, image_master, sprite_master, block_audios, self.controller.difficulty, drop_x=data["drop_x"] * block_size, drop_y=data["drop_y"] * block_size, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), hit_sides=("UDLR" if data.get("hit_sides") is None else data["hit_sides"].upper()), sprite=data["sprite"], coord_x=__convert_coords__(data["coord_x"]), coord_y=__convert_coords__(data["coord_y"]), name=(element if data.get("name") is None else data["name"]))
                case "ENEMY":
                    if data["path"] is None:
                        path = None
                    else:
                        path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                    return NonPlayer(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, path=path, kill_at_end=(False if data.get("kill_at_end") is None else data["kill_at_end"]), is_hostile=(True if data.get("is_hostile") is None else data["is_hostile"]), collision_message=(None if data.get("collision_message") is None else data["collision_message"]), bark=(None if data.get("bark") is None else data["bark"]), hp=data["hp"], can_shoot=(False if data.get("can_shoot") is None else data["can_shoot"]), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"]))
                case "BOSS":
                    if data["path"] is None:
                        path = None
                    else:
                        path = load_path([int(i) for i in data["path"].split(' ')], i, j, block_size)
                    return Boss(self.level, self.controller, j * block_size, i * block_size, sprite_master, enemy_audios, self.controller.difficulty, block_size, music=(None if data.get("music") is None else data["music"]), trigger=(None if data.get("trigger") is None else data["trigger"]), path=path, hp=data["hp"], show_health_bar=(True if data.get("show_health_bar") is None else data["show_health_bar"]), can_shoot=(False if data.get("can_shoot") is None else data["can_shoot"]), sprite=data["sprite"], proj_sprite=(None if data.get("proj_sprite") is None else data["proj_sprite"]), name=(element if data.get("name") is None else data["name"]))
                case "TRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return Trigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "TEXTTRIGGER":
                    packed_input = {'ref': message_audios, 'input': (None if data.get("input") is None else data["input"])}
                    return TextTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "SOUNDTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return SoundTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "SPAWNTRIGGER":
                    all_refs = {'objects_dict': objects_dict, 'sprite_master': sprite_master, 'enemy_audios': enemy_audios, 'block_audios': block_audios, 'message_audios': message_audios, 'image_master': image_master, 'block_size': block_size}
                    packed_input = {'ref': all_refs, 'input': (None if data.get("input") is None else data["input"])}
                    return SpawnTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "REVERTTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return RevertTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "SAVETRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return SaveTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "CHANGELEVELTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return ChangeLevelTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "PROPERTYTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return PropertyTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "CINEMATICTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return CinematicTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "ACHIEVEMENTTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return AchievementTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "OBJECTIVETRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return ObjectiveTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "SWAPLEVELTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return SwapLevelTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "CAMERATOPOINTTRIGGER":
                    packed_input = {'ref': block_size, 'input': (None if data.get("input") is None else data["input"])}
                    return CameraToPointTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "CAMERATOPLAYERTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return CameraToPlayerTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case "DISCORDSTATUSTRIGGER":
                    packed_input = (None if data.get("input") is None else data["input"])
                    return DiscordStatusTrigger(self.level, self.controller, j * block_size, (i - (data["height"] - 1)) * block_size, data["width"] * block_size, data["height"] * block_size, packed_input, fire_once=(True if data.get("fire_once") is None else data["fire_once"]), name=(element if data.get("name") is None else data["name"]))
                case _:
                    pass
        return None

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            if self.value is not None:
                if isinstance(self.value, Trigger):
                    self.level.triggers.append(self.value)
                elif isinstance(self.value, NonPlayer):
                    self.level.enemies.append(self.value)
                elif isinstance(self.value, Hazard):
                    self.level.hazards.append(self.value)
                elif isinstance(self.value, Block):
                    self.level.blocks.append(self.value)
            return time.perf_counter() - start

class RevertTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="RevertTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.level.player.revert()
            return time.perf_counter() - start

class SaveTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="SaveTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.level.player.save()
            return time.perf_counter() - start

class ChangeLevelTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="ChangeLevelTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.controller.next_level = self.value.upper()
            return time.perf_counter() - start

class PropertyTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="PropertyTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            set_property(self, self.value)
            return time.perf_counter() - start

class CinematicTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="CinematicTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            if self.level.cinematics is not None and self.level.cinematics.get(self.value) is not None:
                self.level.cinematics.queue(self.value)
            return time.perf_counter() - start

class AchievementTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="AchievementTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            if self.controller.steamworks is not None and not self.controller.steamworks.UserStats.GetAchievement(self.value):
                self.controller.steamworks.UserStats.SetAchievement(self.value)
                self.controller.should_store_steam_stats = True
            return time.perf_counter() - start

class ObjectiveTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="ObjectiveTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> dict[str, str | bool]:
        return {"target": input["target"], "value": input["value"]}

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            text = None
            for objective in self.level.objectives:
                if self.value["target"] == objective.name:
                    objective.is_active = self.value["value"]
                    if text is None and objective.text is not None:
                        text = objective.text
            self.controller.activate_objective(text)
            return time.perf_counter() - start

class SwapLevelTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="SwapLevelTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.controller.should_hot_swap_level = True
            return time.perf_counter() - start

class CameraToPointTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="CameraToPointTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> dict[str, int | float]:
        block_size, input_unpacked = self.__unpack_input__(input)
        txt = input_unpacked["coords"].split(' ')
        return {"coords": (int(txt[0]) * block_size, int(txt[1]) * block_size), "time": (0.0 if input_unpacked.get("time") is None else input_unpacked["time"])}

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.controller.should_scroll_to_point = self.value
            return time.perf_counter() - start

class CameraToPlayerTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="CameraToPlayerTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.controller.should_scroll_to_point = None
            return time.perf_counter() - start

class DiscordStatusTrigger(Trigger):
    def __init__(self, level, controller, x, y, width, height, input, fire_once=True, name="DiscordStatusTrigger"):
        super().__init__(level, controller, x, y, width, height, input, fire_once=fire_once, name=name)

    def __load_input__(self, input) -> dict[str, str]:
        return {"state": "" if input.get("state") is None else input["state"], "details": "" if input.get("details") is None else input["details"]}

    def collide(self, ent: Entity | None) -> float:
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start = time.perf_counter()
            self.has_fired = True
            self.controller.discord.set_status(details=self.value["details"], state=self.value["state"])
            return time.perf_counter() - start
