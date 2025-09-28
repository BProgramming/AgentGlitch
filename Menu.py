import time
import pygame
from enum import Enum
from Helpers import load_images, glitch, DifficultyScale, validate_file_list, handle_exception


class ButtonType(Enum):
    CLICK = 1
    BAR = 2


class Menu:
    JOYSTICK_TOLERANCE = 0.25

    def __init__(self, win, header, button_labels, music=None, should_glitch=True):
        self.clear = None
        self.clear_grayscale = None
        button_assets = load_images("Menu", "Buttons")
        self.notch_val = []
        self.buttons = self.__make_buttons__(button_labels, pygame.transform.smoothscale_by(button_assets["BUTTON_NORMAL"], 0.5), pygame.transform.smoothscale_by(button_assets["BUTTON_MOUSEOVER"], 0.5))
        self.header = pygame.font.SysFont("courier", 32).render(header, True, (255, 255, 255))
        self.screen = pygame.Surface((min(2 * win.get_width() // 3, max(self.buttons[0][0].width, self.header.get_width())), (self.buttons[0][0].height * len(self.buttons)) + self.header.get_height() + 10), pygame.SRCALPHA)
        self.screen.fill((0, 0, 0, 128))
        self.screen.blit(self.header, ((self.screen.get_width() - self.header.get_width()) // 2, 5))
        self.music = (None if music is None else validate_file_list("Music", music, "mp3"))
        self.music_index = 0
        self.should_glitch = should_glitch
        self.glitch_timer = 0
        self.glitches = None

    def cycle_music(self) -> None:
        if self.music is not None:
            self.music_index += 1
            if self.music_index >= len(self.music):
                self.music_index = 0

    def __make_buttons__(self, labels, button_normal, button_mouseover) -> list:
        buttons = []
        for label in labels:
            text = pygame.font.SysFont("courier", 32).render(label["label"], True, (255, 255, 255))
            normal = button_normal.copy()
            mouseover = button_mouseover.copy()
            notch_val = None
            if label["type"] == ButtonType.CLICK:
                normal.blit(text, ((normal.get_width() - text.get_width()) // 2, (normal.get_height() - text.get_height()) // 2))
                mouseover.blit(text, ((mouseover.get_width() - text.get_width()) // 2, (mouseover.get_height() - text.get_height()) // 2))
                buttons.append([pygame.Rect(0, 0, max(normal.get_width(), mouseover.get_width()), max(normal.get_height(), mouseover.get_height())), normal, mouseover, label["type"]])
            elif label["type"] == ButtonType.BAR:
                normal.blit(text, ((normal.get_width() - text.get_width()) // 10, (normal.get_height() - text.get_height()) // 4))
                mouseover.blit(text, ((mouseover.get_width() - text.get_width()) // 10, (mouseover.get_height() - text.get_height()) // 4))
                notch_val = (label["value"] - label["range"][0]) / (label["range"][-1] - label["range"][0])
                buttons.append([pygame.Rect(0, 0, max(normal.get_width(), mouseover.get_width()), max(normal.get_height(), mouseover.get_height())), normal, mouseover, label["type"]])
                if label["snap"]:
                    buttons[-1].append(label["range"])
            self.notch_val.append(notch_val)
        return buttons

    def fade_in(self, win: pygame.Surface, grayscale: bool = False) -> None:
        if self.clear is None:
            self.clear = pygame.display.get_surface().copy()
        for i in range(32):
            self.screen.set_alpha(8 * i)
            self.display(win, grayscale=grayscale)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                    self.screen.set_alpha(248)
                    self.display(win, grayscale=grayscale)
                    pygame.display.update()
                    return
            time.sleep(0.01)

    def fade_music(self) -> None:
        if self.music is not None:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
                pygame.mixer.music.unload()
            else:
                pygame.mixer.music.load(self.music[self.music_index])
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                pygame.mixer.music.play(fade_ms=2000)
                self.cycle_music()
                pygame.mixer.music.queue(self.music[self.music_index])

    def fade_out(self, win: pygame.Surface, grayscale: bool = False) -> None:
        if self.clear is None:
            return
        else:
            for i in range(32, 0, -1):
                self.screen.set_alpha(8 * i)
                self.display(win, grayscale=grayscale)
                pygame.display.update()

                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        self.screen.set_alpha(0)
                        self.display(win, grayscale=grayscale)
                        pygame.display.update()
                        return
                time.sleep(0.005)

    def set_mouse_pos(self, win) -> None:
        x = (win.get_width() // 2) + (self.buttons[0][0].width // 2.5)

        y = (win.get_height() + self.screen.get_height() - (2 * (len(self.buttons) - 0.5) * self.buttons[0][0].height)) // 2

        pygame.mouse.set_pos((x, y))

    def move_mouse_pos(self, win, direction) -> None:
        x = (win.get_width() // 2) + (self.buttons[0][0].width // 2.5)

        target = pygame.mouse.get_pos()[1] + (direction * self.buttons[0][0].height)
        top = (win.get_height() + self.screen.get_height() - (2 * (len(self.buttons) - 0.5) * self.buttons[0][0].height)) // 2
        bottom = (win.get_height() + self.screen.get_height() - self.buttons[0][0].height) // 2
        y = max(top, min(bottom, target))

        pygame.mouse.set_pos((x, y))

    def display(self, win: pygame.Surface, grayscale: bool=False) -> int | None:
        if self.clear is not None:
            if grayscale:
                if self.clear_grayscale is None:
                    self.clear_grayscale = pygame.transform.grayscale(self.clear)
                win.blit(self.clear_grayscale, (0, 0))
            else:
                win.blit(self.clear, (0, 0))

        screen = self.screen.copy()
        for i in range(len(self.buttons)):
            dest_x = (screen.get_width() - self.buttons[i][0].width) // 2
            dest_y = screen.get_height() - ((len(self.buttons) - i) * self.buttons[i][0].height)
            self.buttons[i][0].x = dest_x + ((win.get_width() - screen.get_width()) // 2)
            self.buttons[i][0].y = dest_y + ((win.get_height() - screen.get_height()) // 2)

            if self.buttons[i][3] == ButtonType.BAR:
                bar = pygame.Surface((self.buttons[i][0].width - 50, self.buttons[i][0].height // 10), pygame.SRCALPHA)
                bar_rect = bar.get_rect()
                notch = pygame.Surface((self.buttons[i][0].height // 10, self.buttons[i][0].height // 5), pygame.SRCALPHA)
                notch_rect = notch.get_rect()
                bar_rect.x = dest_x + ((self.buttons[i][0].width - bar.get_width()) // 2)
                bar_rect.y = dest_y + (3 * (self.buttons[i][0].height - bar.get_height()) // 4)
                notch_rect.x = bar_rect.x - (notch.get_width() // 2) + (self.notch_val[i] * bar.get_width())
                notch_rect.y = bar_rect.y - (bar.get_height() // 2)
            else:
                bar = None
                bar_rect = None
                notch = None
                notch_rect = None

            if self.buttons[i][0].collidepoint(pygame.mouse.get_pos()):
                button_type = 2
                for event in pygame.event.get():
                    if self.buttons[i][2].get_alpha() == 255 and self.buttons[i][3] == ButtonType.CLICK and ((event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (event.type == pygame.JOYBUTTONDOWN and event.button == 0)):
                        return i
                    elif self.buttons[i][3] == ButtonType.BAR and self.notch_val[i] is not None:
                        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]):
                            adj_x = pygame.mouse.get_pos()[0] - self.buttons[i][0].x - ((self.buttons[i][0].width - bar_rect.width) / 2)
                            adj_y = pygame.mouse.get_pos()[1] - self.buttons[i][0].y
                            if -10 <= adj_x <= bar_rect.width + 10 and self.buttons[i][0].height // 2 <= adj_y <= self.buttons[i][0].height:
                                self.notch_val[i] = min(1, max(0, adj_x / bar.get_width()))
                            if len(self.buttons[i]) > 4:
                                index = 0
                                for j in range(len(self.buttons[i][4])):
                                    interval = (self.buttons[i][4][j] - self.buttons[i][4][0]) / (self.buttons[i][4][-1] - self.buttons[i][4][0])
                                    if self.notch_val[i] > interval:
                                        index += 1
                                    elif self.notch_val[i] < interval:
                                        break
                                index = min(len(self.buttons[i][4]) - 1, max(0, index))
                                adj_notch_val = (self.buttons[i][4][index] - self.buttons[i][4][0]) / (self.buttons[i][4][-1] - self.buttons[i][4][0])
                                if index == 0:
                                    self.notch_val[i] = adj_notch_val
                                else:
                                    adj_notch_val_down = (self.buttons[i][4][index - 1] - self.buttons[i][4][0]) / (self.buttons[i][4][-1] - self.buttons[i][4][0])
                                    if self.notch_val[i] - adj_notch_val_down > adj_notch_val - self.notch_val[i]:
                                        self.notch_val[i] = adj_notch_val
                                    else:
                                        self.notch_val[i] = adj_notch_val_down
                        elif event.type == pygame.JOYAXISMOTION and event.axis == 0 and abs(event.value) > Menu.JOYSTICK_TOLERANCE:
                            if len(self.buttons[i]) > 4:
                                self.notch_val[i] = (self.buttons[i][4][min(len(self.buttons[i][4]) - 1, max(0, (self.buttons[i][4].index((self.notch_val[i] * (self.buttons[i][4][-1] - self.buttons[i][4][0])) + self.buttons[i][4][0]) + int(1 if event.value >= 0 else -1))))] - self.buttons[i][4][0]) / (self.buttons[i][4][-1] - self.buttons[i][4][0])
                                time.sleep(0.25)
                            else:
                                self.notch_val[i] = min(1, max(0, self.notch_val[i] + (0.01 if event.value >= 0 else -0.01)))
            else:
                button_type = 1

            screen.blit(self.buttons[i][button_type], (dest_x, dest_y))

            if self.buttons[i][3] == ButtonType.BAR:
                if len(self.buttons[i]) > 4:
                    label = str(DifficultyScale((self.notch_val[i] * (self.buttons[i][4][-1] - self.buttons[i][4][0])) + self.buttons[i][4][0]))
                else:
                    label = str(int(self.notch_val[i] * 100)) + "%"
                text = pygame.font.SysFont("courier", 32).render(label, True, (255, 255, 255))
                screen.blit(text, ((self.buttons[i][button_type].get_width() - text.get_width()) - (self.buttons[i][button_type].get_width() - text.get_width()) // 10, ((i + 1) * self.buttons[i][button_type].get_height()) - text.get_height()))
                if button_type == 1:
                    bar.fill((255, 255, 255))
                    notch.fill((140, 140, 140))
                elif button_type == 2:
                    bar.fill((255, 255, 255))
                    notch.fill((140, 0, 0))
                screen.blit(bar, (bar_rect.x, bar_rect.y))
                screen.blit(notch, (notch_rect.x, notch_rect.y))

        if self.should_glitch:
            if self.glitch_timer > 0:
                self.glitch_timer -= 0.01
            else:
                self.glitches = glitch(0.1, screen)
                self.glitch_timer = 0.1
            if self.glitches is not None:
                for spot in self.glitches:
                    screen.blit(spot[0], spot[1])

        win.blit(screen, ((win.get_width() - screen.get_width()) // 2, (win.get_height() - screen.get_height()) // 2))
        pygame.display.update()
        return None


class Selector(Menu):
    def __init__(self, win, header, note, images, values, index=0, music=None, should_glitch=True, accept_only=False, grayscale=False):
        self.clear = None
        self.clear_grayscale = None
        self.notch_val = [None, None, None]
        self.arrow_asset = pygame.transform.smoothscale_by(load_images("Menu", "Arrows")["ARROW_WHITE"], 0.5)
        button_assets = load_images("Menu", "Buttons")
        self.buttons = self.__make_buttons__(pygame.transform.smoothscale_by(button_assets["HALF_BUTTON_NORMAL"], 0.5), pygame.transform.smoothscale_by(button_assets["HALF_BUTTON_MOUSEOVER"], 0.5), pygame.transform.smoothscale_by(button_assets["BUTTON_NORMAL"], 0.5), pygame.transform.smoothscale_by(button_assets["BUTTON_MOUSEOVER"], 0.5), accept_only=accept_only)
        self.header = pygame.font.SysFont("courier", 32).render(header, True, (255, 255, 255))
        self.note = []
        if note is not None:
            for line in note:
                self.note.append(pygame.font.SysFont("courier", 16).render(line, True, (255, 255, 255)))
        image_width = 0
        image_height = 0
        self.image_index = index
        if isinstance(images, dict):
            if list(images.keys()) != ["normal", "retro"]:
                handle_exception("Picker sprites error: " + str(ValueError(images.keys())))
            else:
                self.images = {}
                for key in images.keys():
                    self.images[key] = []
                    for image in images[key]:
                        image_width = max(image_width, image.get_width())
                        image_height = max(image_height, image.get_height())
                        self.images[key].append([pygame.Rect(0, 0, image_width, image_height), image])
                self.image_selected = self.images["retro" if grayscale else "normal"][self.image_index]
        else:
            self.images = []
            for image in images:
                image_width = max(image_width, image.get_width())
                image_height = max(image_height, image.get_height())
                self.images.append([pygame.Rect(0, 0, image_width, image_height), image])
            self.image_selected = self.images[self.image_index]
        self.values = values
        self.screen = pygame.Surface((min(2 * win.get_width() // 3, max(image_width, self.buttons[0][0].width * 2, self.header.get_width())), self.header.get_height() + image_height + (self.note[0].get_height() * len(self.note) if len(self.note) > 0 else 0) + (self.buttons[0][0].height * 2) + 20), pygame.SRCALPHA)
        self.screen.fill((0, 0, 0, 128))
        self.screen.blit(self.header, ((self.screen.get_width() - self.header.get_width()) // 2, 5))
        for i in range(len(self.note)):
            self.screen.blit(self.note[i], ((self.screen.get_width() - self.note[i].get_width()) // 2, self.header.get_height() + image_height + (i * self.note[i].get_height()) + 10))
        self.music = (None if music is None else validate_file_list("Music", music, "mp3"))
        self.music_index = 0
        self.should_glitch = should_glitch
        self.glitch_timer = 0
        self.glitches = None

    def set_mouse_pos(self, win) -> None:
        x = self.buttons[0 if len(self.buttons) <= 1 else 1][0].x + (self.buttons[0 if len(self.buttons) <= 1 else 1][0].width * 0.75)

        y = (win.get_height() + self.screen.get_height() - self.buttons[0][0].height) // 2

        pygame.mouse.set_pos((x, y))

    def move_mouse_sideways(self, direction) -> None:
        if direction > 0:
            x = self.buttons[1][0].x + (self.buttons[1][0].width * 0.75)
        else:
            x = self.buttons[0][0].x + (self.buttons[0][0].width * 0.75)

        y = pygame.mouse.get_pos()[1]

        pygame.mouse.set_pos((x, y))

    def move_mouse_pos(self, win, direction) -> None:
        x = pygame.mouse.get_pos()[0]

        target = pygame.mouse.get_pos()[1] + (direction * self.buttons[0][0].height)
        top = (win.get_height() + self.screen.get_height() - (2 * (len(self.buttons) - 0.5) * self.buttons[0][0].height)) // 2
        bottom = (win.get_height() + self.screen.get_height() - self.buttons[0][0].height) // 2
        y = max(top, min(bottom, target))

        pygame.mouse.set_pos((x, y))

    def set_index(self, index: int, grayscale: bool = False) -> None:
        self.image_index = index
        if isinstance(self.images, dict):
            self.image_selected = self.images["retro" if grayscale else "normal"][index]
        else:
            self.image_selected = self.images[index]

    def cycle_images(self, direction: int, grayscale: bool = False) -> None:
        if direction > 0:
            self.image_index += 1
        else:
            self.image_index -= 1
        if isinstance(self.images, dict):
            if self.image_index >= len(self.images["retro" if grayscale else "normal"]):
                self.image_index = 0
            elif self.image_index < 0:
                self.image_index = len(self.images["retro" if grayscale else "normal"]) - 1
            self.image_selected = self.images["retro" if grayscale else "normal"][self.image_index]
        else:
            if self.image_index >= len(self.images):
                self.image_index = 0
            elif self.image_index < 0:
                self.image_index = len(self.images) - 1
            self.image_selected = self.images[self.image_index]

    def __make_buttons__(self, half_button_normal, half_button_mouseover, button_normal, button_mouseover, accept_only=False) -> list:
        buttons = []
        loop_range = range(1 if accept_only else 4)
        for i in loop_range:
            if accept_only:
                label = pygame.font.SysFont("courier", 32).render("Accept", True, (255, 255, 255))
                normal = button_normal.copy()
                mouseover = button_mouseover.copy()
            else:
                if i == 0:
                    label = pygame.transform.flip(self.arrow_asset, True, False)
                elif i == 1:
                    label = self.arrow_asset
                elif i == 2:
                    label = pygame.font.SysFont("courier", 32).render("Back", True, (255, 255, 255))
                else:
                    label = pygame.font.SysFont("courier", 32).render("Accept", True, (255, 255, 255))
                normal = half_button_normal.copy()
                mouseover = half_button_mouseover.copy()
            normal.blit(label, ((normal.get_width() - label.get_width()) // 2, (normal.get_height() - label.get_height()) // 2))
            mouseover.blit(label, ((mouseover.get_width() - label.get_width()) // 2, (mouseover.get_height() - label.get_height()) // 2))
            buttons.append([pygame.Rect(0, 0, max(normal.get_width(), mouseover.get_width()), max(normal.get_height(), mouseover.get_height())), normal, mouseover, ButtonType.CLICK])
        return buttons

    def display(self, win: pygame.Surface, grayscale: bool = False) -> int | None:
        if self.clear is not None:
            if grayscale:
                if self.clear_grayscale is None:
                    self.clear_grayscale = pygame.transform.grayscale(self.clear)
                win.blit(self.clear_grayscale, (0, 0))
            else:
                win.blit(self.clear, (0, 0))

        screen = self.screen.copy()
        if self.image_selected[1].get_width() > screen.get_width():
            self.image_selected[1] = pygame.transform.scale_by(self.image_selected[1], screen.get_width() / self.image_selected[1].get_width())
            self.image_selected[0].width = self.image_selected[1].get_width()
            self.image_selected[0].height = self.image_selected[1].get_height()
        dest_x = (screen.get_width() - self.image_selected[0].width) // 2
        dest_y = self.header.get_height() + 10
        self.image_selected[0].x = dest_x + ((win.get_width() - screen.get_width()) // 2)
        self.image_selected[0].y = dest_y + ((win.get_height() - screen.get_height()) // 2)
        screen.blit(self.image_selected[1], (dest_x, dest_y))

        for i in range(len(self.buttons)):
            if len(self.buttons) > 1:
                if i == 0:
                    dest_x = (screen.get_width() - (self.buttons[i][0].width * 2)) // 2
                    dest_y = screen.get_height() - ((len(self.buttons) - 2) * self.buttons[i][0].height)
                elif i == 1:
                    dest_x = ((screen.get_width() - (self.buttons[i][0].width * 2)) // 2) + self.buttons[i][0].width
                    dest_y = screen.get_height() - ((len(self.buttons) - 2) * self.buttons[i][0].height)
                elif i == 2:
                    dest_x = (screen.get_width() - (self.buttons[i][0].width * 2)) // 2
                    dest_y = screen.get_height() - ((len(self.buttons) - 3) * self.buttons[i][0].height)
                else:
                    dest_x = ((screen.get_width() - (self.buttons[i][0].width * 2)) // 2) + self.buttons[i][0].width
                    dest_y = screen.get_height() - ((len(self.buttons) - 3) * self.buttons[i][0].height)
            else:
                dest_x = (screen.get_width() - self.buttons[i][0].width) // 2
                dest_y = screen.get_height() - ((len(self.buttons) - i) * self.buttons[i][0].height)
            self.buttons[i][0].x = dest_x + ((win.get_width() - screen.get_width()) // 2)
            self.buttons[i][0].y = dest_y + ((win.get_height() - screen.get_height()) // 2)

            if self.buttons[i][0].collidepoint(pygame.mouse.get_pos()):
                button_type = 2
                for event in pygame.event.get():
                    if self.buttons[i][3] == ButtonType.CLICK and ((event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (event.type == pygame.JOYBUTTONDOWN and event.button == 0)):
                        return i
            else:
                button_type = 1

            screen.blit(self.buttons[i][button_type], (dest_x, dest_y))

        if self.should_glitch:
            if self.glitch_timer > 0:
                self.glitch_timer -= 0.01
            else:
                self.glitches = glitch(0.1, screen)
                self.glitch_timer = 0.1
            if self.glitches is not None:
                for spot in self.glitches:
                    screen.blit(spot[0], spot[1])

        win.blit(screen, ((win.get_width() - screen.get_width()) // 2, (win.get_height() - screen.get_height()) // 2))
        pygame.display.update()
        return None
