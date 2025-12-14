import cv2
import pygame
import time
from enum import Enum
from Helpers import glitch, handle_exception, ASSETS_FOLDER, retroify_image, NORMAL_WHITE, RETRO_WHITE, RETRO_BLACK, NORMAL_BLACK
from os.path import join, isfile, abspath


class CinematicType(Enum):
    SLIDE = 1
    VIDEO = 2


class CinematicsManager:
    def __init__(self, files: dict[str, str] | list[dict[str, str]] | tuple[dict[str, str]], controller, player_sprites: dict[str, pygame.Surface] | None=None):
        self.cinematics = {}
        self.queued = []
        self.load(files, controller, player_sprites)

    def load(self, files: dict[str, str] | list[dict[str, str]] | tuple[dict[str, str]], controller, player_sprites) -> None:
        if type(files) not in [list, tuple]:
            files = [files]
        for file in files:
            if file["file"] is not None:
                path = join(ASSETS_FOLDER, "Cinematics", file["file"])
                if isfile(path):
                    if file["type"].upper() == "SLIDE":
                        self.cinematics[file["name"]] = Cinematic(self.__load_slide__(path), CinematicType.SLIDE, controller, player_sprites, player_blit=(None if file.get("player_blit") is None else file["player_blit"]), pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None else file["should_glitch"]), should_fade_in=(True if file.get("should_fade_in") is None else file["should_fade_in"]), should_fade_out=(True if file.get("should_fade_out") is None else file["should_fade_out"]), can_scale_up=(True if file.get("can_scale_up") is None else file["can_scale_up"]), can_scale_down=(True if file.get("can_scale_down") is None else file["can_scale_down"]), stretch=(False if file.get("stretch") is None else file["stretch"]), delete_after_play=(False if file.get("delete") is None else file["delete"]))
                    elif file["type"].upper() == "VIDEO":
                        self.cinematics[file["name"]] = Cinematic(self.__load_video__(path), CinematicType.VIDEO, controller, player_sprites, player_blit=None, pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None else file["should_glitch"]), should_fade_in=(True if file.get("should_fade_in") is None else file["should_fade_in"]), should_fade_out=(True if file.get("should_fade_out") is None else file["should_fade_out"]), can_scale_up=(True if file.get("can_scale_up") is None else file["can_scale_up"]), can_scale_down=(True if file.get("can_scale_down") is None else file["can_scale_down"]), stretch=(False if file.get("stretch") is None else file["stretch"]), delete_after_play=(False if file.get("delete") is None else file["delete"]))
                else:
                    handle_exception(f'File {FileNotFoundError(abspath(path))} not found.')

    @staticmethod
    def __load_slide__(file: str) -> pygame.Surface:
        return pygame.image.load(file)

    @staticmethod
    def __load_video__(file: str) -> cv2.VideoCapture:
        return cv2.VideoCapture(file)

    def clear_queue(self) -> None:
        self.queued = []

    def queue(self, name: str) -> None:
        self.queued.append(name)

    def play(self, name: str, win: pygame.Surface) -> float:
        if self.cinematics.get(name) is not None:
            cinematic = self.cinematics[name]
            dtime = cinematic.play(win)
            if cinematic.delete_after_play:
                del self.cinematics[name]
            return dtime
        else:
            return 0

    def play_queue(self, win: pygame.Surface) -> float:
        dtime = 0
        for name in self.queued:
            dtime += self.play(name, win)
        self.queued = []
        return dtime

class Cinematic:
    def __init__(self, ent: pygame.Surface | cv2.VideoCapture, cinematic_type: CinematicType, controller, player_sprites, player_blit: list[dict] | None=None, pause_key: int | list[int] | tuple[int] | None=None, text: str | None=None, should_glitch: bool=False, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True, stretch: bool=False, delete_after_play: bool=True) -> None:
        self.controller = controller
        self.type = cinematic_type
        self.cinematic = ent
        if player_sprites is not None and player_blit is not None: # This is only supported for slides, not for videos
            for blit in player_blit:
                if blit.get("animation") is not None and isinstance(blit["animation"], str) \
                    and blit.get("facing") is not None and isinstance(blit["facing"], str) \
                    and blit.get("frame") is not None and isinstance(blit["frame"], int) \
                    and blit.get("coord") is not None and isinstance(blit["coord"], list) and len(blit["coord"]) == 2 \
                        and isinstance(blit["coord"][0], int) and isinstance(blit["coord"][1], int):
                    anim = f'{blit["animation"]}_{blit["facing"]}'.upper()
                    frame = blit["frame"]
                    coord = blit["coord"]
                    if coord[0] < 0:
                        coord[0] += self.cinematic.get_width()
                    if coord[1] < 0:
                        coord[1] += self.cinematic.get_height()
                    self.cinematic.blit(player_sprites[anim][frame], coord)
        self.pause_key = pause_key
        self.text = text
        self.should_glitch: bool = should_glitch
        self.should_fade_in: bool = should_fade_in
        self.should_fade_out: bool = should_fade_out
        self.can_scale_up: bool = can_scale_up
        self.can_scale_down: bool = can_scale_down
        self.stretch: bool = stretch
        self.delete_after_play: bool = delete_after_play

    def play(self, win: pygame.Surface) -> float:
        start = time.perf_counter()
        pygame.mixer.pause()
        if self.type == CinematicType.SLIDE:
            self.__play_slide__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, can_scale_up=self.can_scale_up, can_scale_down=self.can_scale_down, stretch=self.stretch)
        elif self.type == CinematicType.VIDEO:
            self.__play_video__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, can_scale_up=self.can_scale_up, can_scale_down=self.can_scale_down, stretch=self.stretch)
        pygame.mixer.unpause()
        return time.perf_counter() - start

    @staticmethod
    def __play_slide__(slide: pygame.Surface, controller, win: pygame.Surface, text: str | None=None, should_glitch: bool=False, pause_key: int | list[int] | tuple[int] | None=None, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True, stretch: bool=False) -> None:

        scale_factor = (win.get_width() / slide.get_width(), win.get_height() / slide.get_height())
        if stretch:
            slide = pygame.transform.scale_by(slide, scale_factor)
        else:
            min_factor = min(scale_factor[0], scale_factor[1])
            if (can_scale_up and min_factor > 1) or (can_scale_down and min_factor < 1):
                slide = pygame.transform.scale_by(slide, min_factor)
        og_slide = slide

        if controller.retro:
            slide = retroify_image(slide)
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
                        return
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
                    return
            time.sleep(0.01)
            pause_dtime += .01

        if pause_key is not None:
            valid_keys = []
            if type(pause_key) not in [list, tuple]:
                pause_key = [pause_key]
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
                        return
                time.sleep(0.01)

        black.set_alpha(255)
        win.blit(black, (0, 0))

        if text is not None:
            slide.blit(og_slide, (0, 0))

    @staticmethod
    def __play_video__(video: cv2.VideoCapture, controller, win: pygame.Surface, text: str | None=None, should_glitch: bool=False, pause_key: int | list[int] | tuple[int] | None=None, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True, stretch: bool=False) -> None:
        if not video.isOpened():
            raise IOError(f'Video file {str(video)} could not be opened.')
        if controller.retro:
            colour_white = RETRO_WHITE
            colour_black = RETRO_BLACK
        else:
            colour_white = NORMAL_WHITE
            colour_black = NORMAL_BLACK
        text_colour = colour_white

        ret, frame = video.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pygame_frame = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

            scale_factor = (win.get_width() / pygame_frame.get_width(), win.get_height() / pygame_frame.get_height())
            if stretch:
                pygame_frame = pygame.transform.scale_by(pygame_frame, scale_factor)
            else:
                min_factor = min(scale_factor[0], scale_factor[1])
                if (can_scale_up and min_factor > 1) or (can_scale_down and min_factor < 1):
                    pygame_frame = pygame.transform.scale_by(pygame_frame, min_factor)

            pygame_frame_x = (win.get_width() - pygame_frame.get_width()) // 2
            pygame_frame_y = (win.get_height() - pygame_frame.get_height()) // 2

            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill(colour_black)

            if should_fade_in:
                for i in range(64):
                    #if text is not None:
                    #    for i in range(len(text)):
                    #        text_line = pygame.font.SysFont("courier", 32).render(text[i], True, text_colour)
                    #        pygame_frame.blit(text_line, (pygame_frame.get_width() // 5, (pygame_frame.get_height() // 5) + (i * text_line.get_height())))
                    win.blit(pygame_frame, (pygame_frame_x, pygame_frame_y))
                    black.set_alpha(255 - (4 * i))
                    win.blit(black, (0, 0))
                    pygame.display.update()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            controller.quit()
                        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                            return
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
                        return
                time.sleep(0.01)

                ret, frame = video.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pygame_frame = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                    if (can_scale_up and scale_factor > 1) or (can_scale_down and scale_factor < 1):
                        pygame_frame = pygame.transform.scale(pygame_frame, (int(pygame_frame.get_width() * scale_factor), int(pygame_frame.get_height() * scale_factor)))
                else:
                    break

            if pause_key is not None:
                valid_keys = []
                if type(pause_key) not in [list, tuple]:
                    pause_key = [pause_key]
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
                    #if text is not None:
                    #    for i in range(len(text)):
                    #        text_line = pygame.font.SysFont("courier", 32).render(text[i], True, text_colour)
                    #        pygame_frame.blit(text_line, (pygame_frame.get_width() // 5, (pygame_frame.get_height() // 5) + (i * text_line.get_height())))
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
                            return
                    time.sleep(0.01)

            black.set_alpha(255)
            win.blit(black, (0, 0))

        video.release()
