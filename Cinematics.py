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
    def __init__(self, files: dict[str, str] | list[dict[str, str]] | tuple[dict[str, str]], controller):
        self.cinematics = {}
        self.queued = []
        self.load(files, controller)

    def load(self, files: dict[str, str] | list[dict[str, str]] | tuple[dict[str, str]], controller) -> None:
        if type(files) not in [list, tuple]:
            files = [files]
        for file in files:
            if file["file"].upper() != "NONE":
                path = join(ASSETS_FOLDER, "Cinematics", file["file"])
                if isfile(path):
                    if file["type"].upper() == "SLIDE":
                        self.cinematics[file["name"]] = Cinematic(self.__load_slide__(path), CinematicType.SLIDE, controller, pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None or file["should_glitch"].upper() == "FALSE" else True), should_fade_in=(True if file.get("should_fade_in") is None or file["should_fade_in"].upper() == "TRUE" else False), should_fade_out=(True if file.get("should_fade_out") is None or file["should_fade_out"].upper() == "TRUE" else False), can_scale_up=(True if file.get("can_scale_up") is None or file["can_scale_up"].upper() == "TRUE" else False), can_scale_down=(True if file.get("can_scale_down") is None or file["can_scale_down"].upper() == "TRUE" else False))
                    elif file["type"].upper() == "VIDEO":
                        self.cinematics[file["name"]] = Cinematic(self.__load_video__(path), CinematicType.VIDEO, controller, pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None or file["should_glitch"].upper() == "FALSE" else True), should_fade_in=(True if file.get("should_fade_in") is None or file["should_fade_in"].upper() == "TRUE" else False), should_fade_out=(True if file.get("should_fade_out") is None or file["should_fade_out"].upper() == "TRUE" else False), can_scale_up=(True if file.get("can_scale_up") is None or file["can_scale_up"].upper() == "TRUE" else False), can_scale_down=(True if file.get("can_scale_down") is None or file["can_scale_down"].upper() == "TRUE" else False))
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
        self.queued.append(self.cinematics[name])

    def play(self, name: str, win: pygame.Surface) -> int:
        if self.cinematics.get(name) is not None:
            return self.cinematics[name].play(win)
        else:
            return 0

    def play_queue(self, win: pygame.Surface) -> int:
        dtime = 0
        for cinematic in self.queued:
            dtime += cinematic.play(win)
        self.queued = []
        return dtime / 1000

class Cinematic:
    def __init__(self, ent: pygame.Surface | cv2.VideoCapture, cinematic_type: CinematicType, controller, pause_key: int | list[int] | tuple[int] | None=None, text: str | None=None, should_glitch: bool=False, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True) -> None:
        self.controller = controller
        self.type = cinematic_type
        self.cinematic = ent
        self.pause_key = pause_key
        self.text = text
        self.should_glitch = should_glitch
        self.should_fade_in = should_fade_in
        self.should_fade_out = should_fade_out
        self.can_scale_up = can_scale_up
        self.can_scale_down = can_scale_down

    def play(self, win: pygame.Surface) -> float:
        start = time.perf_counter()
        pygame.mixer.pause()
        if self.type == CinematicType.SLIDE:
            self.__play_slide__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, can_scale_up=self.can_scale_up, can_scale_down=self.can_scale_down)
        elif self.type == CinematicType.VIDEO:
            self.__play_video__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, can_scale_up=self.can_scale_up, can_scale_down=self.can_scale_down)
        pygame.mixer.unpause()
        return time.perf_counter() - start

    @staticmethod
    def __play_slide__(slide: pygame.Surface, controller, win: pygame.Surface, text: str | None=None, should_glitch: bool=False, pause_key: int | list[int] | tuple[int] | None=None, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True) -> None:
        scale_factor = min(win.get_width() / slide.get_width(), win.get_height() / slide.get_height())
        if (can_scale_up and scale_factor > 1) or (can_scale_down and scale_factor < 1):
            slide = pygame.transform.scale_by(slide, scale_factor)
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
    def __play_video__(video: cv2.VideoCapture, controller, win: pygame.Surface, text: str | None=None, should_glitch: bool=False, pause_key: int | list[int] | tuple[int] | None=None, should_fade_in: bool=True, should_fade_out: bool=True, can_scale_up: bool=True, can_scale_down: bool=True) -> None:
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

            scale_factor = min(win.get_width() / pygame_frame.get_width(), win.get_height() / pygame_frame.get_height())
            if (can_scale_up and scale_factor > 1) or (can_scale_down and scale_factor < 1):
                pygame_frame = pygame.transform.scale(pygame_frame, (int(pygame_frame.get_width() * scale_factor), int(pygame_frame.get_height() * scale_factor)))

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
