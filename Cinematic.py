from __future__ import annotations
from typing import Any, TYPE_CHECKING
import cv2
import pygame
import time
from enum import Enum
from pathlib import Path
from Helpers import (
    glitch,
    handle_exception,
    ASSETS_FOLDER,
    image_to_retro,
    NORMAL_WHITE,
    RETRO_WHITE,
    RETRO_BLACK,
    NORMAL_BLACK,
)

if TYPE_CHECKING:
    from Controller import Controller


class CinematicType(Enum):
    SLIDE = 1
    VIDEO = 2


class CinematicsManager:
    def __init__(
            self:           CinematicsManager,
            files:          dict[str, str] | list[dict[str, str]] | tuple[dict[str, str]],
            controller:     Controller,
            player_sprites: dict[str, list[pygame.Surface]] | None = None,
    ) -> None:
        """Initialize the manager and load all provided cinematic definitions."""
        self.cinematics = {}
        self.queued     = []
        self.load(files, controller, player_sprites)

    def load(
            self:           CinematicsManager,
            files:          dict[str, Any] | list[dict[str, Any]] | tuple[dict[str, Any]],
            controller:     Controller,
            player_sprites: dict[str, list[pygame.Surface]] | None,
    ) -> None:
        """Load slide and video cinematics from their definitions into the manager."""
        if type(files) not in [list, tuple]:
            files = [files]
        for file in files:
            if isinstance(file, dict) and file["file"] is not None:
                path = ASSETS_FOLDER / "Cinematics" / file["file"]
                if path.is_file():
                    if file["type"].upper() == "SLIDE":
                        self.cinematics[file["name"]] = Cinematic(
                            self.__load_slide__(path),
                            CinematicType.SLIDE,
                            controller,
                            player_sprites,
                            player_blit       = file.get("player_blit"),
                            pause_key         = file.get("pause_key"),
                            text              = file.get("text"),
                            should_glitch     = file.get("should_glitch", False),
                            should_fade_in    = file.get("should_fade_in", True),
                            should_fade_out   = file.get("should_fade_out", True),
                            can_scale_up      = file.get("can_scale_up", True),
                            can_scale_down    = file.get("can_scale_down", True),
                            stretch           = file.get("stretch", False),
                            delete_after_play = file.get("delete", False),
                        )
                    elif file["type"].upper() == "VIDEO":
                        self.cinematics[file["name"]] = Cinematic(
                            self.__load_video__(path),
                            CinematicType.VIDEO,
                            controller,
                            player_sprites,
                            player_blit       = None,
                            pause_key         = file.get("pause_key"),
                            text              = file.get("text"),
                            should_glitch     = file.get("should_glitch", False),
                            should_fade_in    = file.get("should_fade_in", True),
                            should_fade_out   = file.get("should_fade_out", True),
                            can_scale_up      = file.get("can_scale_up", True),
                            can_scale_down    = file.get("can_scale_down", True),
                            stretch           = file.get("stretch", False),
                            delete_after_play = file.get("delete", False),
                        )
                else:
                    handle_exception(f"File {FileNotFoundError(path.resolve())} not found.")
        return None

    @staticmethod
    def __load_slide__(
            file: Path,
    ) -> pygame.Surface:
        """Load a slide image from disk."""
        return pygame.image.load(file)

    @staticmethod
    def __load_video__(
            file: Path,
    ) -> cv2.VideoCapture:
        """Open a video file for playback via OpenCV."""
        return cv2.VideoCapture(str(file))

    def clear_queue(
            self: CinematicsManager,
    ) -> None:
        """Clear the queue of pending cinematics."""
        self.queued = []
        return None

    def queue(
            self: CinematicsManager,
            name: str,
    ) -> None:
        """Queue a named cinematic for later playback."""
        self.queued.append(name)
        return None

    def play(
            self: CinematicsManager,
            name: str,
            win:  pygame.Surface,
    ) -> float:
        """Play a named cinematic, deleting it afterward if flagged, and return its duration."""
        if self.cinematics.get(name) is not None:
            cinematic = self.cinematics[name]
            dtime     = cinematic.play(win)
            if cinematic.delete_after_play:
                del self.cinematics[name]
            return dtime
        else:
            return 0.0

    def play_queue(
            self: CinematicsManager,
            win:  pygame.Surface,
    ) -> float:
        """Play all queued cinematics in order and return their total duration."""
        dtime = 0.0
        for name in self.queued:
            dtime += self.play(name, win)
        self.queued = []
        return dtime


class Cinematic:
    def __init__(
            self:              Cinematic,
            ent:               pygame.Surface | cv2.VideoCapture,
            cinematic_type:    CinematicType,
            controller:        Controller,
            player_sprites:    dict[str, list[pygame.Surface]] | None,
            player_blit:       list[dict[str, str | int | list[int]]] | None = None,
            pause_key:         str | list[str] | tuple[str] | None           = None,
            text:              str | None                                    = None,
            should_glitch:     bool                                          = False,
            should_fade_in:    bool                                          = True,
            should_fade_out:   bool                                          = True,
            can_scale_up:      bool                                          = True,
            can_scale_down:    bool                                          = True,
            stretch:           bool                                          = False,
            delete_after_play: bool                                          = True,
    ) -> None:
        """Initialize a single cinematic, blitting any player sprites onto slide images."""
        self.controller = controller
        self.type       = cinematic_type
        self.cinematic  = ent
        if isinstance(self.cinematic, pygame.Surface) and player_sprites and player_blit:  # only supported for slides, not videos
            for blit in player_blit:
                if blit.get("animation")   and isinstance(blit["animation"], str) \
                    and blit.get("facing") and isinstance(blit["facing"], str) \
                    and blit.get("frame")  and isinstance(blit["frame"], int) \
                    and blit.get("coord")  and isinstance(blit["coord"], list) \
                    and len(blit["coord"]) == 2 and isinstance(blit["coord"][0], int) and isinstance(blit["coord"][1], int): # noqa
                    anim  = f'{blit["animation"]}_{blit["facing"]}'.upper()
                    frame: int       = blit["frame"] # noqa
                    coord: list[int] = blit["coord"] # noqa
                    if coord[0] < 0:
                        coord[0] += self.cinematic.get_width()
                    if coord[1] < 0:
                        coord[1] += self.cinematic.get_height()
                    self.cinematic.blit(player_sprites[anim][frame], coord)
        self.pause_key:         str | list[str] | tuple[str] | None = pause_key
        self.text:              str | None                          = text
        self.should_glitch:     bool                                = should_glitch
        self.should_fade_in:    bool                                = should_fade_in
        self.should_fade_out:   bool                                = should_fade_out
        self.can_scale_up:      bool                                = can_scale_up
        self.can_scale_down:    bool                                = can_scale_down
        self.stretch:           bool                                = stretch
        self.delete_after_play: bool                                = delete_after_play

    def play(
            self: Cinematic,
            win:  pygame.Surface,
    ) -> float:
        """Play the cinematic (slide or video), pausing other audio, and return its duration."""
        start = time.perf_counter()
        pygame.mixer.pause()
        if self.type == CinematicType.SLIDE and isinstance(self.cinematic, pygame.Surface):
            self.__play_slide__(self.cinematic, self.controller, win, text = self.text, should_glitch = self.should_glitch, pause_key = self.pause_key, should_fade_in = self.should_fade_in, should_fade_out = self.should_fade_out, can_scale_up = self.can_scale_up, can_scale_down = self.can_scale_down, stretch = self.stretch)
        elif self.type == CinematicType.VIDEO and isinstance(self.cinematic, cv2.VideoCapture):
            self.__play_video__(self.cinematic, self.controller, win, text = self.text, should_glitch = self.should_glitch, pause_key = self.pause_key, should_fade_in = self.should_fade_in, should_fade_out = self.should_fade_out, can_scale_up = self.can_scale_up, can_scale_down = self.can_scale_down, stretch = self.stretch)
        pygame.mixer.unpause()
        return time.perf_counter() - start

    @staticmethod
    def __play_slide__(
            slide:           pygame.Surface,
            controller:      Controller,
            win:             pygame.Surface,
            text:            str | None                          = None,
            should_glitch:   bool                                = False,
            pause_key:       str | list[str] | tuple[str] | None = None,
            should_fade_in:  bool                                = True,
            should_fade_out: bool                                = True,
            can_scale_up:    bool                                = True,
            can_scale_down:  bool                                = True,
            stretch:         bool                                = False,
    ) -> None:
        """Render a slide with optional scaling, fades, text, glitch, and a pause-to-continue key."""
        scale_factor = (win.get_width() / slide.get_width(), win.get_height() / slide.get_height())
        if stretch:
            slide = pygame.transform.scale_by(slide, scale_factor)
        else:
            min_factor = min(scale_factor[0], scale_factor[1])
            if (can_scale_up and min_factor > 1) or (can_scale_down and min_factor < 1):
                slide = pygame.transform.scale_by(slide, min_factor)
        og_slide = slide

        if controller.retro:
            slide        = image_to_retro(slide)
            colour_white = RETRO_WHITE
            colour_black = RETRO_BLACK
        else:
            colour_white = NORMAL_WHITE
            colour_black = NORMAL_BLACK
        text_colour = colour_black
        for e in slide.get_at((slide.get_width() // 5, slide.get_height() // 5))[:3]:
            if e < 255 // 2:
                text_colour = colour_white
                break

        if text is not None:
            for i in range(len(text)):
                text_line = pygame.font.SysFont("courier", 32).render(text[i], True, text_colour)
                slide.blit(text_line, (slide.get_width() // 5, (slide.get_height() // 5) + (i * text_line.get_height())))

        slide_x = (win.get_width() - slide.get_width()) // 2
        slide_y = (win.get_height() - slide.get_height()) // 2

        black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
        black.fill(colour_black)

        if should_fade_in:
            for i in range(64):
                win.blit(slide, (slide_x, slide_y))
                black.set_alpha(255 - (4 * i))
                win.blit(black, (0, 0))
                pygame.display.update()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.quit()
                    elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        return None
                time.sleep(0.01)

        black.set_alpha(255)
        win.blit(black, (0, 0))

        pause_dtime = 0
        while pause_dtime < 1:
            win.blit(slide, (slide_x, slide_y))
            if should_glitch and pause_dtime > 0.75:
                for spot in glitch(0.5, win):
                    win.blit(spot[0], spot[1])
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    controller.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                    return None
            time.sleep(0.01)
            pause_dtime += 0.01

        if pause_key is not None:
            valid_keys = []
            if not isinstance(pause_key, list) and not isinstance(pause_key, tuple):
                pause_key = [pause_key]
            if isinstance(pause_key, list):
                for key in pause_key:
                    if hasattr(controller, key):
                        controller_keys = getattr(controller, key)
                        for options in controller_keys:
                            valid_keys.append(options)
            cont = False
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.quit()
                    elif (event.type == pygame.KEYDOWN and event.key in valid_keys) or ((event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN) and event.button in valid_keys):
                        cont = True
                        break
                if cont:
                    break
                time.sleep(0.01)

        if should_fade_out:
            for i in range(64):
                win.blit(slide, (slide_x, slide_y))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                if should_glitch:
                    for spot in glitch(0.5, win):
                        win.blit(spot[0], spot[1])
                pygame.display.update()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.quit()
                    elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        return None
                time.sleep(0.01)

        black.set_alpha(255)
        win.blit(black, (0, 0))

        if text is not None:
            slide.blit(og_slide, (0, 0))
        return None

    @staticmethod
    def __play_video__(
            video:           cv2.VideoCapture,
            controller:      Controller,
            win:             pygame.Surface,
            text:            str | None                          = None,
            should_glitch:   bool                                = False,
            pause_key:       str | list[str] | tuple[str] | None = None,
            should_fade_in:  bool                                = True,
            should_fade_out: bool                                = True,
            can_scale_up:    bool                                = True,
            can_scale_down:  bool                                = True,
            stretch:         bool                                = False,
    ) -> None:
        """Play a video frame-by-frame with optional scaling, fades, text, glitch, and pause key."""
        if not video.isOpened():
            raise IOError(f"Video file {str(video)} could not be opened.")
        if controller.retro:
            colour_white = RETRO_WHITE
            colour_black = RETRO_BLACK
        else:
            colour_white = NORMAL_WHITE
            colour_black = NORMAL_BLACK
        text_colour = colour_white

        ret, frame = video.read()
        if ret:
            frame_rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pygame_frame  = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

            scale_factor = (win.get_width() / pygame_frame.get_width(), win.get_height() / pygame_frame.get_height())
            min_factor = min(scale_factor[0], scale_factor[1])
            if stretch:
                pygame_frame = pygame.transform.scale_by(pygame_frame, scale_factor)
            else:
                if (can_scale_up and min_factor > 1) or (can_scale_down and min_factor < 1):
                    pygame_frame = pygame.transform.scale_by(pygame_frame, min_factor)

            pygame_frame_x = (win.get_width() - pygame_frame.get_width()) // 2
            pygame_frame_y = (win.get_height() - pygame_frame.get_height()) // 2

            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill(colour_black)

            if should_fade_in:
                for i in range(64):
                    win.blit(pygame_frame, (pygame_frame_x, pygame_frame_y))
                    black.set_alpha(255 - (4 * i))
                    win.blit(black, (0, 0))
                    pygame.display.update()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            controller.quit()
                        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                            return None
                    time.sleep(0.01)

            black.set_alpha(255)
            win.blit(black, (0, 0))

            while video.isOpened():
                win.blit(black, (0, 0))
                if text is not None:
                    for i in range(len(text)):
                        text_line = pygame.font.SysFont("courier", 32).render(text[i], True, text_colour)
                        pygame_frame.blit(text_line, (pygame_frame.get_width() // 5, (pygame_frame.get_height() // 5) + (i * text_line.get_height())))
                win.blit(pygame_frame, (pygame_frame_x, pygame_frame_y))
                pygame.display.update()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.quit()
                    elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        return None
                time.sleep(0.01)

                ret, frame = video.read()
                if ret:
                    frame_rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pygame_frame = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                    if (can_scale_up and min_factor > 1) or (can_scale_down and min_factor < 1):
                        pygame_frame = pygame.transform.scale(pygame_frame, (min_factor, min_factor))
                else:
                    break

            if pause_key is not None:
                valid_keys = []
                if not isinstance(pause_key, list) and not isinstance(pause_key, tuple):
                    pause_key = [pause_key]
                if isinstance(pause_key, list):
                    for key in pause_key:
                        if hasattr(controller, key):
                            controller_keys = getattr(controller, key)
                            for options in controller_keys:
                                valid_keys.append(options)
                cont = False
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            controller.quit()
                        elif (event.type == pygame.KEYDOWN and event.key in valid_keys) or ((event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN) and event.button in valid_keys):
                            cont = True
                            break
                    if cont:
                        break
                    time.sleep(0.01)

            if should_fade_out:
                for i in range(64):
                    win.blit(pygame_frame, (pygame_frame_x, pygame_frame_y))
                    black.set_alpha(4 * i)
                    win.blit(black, (0, 0))
                    if should_glitch:
                        for spot in glitch(0.5, win):
                            win.blit(spot[0], spot[1])
                    pygame.display.update()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            controller.quit()
                        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                            return None
                    time.sleep(0.01)

            black.set_alpha(255)
            win.blit(black, (0, 0))

        video.release()
        return None
