import time
import pygame
from enum import Enum
from Helpers import load_images, glitch, DifficultyScale, validate_file_list, handle_exception, retroify_image, NORMAL_BLACK, NORMAL_WHITE, RETRO_BLACK, RETRO_WHITE


class ButtonType(Enum):
    CLICK = 1
    BAR = 2


class Button:
    def __init__(self, controller, x, y, width, height, value, img_normal=None, img_mouseover=None, label_normal=None, label_mouseover=None) -> None:
        self.rect = pygame.Rect(x, y, width, height)
        self.controller = controller
        self.value = value
        self._normal = {'normal': self.__make__(img_normal, label_normal), 'mouseover': self.__make__(img_mouseover, label_mouseover)}
        self._retro = {key: retroify_image(value) for key, value in self._normal.items()}
        self.is_mouseover = False
        self.is_enabled = True

    def __make__(self, image: pygame.Surface | None, label: pygame.Surface | None) -> pygame.Surface:
        if image is None:
            image = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            image.fill(NORMAL_BLACK)
        else:
            image = image.copy()

        if label is None:
            return image
        else:
            image.blit(label, ((image.get_width() - label.get_width()) // 2, (image.get_height() - label.get_height()) // 2))
            return image

    def __get_image__(self, name) -> pygame.Surface:
        if self.controller.retro:
            return self._retro[name]
        else:
            return self._normal[name]

    def set_alpha(self, alpha: int) -> None:
        for key in self._normal.keys():
            self._normal[key].set_alpha(alpha // (2 - int(self.is_enabled)))
        for key in self._retro.keys():
            self._retro[key].set_alpha(alpha // (2 - int(self.is_enabled)))

    @property
    def normal(self) -> pygame.Surface:
        return self.__get_image__('normal')

    @property
    def mouseover(self) -> pygame.Surface:
        return self.__get_image__('mouseover')

    def draw(self) -> None:
        self.controller.win.blit(self.mouseover if self.is_mouseover and self.is_enabled else self.normal, (self.rect.x, self.rect.y))


class Bar(Button):
    def __init__(self, controller, x, y, width, height, value, range, snap=True, img_normal=None, img_mouseover=None, label_normal=None, label_mouseover=None) -> None:
        super().__init__(controller, x, y, width, height, value, img_normal=img_normal, img_mouseover=img_mouseover, label_normal=label_normal, label_mouseover=label_mouseover)
        self.range = range
        self.snap = snap
        self.bar_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height / 10)

    @property
    def pct_val(self) -> int:
        return (self.value - self.range[0]) / (self.range[-1] - self.range[0])

    def __get_notch__(self, base: pygame.Surface) -> pygame.Surface:
        bar = pygame.Surface((base.get_width() - 50, base.get_height() / 10), pygame.SRCALPHA)
        bar.fill(RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
        base.blit(bar, ((base.get_width() - bar.get_width()) / 2, (base.get_height() - bar.get_height()) * 0.75))
        notch = pygame.Surface((base.get_height() / 10, base.get_height() / 5), pygame.SRCALPHA)
        notch.fill((137, 0, 0, 255) if self.controller.retro else (140, 0, 0, 255))
        base.blit(notch, (((base.get_width() - bar.get_width()) / 2) + (self.pct_val * bar.get_width()), (base.get_height() - bar.get_height() - (notch.get_height() / 2)) * 0.75))
        return base

    @property
    def normal(self) -> pygame.Surface:
        return self.__get_notch__(super().normal.copy())

    @property
    def mouseover(self) -> pygame.Surface:
        return self.__get_notch__(super().mouseover.copy())


class Menu:
    JOYSTICK_TOLERANCE = 3500

    def __init__(self, controller, header, buttons: list[dict], music=None, should_glitch=True):
        self.controller = controller
        self.clear_normal = None
        self.clear_retro = None
        button_assets = {key: pygame.transform.smoothscale_by(value, 0.5) for key, value in load_images("Menu", "Buttons").items()}
        button_width = button_assets["BUTTON_NORMAL"].get_width()
        button_height = button_assets["BUTTON_NORMAL"].get_height()
        if header is not None:
            text = pygame.font.SysFont("courier", 32).render(header, True, NORMAL_WHITE)
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, max(button_width, text.get_width())), (button_height * len(buttons)) + text.get_height() + 10), pygame.SRCALPHA)
            screen.fill(NORMAL_BLACK)
            screen.blit(text, ((screen.get_width() - text.get_width()) // 2, 5))
        else:
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, button_width), button_height * len(buttons)), pygame.SRCALPHA)
            screen.fill(NORMAL_BLACK)
        self.screen_normal = screen
        self.screen_retro = retroify_image(screen)
        self.rect = pygame.Rect((self.controller.win.get_width() - screen.get_width()) // 2, (self.controller.win.get_height() - screen.get_height()) // 2, screen.get_width(), screen.get_height())

        self.buttons = []
        for i in range(len(buttons)):
            x = (self.controller.win.get_width() - button_width) // 2
            y = self.controller.win.get_height() - self.rect.y - ((len(buttons) - i) * button_height)
            label = pygame.font.SysFont("courier", 32).render(buttons[i]["label"], True, NORMAL_WHITE)
            if buttons[i]["type"] == ButtonType.CLICK:
                button = Button(self.controller, x, y, button_width, button_height, i, img_normal=button_assets["BUTTON_NORMAL"], img_mouseover=button_assets["BUTTON_MOUSEOVER"], label_normal=label, label_mouseover=label)
            elif buttons[i]["type"] == ButtonType.BAR:
                button = Bar(self.controller, x, y, button_width, button_height, buttons[i]["value"], buttons[i]["range"], snap=buttons[i]["snap"], img_normal=button_assets["BUTTON_NORMAL"], img_mouseover=button_assets["BUTTON_MOUSEOVER"], label_normal=label, label_mouseover=label)
            else:
                button = None
            self.buttons.append(button)
        self.joystick_movement = (0, 0)

        self.music = (None if music is None else validate_file_list("Music", music, "mp3"))
        self.music_index = 0
        self.should_glitch = should_glitch
        self.glitch_timer = 0
        self.glitches = None

    def set_alpha(self, alpha: int) -> None:
        for button in self.buttons:
            button.set_alpha(alpha)
        self.screen_normal.set_alpha(alpha)
        self.screen_retro.set_alpha(alpha)

    def cycle_music(self) -> None:
        if self.music is not None:
            self.music_index += 1
            if self.music_index >= len(self.music):
                self.music_index = 0

    def fade_in(self) -> None:
        if self.clear_normal is None:
            self.clear_normal = pygame.display.get_surface().copy()
        if self.clear_retro is None:
            self.clear_retro = retroify_image(self.clear_normal)

        if self.controller.gamepad is not None:
            self.set_mouse_pos(0)
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(True)

        for i in range(32):
            self.set_alpha(8 * i)
            self.draw()
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                    self.set_alpha(248)
                    self.draw()
                    pygame.display.update()
                    return
            time.sleep(0.005)

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

    def fade_out(self) -> None:
        pygame.mouse.set_visible(False)
        if (self.controller.retro and self.clear_retro is None) or (not self.controller.retro and self.clear_normal is None):
            return
        else:
            for i in range(32, 0, -1):
                self.set_alpha(8 * i)
                self.draw()
                pygame.display.update()

                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                        self.set_alpha(0)
                        self.draw()
                        pygame.display.update()
                        return
                time.sleep(0.005)

    def draw(self) -> None:
        if self.clear_normal is None:
            self.clear_normal = pygame.display.get_surface().copy()
        if self.clear_retro is None:
            self.clear_retro = retroify_image(self.clear_normal)

        self.controller.win.fill((0, 0, 0))
        clear = self.clear_retro if self.controller.retro else self.clear_normal
        self.controller.win.blit(clear, ((self.controller.win.get_width() - clear.get_width()) / 2, (self.controller.win.get_height() - clear.get_height()) / 2))
        screen = self.screen_retro if self.controller.retro else self.screen_normal
        self.controller.win.blit(screen, (self.rect.x, self.rect.y))
        for button in self.buttons:
            button.draw()

    def loop(self) -> int | None:
        if self.controller.gamepad is not None:
            should_process_event = True
            gamepad = self.controller.gamepad
            layout = self.controller.GAMEPAD_LAYOUTS[self.controller.active_gamepad_layout]
            if abs(gamepad.get_axis(layout['axis_vert'])) > Menu.JOYSTICK_TOLERANCE:
                self.joystick_movement = (0, 1 if gamepad.get_axis(layout['axis_vert']) > 0 else -1)
                should_process_event = False
            elif abs(gamepad.get_axis(layout['axis_horiz'])) > Menu.JOYSTICK_TOLERANCE:
                self.joystick_movement = (1 if gamepad.get_axis(layout['axis_horiz']) > 0 else -1, 0)
                should_process_event = False
            elif gamepad.get_button(layout['button_up']):
                self.joystick_movement = (0, -1)
                should_process_event = False
            elif gamepad.get_button(layout['button_down']):
                self.joystick_movement = (0, 1)
                should_process_event = False
            elif gamepad.get_button(layout['button_right']):
                self.joystick_movement = (1, 0)
                should_process_event = False
            elif gamepad.get_button(layout['button_left']):
                self.joystick_movement = (-1, 0)
                should_process_event = False
            if self.joystick_movement != (0, 0) and should_process_event:
                self.move_mouse_pos_horiz(self.joystick_movement[0])
                self.move_mouse_pos_vert(self.joystick_movement[1])
                self.joystick_movement = (0, 0)

        pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.buttons):
            button.is_mouseover = (button.is_enabled and button.rect.collidepoint(pos))

            if button.is_mouseover:
                if pygame.mouse.get_pressed()[0]:
                    if isinstance(button, Bar):
                        pct = (pos[0] - button.bar_rect.x) / button.bar_rect.width
                        if button.snap:
                            dec = pct * button.range[-1]
                            if dec < button.range[0]:
                                button.value = button.range[0]
                            elif dec > button.range[-1]:
                                button.value = button.range[-1]
                            else:
                                for val in button.range:
                                    if val >= dec:
                                        button.value = val
                                        break
                        else:
                            button.value = min(button.range[-1], max(button.range[0], pct * button.range[-1]))
                for event in pygame.event.get():
                    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (event.type == pygame.JOYBUTTONDOWN and event.button == self.controller.GAMEPAD_LAYOUTS[self.controller.active_gamepad_layout]['button_jump']):
                        return i
                    elif event.type == pygame.JOYBUTTONDOWN and event.button == self.controller.GAMEPAD_LAYOUTS[self.controller.active_gamepad_layout]['button_crouch_uncrouch']:
                        return -1
        return None

    def set_mouse_pos(self, i) -> None:
        rect = self.buttons[i].rect
        pygame.mouse.set_pos(rect.x + (rect.width * 0.75), rect.y + (rect.height / 2))

    def move_mouse_pos_vert(self, direction) -> None:
        if direction == 0 or len(self.buttons) == 1:
            return
        if pygame.mouse.get_visible():
            pygame.mouse.set_visible(False)
        for i, button in enumerate(self.buttons):
            if button.rect.collidepoint(pygame.mouse.get_pos()):
                if isinstance(self, Selector) and ((direction > 0 and i < len(self.buttons) // 2) or (direction < 0 and i > (len(self.buttons) // 2) - 1)) or not isinstance(self, Selector) and ((direction > 0 and i < len(self.buttons) - 1) or (direction < 0 and i > 0)):
                    cur = pygame.mouse.get_pos()
                    pygame.mouse.set_pos(cur[0], cur[1] + (direction * button.rect.height))
                    break

    def move_mouse_pos_horiz(self, direction) -> None:
        if direction == 0 or len(self.buttons) == 1 or not isinstance(self, Selector):
            return
        if pygame.mouse.get_visible():
            pygame.mouse.set_visible(False)
        for i, button in enumerate(self.buttons):
            if button.rect.collidepoint(pygame.mouse.get_pos()):
                if isinstance(button, Bar):
                    if len(button.range) == 2 and button.range[0] == 0 and button.range[1] == 100:
                        for j, val in enumerate(button.range):
                            if button.value == val and ((j < len(button.range) - 1 and direction > 0) or (j > 0 and direction < 0)):
                                button.value = max(button.range[0], min(button.range[-1], button.pct_val * (button.range[-1] - button.range[0]) + button.range[0]))
                                break
                elif (direction > 0 and i % 2 == 0) or (direction < 0 and i % 2 == 1):
                    cur = pygame.mouse.get_pos()
                    pygame.mouse.set_pos(cur[0] + direction * button.rect.width, cur[1])
                break

class Selector(Menu):
    def __init__(self, controller, header, note, images, values, index=0, music=None, should_glitch=True, accept_only=False):
        self.controller = controller
        self.clear_normal = None
        self.clear_retro = None
        button_assets = {key: pygame.transform.smoothscale_by(value, 0.5) for key, value in load_images("Menu", "Buttons").items()}
        button_width = button_assets["HALF_BUTTON_NORMAL"].get_width()
        button_height = button_assets["HALF_BUTTON_NORMAL"].get_height()
        arrow_asset = pygame.transform.smoothscale_by(load_images("Menu", "Arrows")["ARROW_WHITE"], 0.5)

        max_image_width = 0
        max_image_height = 0
        self.image_index = index
        if isinstance(images, dict):
            if list(images.keys()) != ["normal", "retro"]:
                handle_exception(f'Picker sprites error: {ValueError(images.keys())}')
            else:
                self.images = {}
                for key in images.keys():
                    self.images[key] = []
                    for image in images[key]:
                        scale_val = min(image.get_width() / self.controller.win.get_width(), image.get_height() / self.controller.win.get_height())
                        if scale_val > 1:
                            image = pygame.transform.scale_by(image, 1 / scale_val)
                        max_image_width = max(max_image_width, image.get_width())
                        max_image_height = max(max_image_height, image.get_height())
                        self.images[key].append(image)
        else:
            self.images = {"normal": [], "retro": []}
            for image in images:
                scale_val = min(image.get_width() / self.controller.win.get_width(), image.get_height() / self.controller.win.get_height())
                if scale_val > 1:
                    image = pygame.transform.scale_by(image, 1 / scale_val)
                max_image_width = max(max_image_width, image.get_width())
                max_image_height = max(max_image_height, image.get_height())
                self.images["normal"].append(image)
                self.images["retro"].append(retroify_image(image))

        self.note = []
        if note is not None:
            for line in note:
                self.note.append(pygame.font.SysFont("courier", 16).render(line, True, NORMAL_WHITE))
        if header is not None:
            text = pygame.font.SysFont("courier", 32).render(header, True, NORMAL_WHITE)
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, max(max_image_width, button_width * 2, text.get_width())), max_image_height + (button_height * 2) + text.get_height() + (self.note[0].get_height() * len(self.note) if len(self.note) > 0 else 0) + 10), pygame.SRCALPHA)
            screen.fill(NORMAL_BLACK)
            screen.blit(text, ((screen.get_width() - text.get_width()) / 2, 5))
        else:
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, button_width * 2), max_image_height + (button_height * 2)), pygame.SRCALPHA)
            screen.fill(NORMAL_BLACK)
        self.screen_normal = screen
        self.screen_retro = retroify_image(screen)
        self.rect = pygame.Rect((self.controller.win.get_width() - screen.get_width()) // 2, (self.controller.win.get_height() - screen.get_height()) // 2, screen.get_width(), screen.get_height())

        self.values = values

        self.buttons = []
        loop_range = range(1 if accept_only else 4)
        for i in loop_range:
            normal = button_assets["HALF_BUTTON_NORMAL"].copy()
            mouseover = button_assets["HALF_BUTTON_MOUSEOVER"].copy()

            if accept_only:
                label = pygame.font.SysFont("courier", 32).render("Accept", True, NORMAL_WHITE)
            else:
                if i == 0:
                    label = pygame.transform.flip(arrow_asset, True, False)
                elif i == 1:
                    label = arrow_asset
                elif i == 2:
                    label = pygame.font.SysFont("courier", 32).render("Back", True, NORMAL_WHITE)
                else:
                    label = pygame.font.SysFont("courier", 32).render("Accept", True, NORMAL_WHITE)

            x = self.controller.win.get_width() // 2 - (button_width * (1 - i % 2))
            y = self.rect.y + self.rect.height - (button_height * ((len(loop_range) - i + 1) // 2))
            self.buttons.append(Button(self.controller, x, y, button_width, button_height, i, img_normal=normal, img_mouseover=mouseover, label_normal=label, label_mouseover=label))
        self.joystick_movement = (0, 0)

        self.music = (None if music is None else validate_file_list("Music", music, "mp3"))
        self.music_index = 0
        self.should_glitch = should_glitch
        self.glitch_timer = 0
        self.glitches = None
        self.cycle_images(0)

    def move_mouse_pos_horiz(self, direction) -> None:
        if direction == 0 or len(self.buttons) == 1:
            return
        if pygame.mouse.get_visible():
            pygame.mouse.set_visible(False)
        for i, button in enumerate(self.buttons):
            if button.rect.collidepoint(pygame.mouse.get_pos()):
                if isinstance(button, Bar):
                    if len(button.range) == 2 and button.range[0] == 0 and button.range[1] == 100:
                        for j, val in enumerate(button.range):
                            if button.value == val and ((j < len(button.range) - 1 and direction > 0) or (j > 0 and direction < 0)):
                                button.value = max(button.range[0], min(button.range[-1], button.pct_val * (button.range[-1] - button.range[0]) + button.range[0]))
                                break
                elif (direction > 0 and i % 2 == 0) or (direction < 0 and i % 2 == 1):
                    cur = pygame.mouse.get_pos()
                    pygame.mouse.set_pos(cur[0] + direction * button.rect.width, cur[1])
                break
    def set_index(self, index: int) -> None:
        self.image_index = index
        self.image_selected = self.images["retro" if self.controller.retro else "normal"][index]

    def cycle_images(self, direction: int) -> None:
        if direction > 0:
            self.image_index += 1
        elif direction < 0:
            self.image_index -= 1
        if self.image_index >= len(self.images["retro" if self.controller.retro else "normal"]):
            self.image_index = 0
        elif self.image_index < 0:
            self.image_index = len(self.images["retro" if self.controller.retro else "normal"]) - 1
        self.image_selected = self.images["retro" if self.controller.retro else "normal"][self.image_index].copy()
        self.img_rect = pygame.Rect(self.rect.x + (self.rect.width - self.image_selected.get_width()) // 2, self.rect.y + self.rect.height - (self.buttons[0].normal.get_height() * max(1, len(self.buttons) // 2)) - self.image_selected.get_height(), self.image_selected.get_width(), self.image_selected.get_height())

    def set_alpha(self, alpha: int) -> None:
        self.image_selected.set_alpha(alpha)
        super().set_alpha(alpha)

    def draw(self) -> None:
        super().draw()
        self.controller.win.blit(self.image_selected, (self.img_rect.x, self.img_rect.y))
