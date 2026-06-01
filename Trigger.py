from __future__ import annotations
from typing import Any, TYPE_CHECKING
import time
import pygame

from Block import (
    Block,
    Hazard,
)
from Entity import Entity
from Helpers import (
    ASSETS_FOLDER,
    display_text,
    handle_exception,
    load_text_from_file,
    set_property,
)

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class Trigger(Entity):
    def __init__(
            self:       Trigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "Trigger",
    ) -> None:
        """Initialize a trigger region and load its configured input value."""
        super().__init__(
            level,
            controller,
            x,
            y,
            width,
            height,
            name = name,
        )
        self.fire_once = fire_once
        self.has_fired = False
        self.value     = self.__load_input__(value)

    def save(
            self: Trigger,
    ) -> dict[str, dict[str, bool]] | None:
        """Return the trigger's fired state, or None if it has not fired."""
        return {self.name: {"has_fired": self.has_fired}} if self.has_fired else None

    def load(
            self: Trigger,
            info: dict[str, Any],
    ) -> None:
        """Restore the trigger's fired state from saved data."""
        self.has_fired = info["has_fired"]
        return None

    @staticmethod
    def __unpack_input__(
            value: dict,
    ) -> tuple[Any, Any]:
        """Split a packed input dict into its reference and input components."""
        return value["ref"], value["input"]

    def __load_input__(
            self:  Trigger,
            value: Any,
    ) -> Any:
        """Process and return the trigger's raw input value (identity by default)."""
        return value

    def collide(
            self: Trigger,
            ent:  Entity | None,
    ) -> float:
        """Handle the player entering the trigger (no-op for the base trigger)."""
        return 0.0

    def draw(
            self:          Trigger,
            win:           pygame.Surface,
            offset_x:      float,
            offset_y:      float,
            master_volume: dict,
    ) -> None:
        """Triggers are invisible and draw nothing."""
        return None


class AchievementTrigger(Trigger):
    def __init__(
            self:       AchievementTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "AchievementTrigger",
    ) -> None:
        """Initialize a trigger that unlocks a Steam achievement when fired."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: AchievementTrigger,
            ent:  Entity | None,
    ) -> float:
        """Unlock the configured achievement, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if self.controller.steamworks and not self.controller.steamworks.UserStats.GetAchievement(self.value):
                self.controller.steamworks.UserStats.SetAchievement(self.value)
                self.controller.should_store_steam_stats = True
            return time.perf_counter() - start


class CameraToPlayerTrigger(Trigger):
    def __init__(
            self:       CameraToPlayerTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "CameraToPlayerTrigger",
    ) -> None:
        """Initialize a trigger that returns the camera to the player."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: CameraToPlayerTrigger,
            ent:  Entity | None,
    ) -> float:
        """Clear any scroll-to-point target, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            self.controller.should_scroll_to_point = None
            return time.perf_counter() - start


class CameraToPointTrigger(Trigger):
    def __init__(
            self:       CameraToPointTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "CameraToPointTrigger",
    ) -> None:
        """Initialize a trigger that scrolls the camera to a fixed point."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  CameraToPointTrigger,
            value: dict,
    ) -> dict[str, Any]:
        """Resolve the target coordinates (in pixels) and dwell time from the packed input."""
        block_size, input_unpacked = self.__unpack_input__(value)
        txt = input_unpacked["coords"].split(" ")
        return {"coords": (int(txt[0]) * block_size, int(txt[1]) * block_size), "time": (0.0 if input_unpacked.get("time") is None else input_unpacked["time"])}

    def collide(
            self: CameraToPointTrigger,
            ent:  Entity | None,
    ) -> float:
        """Set the camera scroll-to-point target, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            self.controller.should_scroll_to_point = self.value
            return time.perf_counter() - start


class ChangeLevelTrigger(Trigger):
    def __init__(
            self:       ChangeLevelTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "ChangeLevelTrigger",
    ) -> None:
        """Initialize a trigger that advances to another level."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: ChangeLevelTrigger,
            ent:  Entity | None,
    ) -> float:
        """Queue the next level, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if isinstance(self.value, str):
                self.controller.next_level = self.value.upper()
            return time.perf_counter() - start


class CinematicTrigger(Trigger):
    def __init__(
            self:       CinematicTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "CinematicTrigger",
    ) -> None:
        """Initialize a trigger that queues a cinematic."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: CinematicTrigger,
            ent:  Entity | None,
    ) -> float:
        """Queue the configured cinematic, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if self.level.cinematics and self.level.cinematics.get(self.value):
                self.level.cinematics.queue(self.value)
            return time.perf_counter() - start


class DiscordStatusTrigger(Trigger):
    def __init__(
            self:       DiscordStatusTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "DiscordStatusTrigger",
    ) -> None:
        """Initialize a trigger that updates the Discord rich-presence status."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  DiscordStatusTrigger,
            value: dict,
    ) -> dict[str, str]:
        """Resolve the Discord state and details strings from the input."""
        return {"state": value.get("state", ""), "details": value.get("details", "")}

    def collide(
            self: DiscordStatusTrigger,
            ent:  Entity | None,
    ) -> float:
        """Push the configured status to Discord, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if isinstance(self.value, dict) and self.controller.discord:
                self.controller.discord.set_status(details = self.value["details"], state = self.value["state"])
            return time.perf_counter() - start


class ObjectiveTrigger(Trigger):
    def __init__(
            self:       ObjectiveTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "ObjectiveTrigger",
    ) -> None:
        """Initialize a trigger that activates or deactivates an objective."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  ObjectiveTrigger,
            value: dict,
    ) -> dict[str, str | bool]:
        """Resolve the objective target name and active flag from the input."""
        return {"target": value["target"], "value": value["value"]}

    def collide(
            self: ObjectiveTrigger,
            ent:  Entity | None,
    ) -> float:
        """Apply the objective activation, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if self.value and isinstance(self.value, dict) and isinstance(self.value["target"], str) and isinstance(self.value["value"], bool):
                self.controller.activate_objective(self.value["target"], self.value["value"])
            return time.perf_counter() - start


class PropertyTrigger(Trigger):
    def __init__(
            self:       PropertyTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "PropertyTrigger",
    ) -> None:
        """Initialize a trigger that sets a property on matching entities."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: PropertyTrigger,
            ent:  Entity | None,
    ) -> float:
        """Apply the configured property change, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            set_property(self, self.value)
            return time.perf_counter() - start


class RevertTrigger(Trigger):
    def __init__(
            self:       RevertTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "RevertTrigger",
    ) -> None:
        """Initialize a trigger that reverts the player to their last cached state."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: RevertTrigger,
            ent:  Entity | None,
    ) -> float:
        """Revert the player, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            self.level.player.revert()
            return time.perf_counter() - start


class SaveTrigger(Trigger):
    def __init__(
            self:       SaveTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "SaveTrigger",
    ) -> None:
        """Initialize a trigger that saves the game when fired."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: SaveTrigger,
            ent:  Entity | None,
    ) -> float:
        """Save the game and player profile, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            self.controller.save()
            self.controller.save_player_profile()
            return time.perf_counter() - start


class SoundTrigger(Trigger):
    def __init__(
            self:       SoundTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "SoundTrigger",
    ) -> None:
        """Initialize a trigger that plays a sound effect when fired."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  SoundTrigger,
            value: str,
    ) -> pygame.mixer.Sound | None:
        """Load the trigger's sound file, or None if it is missing or not audio."""
        path = ASSETS_FOLDER / "SoundEffects" / "triggers" / value
        if not path.is_file() or len(value) < 4 or (value[-4:] != ".wav" and value[-4:] != ".mp3"):
            return None
        else:
            return pygame.mixer.Sound(path)

    def collide(
            self: SoundTrigger,
            ent:  Entity | None,
    ) -> float:
        """Play the configured sound, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if self.value is not None and isinstance(self.value, pygame.mixer.Sound):
                pygame.mixer.find_channel(force = True).play(self.value)
            return time.perf_counter() - start


class SpawnTrigger(Trigger):
    def __init__(
            self:       SpawnTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "SpawnTrigger",
    ) -> None:
        """Initialize a trigger that spawns a new entity when fired."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  SpawnTrigger,
            value: dict,
    ) -> Entity | None:
        """Construct (but do not yet add) the entity this trigger will spawn from the object dict."""
        # Deferred import breaks the EntityFactory <-> Trigger module cycle: by the time a
        # trigger actually fires, EntityFactory is fully initialized.
        from EntityFactory import build_entity
        refs, input_unpacked = self.__unpack_input__(value)
        objects_dict   = refs["objects_dict"]
        sprite_master  = refs["sprite_master"]
        enemy_audios   = refs["enemy_audios"]
        block_audios   = refs["block_audios"]
        message_audios = refs["message_audios"]
        image_master   = refs["image_master"]
        block_size     = refs["block_size"]
        element        = input_unpacked["name"]
        if len(element) > 0 and objects_dict.get(element) is not None:
            j, i  = tuple(map(int, input_unpacked["coords"].split(" ")))
            entry = objects_dict[element]
            data  = entry["data"]
            return build_entity(entry["type"].upper(), data, element, self.level, self.controller, i, j, block_size, objects_dict, sprite_master, image_master, enemy_audios, block_audios, message_audios, is_stacked=False)
        return None

    def collide(
            self: SpawnTrigger,
            ent:  Entity | None,
    ) -> float:
        """Add the prepared spawn entity to the appropriate level list, returning the frame-time offset."""
        # Deferred import: NonPlayer pulls in Actor -> Objective -> Trigger, and Objective pulls in Trigger, so
        # importing them at module load would cause a circular import. It is only needed for this isinstance check.
        from NonPlayer import NonPlayer
        from Objective import Objective
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
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
                elif isinstance(self.value, Objective):
                    self.level.objectives.append(self.value)
            return time.perf_counter() - start


class SwapLevelTrigger(Trigger):
    def __init__(
            self:       SwapLevelTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "SwapLevelTrigger",
    ) -> None:
        """Initialize a trigger that hot-swaps to the level's linked hot-swap level."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def collide(
            self: SwapLevelTrigger,
            ent:  Entity | None,
    ) -> float:
        """Request a hot-swap of the level, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            self.controller.should_hot_swap_level = True
            return time.perf_counter() - start


class TextTrigger(Trigger):
    def __init__(
            self:       TextTrigger,
            level:      Level,
            controller: Controller,
            x:          float,
            y:          float,
            width:      float,
            height:     float,
            value:      Any,
            fire_once:  bool = True,
            name:       str  = "TextTrigger",
    ) -> None:
        """Initialize a trigger that displays a block of text (with optional audio)."""
        super().__init__(level, controller, x, y, width, height, value, fire_once = fire_once, name = name)

    def __load_input__(
            self:  TextTrigger,
            value: dict,
    ) -> dict[str, Any | None] | None:
        """Resolve the text lines, type-out flag, and optional audio from the packed input."""
        message_audios, input_unpacked = self.__unpack_input__(value)
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

    def collide(
            self: TextTrigger,
            ent:  Entity | None,
    ) -> float:
        """Display the configured text, returning the frame-time offset."""
        if self.fire_once and self.has_fired:
            return 0.0
        else:
            start          = time.perf_counter()
            self.has_fired = True
            if isinstance(self.value, dict):
                display_text(
                    self.value["text"],
                    self.controller,
                    audio            = self.value["audio"],
                    should_type_text = self.value["should_type"],
                    retro            = self.level.retro,
                )
            return time.perf_counter() - start
