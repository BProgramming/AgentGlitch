from __future__ import annotations
from typing import Any, TYPE_CHECKING
import time
import pygame
from enum import Enum
from Helpers import (
    load_images,
    validate_file_list,
    handle_exception,
    image_to_retro,
    NORMAL_BLACK,
    NORMAL_WHITE,
    RETRO_BLACK,
    RETRO_WHITE,
)

if TYPE_CHECKING:
    from Controller import Controller


class ButtonType(Enum):
    CLICK = 1
    BAR   = 2


class Button:
    def __init__(
            self:            Button,
            controller:      Controller,
            x:               float,
            y:               float,
            width:           float,
            height:          float,
            value:           object,
            img_normal:      pygame.Surface | None = None,
            img_mouseover:   pygame.Surface | None = None,
            label_normal:    pygame.Surface | None = None,
            label_mouseover: pygame.Surface | None = None,
    ) -> None:
        """Initialize a button with its normal/mouseover images for both colour schemes."""
        self.rect:         pygame.Rect = pygame.Rect(x, y, width, height)
        self.controller:   Controller  = controller
        self.value:        Any         = value

        self._normal:      dict[str, pygame.Surface] = {"normal": self.__make__(img_normal, label_normal), "mouseover": self.__make__(img_mouseover, label_mouseover)}
        self._retro:       dict[str, pygame.Surface] = {key: image_to_retro(value) for key, value in self._normal.items()}

        self.is_mouseover: bool = False
        self.is_focused:   bool = False
        self.is_enabled:   bool = True

    def __make__(
            self:  Button,
            image: pygame.Surface | None,
            label: pygame.Surface | None,
    ) -> pygame.Surface:
        """Compose a button surface from a background image and a centred label."""
        if image is None:
            image = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            image.fill(RETRO_BLACK if self.controller.retro else NORMAL_BLACK)
        else:
            image = image.copy()

        if label is None:
            return image
        else:
            image.blit(label, ((image.get_width() - label.get_width()) // 2, (image.get_height() - label.get_height()) // 2))
            return image

    def __get_image__(
            self: Button,
            name: str,
    ) -> pygame.Surface:
        """Return the normal or mouseover image for the active colour scheme."""
        if self.controller.retro:
            return self._retro[name]
        else:
            return self._normal[name]

    def set_alpha(
            self:  Button,
            alpha: int,
    ) -> None:
        """Set the button's alpha, halving it when the button is disabled."""
        for key in self._normal.keys():
            self._normal[key].set_alpha(alpha // (2 - int(self.is_enabled)))
        for key in self._retro.keys():
            self._retro[key].set_alpha(alpha // (2 - int(self.is_enabled)))
        return None

    @property
    def normal(
            self: Button,
    ) -> pygame.Surface:
        """Return the button's normal-state image."""
        return self.__get_image__("normal")

    @property
    def mouseover(
            self: Button,
    ) -> pygame.Surface:
        """Return the button's mouseover-state image."""
        return self.__get_image__("mouseover")

    def draw(
            self: Button,
    ) -> None:
        """Blit the button, using the mouseover image when active and enabled."""
        active = (self.is_mouseover or self.is_focused) and self.is_enabled
        self.controller.win.blit(
            self.mouseover if active else self.normal,
            (self.rect.x, self.rect.y),
        )
        return None


class Bar(Button):
    def __init__(
            self:            Bar,
            controller:      Controller,
            x:               float,
            y:               float,
            width:           float,
            height:          float,
            value:           float,
            range:           tuple, # noqa
            snap:            bool                  = True,
            img_normal:      pygame.Surface | None = None,
            img_mouseover:   pygame.Surface | None = None,
            label_normal:    pygame.Surface | None = None,
            label_mouseover: pygame.Surface | None = None,
    ) -> None:
        """Initialize a slider bar with a value range and optional snapping."""
        super().__init__(controller, x, y, width, height, value, img_normal=img_normal, img_mouseover=img_mouseover, label_normal=label_normal, label_mouseover=label_mouseover)
        self.range    = range
        self.snap     = snap
        self.bar_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height / 10)

    @property
    def pct_val(
            self: Bar,
    ) -> float:
        """Return the bar's value as a fraction between its range endpoints."""
        return (self.value - self.range[0]) / (self.range[-1] - self.range[0])

    def __get_notch__(
            self: Bar,
            base: pygame.Surface,
    ) -> pygame.Surface:
        """Draw the slider track and value notch onto a copy of the base button image."""
        bar = pygame.Surface((base.get_width() - 50, base.get_height() / 10), pygame.SRCALPHA)
        bar.fill(RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
        base.blit(bar, ((base.get_width() - bar.get_width()) / 2, (base.get_height() - bar.get_height()) * 0.75))
        notch = pygame.Surface((base.get_height() / 10, base.get_height() / 5), pygame.SRCALPHA)
        notch.fill((137, 0, 0, 255) if self.controller.retro else (140, 0, 0, 255))
        base.blit(notch, (((base.get_width() - bar.get_width()) / 2) + (self.pct_val * bar.get_width()), (base.get_height() - bar.get_height() - (notch.get_height() / 2)) * 0.75))
        return base

    @property
    def normal(
            self: Bar,
    ) -> pygame.Surface:
        """Return the bar's normal-state image with the track and notch drawn on."""
        return self.__get_notch__(super().normal.copy())

    @property
    def mouseover(
            self: Bar,
    ) -> pygame.Surface:
        """Return the bar's mouseover-state image with the track and notch drawn on."""
        return self.__get_notch__(super().mouseover.copy())


class Menu:
    JOYSTICK_TOLERANCE = 3500

    def __init__(
            self:          Menu,
            controller:    Controller,
            header:        str | None,
            buttons:       list[dict],
            music:         list[str] | None = None,
            should_glitch: bool             = True,
    ) -> None:
        """Build a menu of clickable buttons and sliders under an optional header."""
        self.controller   = controller
        self.clear_normal = None
        self.clear_retro  = None
        self.focused_index: int              = 0
        self._joy_held:     tuple[int, int]  = (0, 0)    # (horiz, vert) direction held
        self._joy_repeat_timer: float        = 0.0       # time until next auto-repeat move
        images        = load_images("Menu", "Buttons")
        button_assets = {key: pygame.transform.smoothscale_by(value, 0.5) if value else None for key, value in images.items()} if images else {}
        button_width  = button_assets["BUTTON_NORMAL"].get_width()  if button_assets.get("BUTTON_NORMAL") else 0 # noqa
        button_height = button_assets["BUTTON_NORMAL"].get_height() if button_assets.get("BUTTON_NORMAL") else 0 # noqa
        if header is not None:
            text   = pygame.font.SysFont("courier", 32).render(header, True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, max(button_width, text.get_width())), (button_height * len(buttons)) + text.get_height() + 10), pygame.SRCALPHA)
            screen.fill(RETRO_BLACK if self.controller.retro else NORMAL_BLACK)
            screen.blit(text, ((screen.get_width() - text.get_width()) // 2, 5))
        else:
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, button_width), button_height * len(buttons)), pygame.SRCALPHA)
            screen.fill(RETRO_BLACK if self.controller.retro else NORMAL_BLACK)
        self.screen_normal = screen
        self.screen_retro  = image_to_retro(screen)
        self.rect          = pygame.Rect((self.controller.win.get_width() - screen.get_width()) // 2, (self.controller.win.get_height() - screen.get_height()) // 2, screen.get_width(), screen.get_height())

        self.buttons = []
        for i in range(len(buttons)):
            x     = (self.controller.win.get_width() - button_width) // 2
            y     = self.controller.win.get_height() - self.rect.y - ((len(buttons) - i) * button_height)
            label = pygame.font.SysFont("courier", 32).render(buttons[i]["label"], True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
            if buttons[i]["type"] == ButtonType.CLICK:
                button = Button(self.controller, x, y, button_width, button_height, i, img_normal=button_assets["BUTTON_NORMAL"], img_mouseover=button_assets["BUTTON_MOUSEOVER"], label_normal=label, label_mouseover=label)
            elif buttons[i]["type"] == ButtonType.BAR:
                button = Bar(self.controller, x, y, button_width, button_height, buttons[i]["value"], buttons[i]["range"], snap=buttons[i]["snap"], img_normal=button_assets["BUTTON_NORMAL"], img_mouseover=button_assets["BUTTON_MOUSEOVER"], label_normal=label, label_mouseover=label)
            else:
                button = None
            self.buttons.append(button)
        self.joystick_movement = (0, 0)

        self.music         = validate_file_list("Music", music, "mp3") if music else None
        self.music_index   = 0
        self.should_glitch = should_glitch
        self.glitch_timer  = 0
        self.glitches      = None

    def set_alpha(
            self:  Menu,
            alpha: int,
    ) -> None:
        """Set the alpha of every button and the menu's backing surfaces."""
        for button in self.buttons:
            button.set_alpha(alpha)
        self.screen_normal.set_alpha(alpha)
        self.screen_retro.set_alpha(alpha)
        return None

    def cycle_music(
            self: Menu,
    ) -> None:
        """Advance to the next menu music track, wrapping around."""
        if self.music is not None:
            self.music_index += 1
            if self.music_index >= len(self.music):
                self.music_index = 0
        return None

    def fade_in(
            self: Menu,
    ) -> None:
        """Fade the menu in over the current screen, snapping fully visible on input."""
        if self.clear_normal is None:
            self.clear_normal = pygame.display.get_surface().copy()
        if self.clear_retro is None:
            self.clear_retro = image_to_retro(self.clear_normal)

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
                    return None
            time.sleep(0.005)
        return None

    def fade_music(
            self: Menu,
    ) -> None:
        """Fade out current music or fade in this menu's music if none is playing."""
        if self.music:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
                pygame.mixer.music.unload()
            else:
                pygame.mixer.music.load(self.music[self.music_index])
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                pygame.mixer.music.play(fade_ms=2000)
                self.cycle_music()
                pygame.mixer.music.queue(self.music[self.music_index])
        return None

    def fade_out(
            self: Menu,
    ) -> None:
        """Fade the menu out, snapping fully hidden on input."""
        pygame.mouse.set_visible(False)
        if (self.controller.retro and self.clear_retro is None) or (not self.controller.retro and self.clear_normal is None):
            return None
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
                        return None
                time.sleep(0.005)
        return None

    def draw(
            self: Menu,
    ) -> None:
        """Draw the menu's backdrop, backing surface, and all buttons."""
        if self.clear_normal is None:
            self.clear_normal = pygame.display.get_surface().copy()
        if self.clear_retro is None:
            self.clear_retro = image_to_retro(self.clear_normal)

        self.controller.win.fill((0, 0, 0))
        clear = self.clear_retro if self.controller.retro else self.clear_normal
        self.controller.win.blit(clear, ((self.controller.win.get_width() - clear.get_width()) / 2, (self.controller.win.get_height() - clear.get_height()) / 2))
        screen = self.screen_retro if self.controller.retro else self.screen_normal
        self.controller.win.blit(screen, (self.rect.x, self.rect.y))
        for button in self.buttons:
            button.draw()
        return None

    def loop(
            self: Menu,
    ) -> int | None:
        """Process one frame of menu input and return a selected index, -1 for back, or None."""
        layout = (
            self.controller.GAMEPAD_LAYOUTS[self.controller.active_gamepad_layout]
            if self.controller.gamepad is not None and self.controller.active_gamepad_layout
            else None
        )
        gamepad = self.controller.gamepad

        # ── Analogue / D-pad input → move focus index ─────────────────────
        raw_dir = (0, 0)
        if gamepad and layout:
            vert  = gamepad.get_axis(layout["axis_vert"]) # noqa
            horiz = gamepad.get_axis(layout["axis_horiz"]) # noqa
            if abs(vert) > Menu.JOYSTICK_TOLERANCE:
                raw_dir = (0, 1 if vert > 0 else -1)
            elif abs(horiz) > Menu.JOYSTICK_TOLERANCE:
                raw_dir = (1 if horiz > 0 else -1, 0)
            elif gamepad.get_button(layout["button_up"]): # noqa
                raw_dir = (0, -1)
            elif gamepad.get_button(layout["button_down"]): # noqa
                raw_dir = (0, 1)
            elif gamepad.get_button(layout["button_right"]): # noqa
                raw_dir = (1, 0)
            elif gamepad.get_button(layout["button_left"]): # noqa
                raw_dir = (-1, 0)

        # Initial press or auto-repeat after hold delay.
        now         = time.monotonic()
        HOLD_DELAY  = 0.40  # noqa seconds before auto-repeat starts
        HOLD_REPEAT = 0.12  # noqa seconds between auto-repeat steps
        if raw_dir != (0, 0):
            if self._joy_held == (0, 0):
                # Fresh press — move immediately and start hold timer.
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_DELAY
                self._joy_held         = raw_dir
            elif raw_dir == self._joy_held and now >= self._joy_repeat_timer:
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_REPEAT
            elif raw_dir != self._joy_held:
                # Direction changed mid-hold — treat as new press.
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_DELAY
                self._joy_held         = raw_dir
        else:
            self._joy_held = (0, 0)

        # ── Mouse hover updates focus ──────────────────────────────────────
        pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.buttons):
            if button.is_enabled and button.rect.collidepoint(pos):
                self.focused_index = i
                break

        # Clamp to enabled buttons.
        self.focused_index = max(0, min(self.focused_index, len(self.buttons) - 1))

        # Update visual state.
        for i, button in enumerate(self.buttons):
            button.is_focused   = (i == self.focused_index)
            button.is_mouseover = (button.is_enabled and button.rect.collidepoint(pos))

        # ── Sliders: drag with mouse ───────────────────────────────────────
        focused_btn = self.buttons[self.focused_index]
        if isinstance(focused_btn, Bar) and pygame.mouse.get_pressed()[0]:
            pct = (pos[0] - focused_btn.bar_rect.x) / focused_btn.bar_rect.width
            if focused_btn.snap:
                dec = pct * focused_btn.range[-1]
                dec = max(focused_btn.range[0], min(focused_btn.range[-1], dec))
                for val in focused_btn.range:
                    if val >= dec:
                        focused_btn.value = val
                        break
            else:
                focused_btn.value = min(
                    focused_btn.range[-1],
                    max(focused_btn.range[0], pct * focused_btn.range[-1]),
                )

        # ── Event-driven confirmation ──────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Click confirms whichever button the mouse is over.
                for i, button in enumerate(self.buttons):
                    if button.is_enabled and button.rect.collidepoint(pos):
                        if isinstance(button, Bar):
                            return self._handle_bar_confirm(i, button)
                        return i

            elif event.type == pygame.KEYDOWN:
                kl = self.controller.KEYBOARD_LAYOUTS[self.controller.active_keyboard_layout]
                if event.key in kl["keys_crouch_uncrouch"] + kl.get("keys_down", []):
                    self._apply_focus_move((0, 1))
                elif event.key in kl["keys_jump"] + kl.get("keys_up", []):
                    self._apply_focus_move((0, -1))
                elif event.key in kl["keys_right"]:
                    self._apply_focus_move((1, 0))
                elif event.key in kl["keys_left"]:
                    self._apply_focus_move((-1, 0))
                elif event.key in kl["keys_pause_unpause"]:
                    return -1
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if isinstance(focused_btn, Bar):
                        return self._handle_bar_confirm(self.focused_index, focused_btn)
                    return self.focused_index

            elif event.type == pygame.JOYBUTTONDOWN and layout is not None:
                if event.button == layout["button_jump"]: # noqa
                    if isinstance(focused_btn, Bar):
                        return self._handle_bar_confirm(self.focused_index, focused_btn)
                    return self.focused_index
                elif event.button == layout["button_crouch_uncrouch"]: # noqa
                    return -1

        return None

    def _apply_focus_move(
            self:      Menu,
            direction: tuple[int, int],
    ) -> None:
        """Move self.focused_index by one step in the given direction."""
        _, vert    = direction
        horiz, _   = direction
        if isinstance(self, Selector):
            half = len(self.buttons) // 2
            if vert > 0 and self.focused_index < half - 1:
                self.focused_index += 1
            elif vert < 0 and self.focused_index > 0: # noqa
                self.focused_index -= 1
            elif horiz != 0:
                # Left/right navigates between the two columns of a Selector.
                other = self.focused_index + (1 if horiz > 0 else -1)
                if 0 <= other < len(self.buttons):
                    self.focused_index = other
        else:
            if vert > 0 and self.focused_index < len(self.buttons) - 1:
                self.focused_index += 1
            elif vert < 0 and self.focused_index > 0: # noqa
                self.focused_index -= 1
        return None

    def _handle_bar_confirm(
            self:   Menu,
            i:      int,
            button: Bar,
    ) -> int | None:
        """Handle a confirmation press on a slider, returning its index to the caller."""
        # For now just return the index so the caller knows which bar was activated.
        return i

    def set_mouse_pos(
            self: Menu,
            i:    int,
    ) -> None:
        """Set the focused button index (kept for backward compatibility)."""
        self.focused_index = max(0, min(i, len(self.buttons) - 1))
        return None


class Selector(Menu):
    def __init__(  # noqa
            self:          Selector,
            controller:    Controller,
            header:        str | None,
            note:          list[str] | None,
            images:        dict | list,
            values:        list,
            index:         int              = 0,
            music:         list[str] | None = None,
            should_glitch: bool             = True,
            accept_only:   bool             = False,
    ) -> None:
        """Build an image selector with arrow/accept/back buttons and a cycled image set."""
        self.controller   = controller
        self.clear_normal = None
        self.clear_retro  = None
        button_assets = {key: pygame.transform.smoothscale_by(value, 0.5) for key, value in load_images("Menu", "Buttons").items()} # noqa
        button_width  = button_assets["HALF_BUTTON_NORMAL"].get_width()
        button_height = button_assets["HALF_BUTTON_NORMAL"].get_height()

        arrow_asset   = pygame.transform.smoothscale_by(load_images("Menu", "Arrows")["ARROW_WHITE"], 0.5) # noqa

        max_image_width  = 0
        max_image_height = 0
        self.image_index = index
        if isinstance(images, dict):
            if list(images.keys()) != ["normal", "retro"]:
                handle_exception(f"Couldn't load picker sprites: {ValueError(images.keys())}")
            else:
                self.images = {}
                for key in images.keys():
                    self.images[key] = []
                    for i, image in enumerate(images[key]):
                        if image:
                            scale_val: int = min(image.get_width() / self.controller.win.get_width(), image.get_height() / self.controller.win.get_height())
                            if scale_val > 1:
                                image = pygame.transform.scale_by(image, 1 / scale_val)
                            max_image_width  = max(max_image_width, image.get_width())
                            max_image_height = max(max_image_height, image.get_height())
                            self.images[key].append(image)
                        else:
                            handle_exception(f"No picker sprite found for {key} at element {i}.")
        else:
            self.images = {"normal": [], "retro": []}
            for image in images:
                scale_val = min(image.get_width() / self.controller.win.get_width(), image.get_height() / self.controller.win.get_height())
                if scale_val > 1:
                    image = pygame.transform.scale_by(image, 1 / scale_val)
                max_image_width  = max(max_image_width, image.get_width())
                max_image_height = max(max_image_height, image.get_height())
                self.images["normal"].append(image)
                self.images["retro"].append(image_to_retro(image))

        self.note = []
        if note is not None:
            for line in note:
                self.note.append(pygame.font.SysFont("courier", 16).render(line, True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE))
        if header is not None:
            text   = pygame.font.SysFont("courier", 32).render(header, True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, max(max_image_width, button_width * 2, text.get_width())), max_image_height + (button_height * 2) + text.get_height() + (self.note[0].get_height() * len(self.note) if len(self.note) > 0 else 0) + 10), pygame.SRCALPHA)
            screen.fill(RETRO_BLACK if self.controller.retro else NORMAL_BLACK)
            screen.blit(text, ((screen.get_width() - text.get_width()) / 2, 5))
        else:
            screen = pygame.Surface((min(2 * self.controller.win.get_width() // 3, button_width * 2), max_image_height + (button_height * 2)), pygame.SRCALPHA)
            screen.fill(RETRO_BLACK if self.controller.retro else NORMAL_BLACK)
        self.screen_normal = screen
        self.screen_retro  = image_to_retro(screen)
        self.rect          = pygame.Rect((self.controller.win.get_width() - screen.get_width()) // 2, (self.controller.win.get_height() - screen.get_height()) // 2, screen.get_width(), screen.get_height())

        self.values = values

        self.buttons = []
        loop_range   = range(1 if accept_only else 4)
        for i in loop_range:
            normal    = button_assets["HALF_BUTTON_NORMAL"].copy()
            mouseover = button_assets["HALF_BUTTON_MOUSEOVER"].copy()

            if accept_only:
                label = pygame.font.SysFont("courier", 32).render("Accept", True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
            else:
                if i == 0:
                    label = pygame.transform.flip(arrow_asset, True, False)
                elif i == 1:
                    label = arrow_asset
                elif i == 2:
                    label = pygame.font.SysFont("courier", 32).render("Back", True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)
                else:
                    label = pygame.font.SysFont("courier", 32).render("Accept", True, RETRO_WHITE if self.controller.retro else NORMAL_WHITE)

            x = self.controller.win.get_width() // 2 - (button_width * (1 - i % 2))
            y = self.rect.y + self.rect.height - (button_height * ((len(loop_range) - i + 1) // 2))
            self.buttons.append(Button(self.controller, x, y, button_width, button_height, i, img_normal=normal, img_mouseover=mouseover, label_normal=label, label_mouseover=label))

        # focused_index navigation state (Selector doesn't call super().__init__
        # so these must be set explicitly here alongside joystick_movement)
        self.joystick_movement  = (0, 0)   # kept for any legacy references
        self.focused_index: int = 0
        self._joy_held:     tuple[int, int] = (0, 0)
        self._joy_repeat_timer: float       = 0.0

        self.music         = (None if music is None else validate_file_list("Music", music, "mp3"))
        self.music_index   = 0
        self.should_glitch = should_glitch
        self.glitch_timer  = 0
        self.glitches      = None
        self.cycle_images(0)

    def _apply_focus_move(
            self:      Selector,
            direction: tuple[int, int],
    ) -> None:
        """Navigate the 2x2 button grid (or single button for accept-only selectors)."""
        horiz, vert = direction
        n = len(self.buttons)
        if n == 1:
            return None  # accept_only: nothing to navigate

        row = self.focused_index // 2
        col = self.focused_index % 2

        if horiz > 0 and col == 0:
            self.focused_index += 1
        elif horiz < 0 and col == 1:
            self.focused_index -= 1
        elif vert > 0 and row == 0:
            self.focused_index += 2   # move down to back/accept row
        elif vert < 0 and row == 1:
            self.focused_index -= 2   # move up to arrows row
        return None

    def loop(
            self: Selector,
    ) -> int | None:
        """Process one frame of selector input and return a button index, -1 for back, or None."""
        layout = (
            self.controller.GAMEPAD_LAYOUTS[self.controller.active_gamepad_layout]
            if self.controller.gamepad is not None and self.controller.active_gamepad_layout
            else None
        )
        gamepad = self.controller.gamepad

        # ── Directional input ──────────────────────────────────────────────
        raw_dir = (0, 0)
        if gamepad is not None and layout is not None:
            horiz = gamepad.get_axis(layout["axis_horiz"]) # noqa
            vert  = gamepad.get_axis(layout["axis_vert"]) # noqa
            if abs(horiz) > Menu.JOYSTICK_TOLERANCE:
                raw_dir = (1 if horiz > 0 else -1, 0)
            elif abs(vert) > Menu.JOYSTICK_TOLERANCE:
                raw_dir = (0, 1 if vert > 0 else -1)
            elif gamepad.get_button(layout["button_right"]): # noqa
                raw_dir = (1, 0)
            elif gamepad.get_button(layout["button_left"]): # noqa
                raw_dir = (-1, 0)
            elif gamepad.get_button(layout["button_up"]): # noqa
                raw_dir = (0, -1)
            elif gamepad.get_button(layout["button_down"]): # noqa
                raw_dir = (0, 1)

        HOLD_DELAY  = 0.40 # noqa
        HOLD_REPEAT = 0.12 # noqa
        now = time.monotonic()

        if raw_dir != (0, 0):
            if self._joy_held == (0, 0):
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_DELAY
                self._joy_held         = raw_dir
            elif raw_dir == self._joy_held and now >= self._joy_repeat_timer:
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_REPEAT
            elif raw_dir != self._joy_held:
                self._apply_focus_move(raw_dir)
                self._joy_repeat_timer = now + HOLD_DELAY
                self._joy_held         = raw_dir
            # Horizontal movement on the arrows row (buttons 0/1) cycles
            # images immediately without needing a separate confirm press.
            if raw_dir[0] != 0 and self.focused_index < 2 and len(self.buttons) > 1:
                return self.focused_index
        else:
            self._joy_held = (0, 0)

        # ── Mouse hover updates focus ──────────────────────────────────────
        pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.buttons):
            if button.is_enabled and button.rect.collidepoint(pos):
                self.focused_index = i
                break

        self.focused_index = max(0, min(self.focused_index, len(self.buttons) - 1))
        for i, button in enumerate(self.buttons):
            button.is_focused   = (i == self.focused_index and button.is_enabled)
            button.is_mouseover = (button.is_enabled and button.rect.collidepoint(pos))

        # ── Events ────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, button in enumerate(self.buttons):
                    if button.is_enabled and button.rect.collidepoint(pos):
                        return i

            elif event.type == pygame.KEYDOWN:
                kl = self.controller.KEYBOARD_LAYOUTS[self.controller.active_keyboard_layout]
                if event.key in kl["keys_right"]:
                    self._apply_focus_move((1, 0))
                    if self.focused_index < 2 and len(self.buttons) > 1:
                        return self.focused_index
                elif event.key in kl["keys_left"]:
                    self._apply_focus_move((-1, 0))
                    if self.focused_index < 2 and len(self.buttons) > 1:
                        return self.focused_index
                elif event.key in kl["keys_crouch_uncrouch"]:
                    self._apply_focus_move((0, 1))
                elif event.key in kl["keys_jump"]:
                    self._apply_focus_move((0, -1))
                elif event.key in kl["keys_pause_unpause"]:
                    return -1
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return self.focused_index

            elif event.type == pygame.JOYBUTTONDOWN and layout is not None:
                if event.button == layout["button_jump"]: # noqa
                    return self.focused_index
                elif event.button == layout["button_crouch_uncrouch"]: # noqa
                    return -1

        return None

    def set_index(
            self:  Selector,
            index: int,
    ) -> None:
        """Set the currently displayed image index and selected image."""
        self.image_index    = index
        self.image_selected = self.images["retro" if self.controller.retro else "normal"][index] # noqa
        return None

    def cycle_images(
            self:      Selector,
            direction: int,
    ) -> None:
        """Cycle the displayed image in the given direction and recompute its placement."""
        if direction > 0:
            self.image_index += 1
        elif direction < 0:
            self.image_index -= 1
        if self.image_index >= len(self.images["retro" if self.controller.retro else "normal"]):
            self.image_index = 0
        elif self.image_index < 0:
            self.image_index = len(self.images["retro" if self.controller.retro else "normal"]) - 1
        self.image_selected = self.images["retro" if self.controller.retro else "normal"][self.image_index].copy() # noqa
        self.img_rect       = pygame.Rect(self.rect.x + (self.rect.width - self.image_selected.get_width()) // 2, self.rect.y + self.rect.height - (self.buttons[0].normal.get_height() * max(1, len(self.buttons) // 2)) - self.image_selected.get_height(), self.image_selected.get_width(), self.image_selected.get_height()) # noqa
        return None

    def set_alpha(
            self:  Selector,
            alpha: int,
    ) -> None:
        """Set the alpha of the selected image and all buttons."""
        self.image_selected.set_alpha(alpha)
        super().set_alpha(alpha)
        return None

    def draw(
            self: Selector,
    ) -> None:
        """Draw the menu chrome and the currently selected image."""
        super().draw()
        self.controller.win.blit(self.image_selected, (self.img_rect.x, self.img_rect.y))
        return None
