import pygame
import sys
import time
from enum import Enum
from Helpers import glitch
from os.path import join, isfile


class CinematicType(Enum):
    SLIDE = 1
    VIDEO = 2


class CinematicsManager:
    def __init__(self, files, controller):
        self.cinematics = {}
        self.queued = []
        self.load(files, controller)

    def load(self, files, controller):
        if type(files) not in [list, tuple]:
            files = [files]
        for file in files:
            path = join("Assets", "Cinematics", file["file"])
            if isfile(path):
                if file["type"].upper() == "SLIDE":
                    self.cinematics[file["name"]] = Cinematic(self.__load_slide__(path), CinematicType.SLIDE, controller, pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None or file["should_glitch"].upper() == "FALSE" else True), should_fade_in=(True if file.get("should_fade_in") is None or file["should_fade_in"].upper() == "TRUE" else False), should_fade_out=(True if file.get("should_fade_out") is None or file["should_fade_out"].upper() == "TRUE" else False))
                elif file["type"].upper() == "VIDEO":
                    self.cinematics[file["name"]] = Cinematic(self.__load_video__(path), CinematicType.VIDEO, controller, pause_key=(None if file.get("pause_key") is None else file["pause_key"]), text=(None if file.get("text") is None else file["text"]), should_glitch=(False if file.get("should_glitch") is None or file["should_glitch"].upper() == "FALSE" else True), should_fade_in=(True if file.get("should_fade_in") is None or file["should_fade_in"].upper() == "TRUE" else False), should_fade_out=(True if file.get("should_fade_out") is None or file["should_fade_out"].upper() == "TRUE" else False))

    def __load_slide__(self, file):
        return pygame.image.load(file)

    def __load_video__(self, file):
        return None

    def clear_queue(self):
        self.queued = []

    def queue(self, name):
        self.queued.append(self.cinematics[name])

    def play(self, name, win, fps=None):
        if self.cinematics.get(name) is not None:
            return self.cinematics[name].play(win, fps=fps)
        else:
            return 0

    def play_queue(self, win, fps=None):
        dtime = 0
        for cinematic in self.queued:
            dtime += cinematic.play(win, fps=fps)
        self.queued = []
        return dtime

class Cinematic:
    def __init__(self, obj, type, controller, pause_key=None, text=None, should_glitch=False, should_fade_in=True, should_fade_out=True):
        self.controller = controller
        self.type = type
        self.cinematic = obj
        self.pause_key = pause_key
        self.text = text
        self.should_glitch = should_glitch
        self.should_fade_in = should_fade_in
        self.should_fade_out = should_fade_out

    def play(self, win, fps=None):
        start = time.perf_counter_ns()
        pygame.mixer.pause()
        if self.type == CinematicType.SLIDE:
            self.__play_slide__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, fps=fps)
        elif self.type == CinematicType.VIDEO:
            self.__play_video__(self.cinematic, self.controller, win, text=self.text, should_glitch=self.should_glitch, pause_key=self.pause_key, should_fade_in=self.should_fade_in, should_fade_out=self.should_fade_out, fps=fps)
        pygame.mixer.unpause()
        return (time.perf_counter_ns() - start) // 1000000

    @staticmethod
    def __play_slide__(slide, controller, win, text=None, should_glitch=False, pause_key=None, should_fade_in=True, should_fade_out=True, fps=None):
        ffwd = False
        og_slide = slide
        if text is not None:
            for i in range(len(text)):
                text_line = pygame.font.SysFont("courier", 32).render(text[i], True, (0, 0, 0))
                slide.blit(text_line, (slide.get_width() // 5, (slide.get_height() // 5) + (i * text_line.get_height())))

        black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
        black.fill((0, 0, 0))

        if should_fade_in:
            for i in range(64):
                win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(255 - (4 * i))
                win.blit(black, (0, 0))
                pygame.display.update()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.save_player_profile(controller)
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        ffwd = True
                        break
                if ffwd:
                    break
                time.sleep(0.01)
        else:
            black.set_alpha(255)
            win.blit(black, (0, 0))

        pause_dtime = 0
        while pause_dtime < 1000:
            win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
            if should_glitch and pause_dtime > 750:
                for spot in glitch(0.5, win):
                    win.blit(spot[0], spot[1])
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    controller.save_player_profile(controller)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                    ffwd = True
                    break
            if ffwd:
                break
            time.sleep(0.01)
            pause_dtime += 10

        if pause_key is not None:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.save_player_profile(controller)
                        pygame.quit()
                        sys.exit()
                    elif (event.type == pygame.KEYDOWN and event.key == pause_key) or ((event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN) and event.button == pause_key):
                        break
                time.sleep(0.01)

        if should_fade_out:
            for i in range(64):
                win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                if should_glitch:
                    for spot in glitch(0.5, win):
                        win.blit(spot[0], spot[1])
                pygame.display.update()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.save_player_profile(controller)
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        ffwd = True
                        break
                if ffwd:
                    break
                time.sleep(0.01)
        else:
            black.set_alpha(255)
            win.blit(black, (0, 0))

        if text is not None:
            slide.blit(og_slide, (0, 0))

    @staticmethod
    def __play_video__(video, controller, win, text=None, should_glitch=False, pause_key=None, should_fade_in=True, should_fade_out=True, fps=None):
        pass
