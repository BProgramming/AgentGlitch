import random
import time
import pygame
import pygame._sdl2.controller
import sys
from Menu import Menu, Selector, ButtonType
from Helpers import display_text, DifficultyScale, load_images, load_level_images, load_picker_sprites, \
    make_image_from_text, NORMAL_WHITE, RETRO_WHITE
from SaveLoadFunctions import save, save_player_profile


class Controller:
    KEYBOARD_LAYOUTS = {"ARROW_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_LEFT], "keys_right": [pygame.K_RIGHT], "keys_crouch_uncrouch": [pygame.K_DOWN], "keys_jump": [pygame.K_UP], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS], "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_d], "keys_block": [pygame.K_a], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]},
                        "WASD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_a], "keys_right": [pygame.K_d], "keys_crouch_uncrouch": [pygame.K_s], "keys_jump": [pygame.K_w], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS], "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_LEFT, pygame.K_KP4], "keys_block": [pygame.K_RIGHT, pygame.K_KP6], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_UP, pygame.K_KP8], "keys_shrink": [pygame.K_DOWN, pygame.K_KP5]},
                        "NUMPAD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_KP4], "keys_right": [pygame.K_KP6], "keys_crouch_uncrouch": [pygame.K_KP5], "keys_jump": [pygame.K_KP8], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS],  "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_d], "keys_block": [pygame.K_a], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]},
                        "ALT_NUMPAD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_KP4], "keys_right": [pygame.K_KP6], "keys_crouch_uncrouch": [pygame.K_KP5], "keys_jump": [pygame.K_KP8], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS],  "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_a], "keys_block": [pygame.K_d], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]}}
    GAMEPAD_LAYOUTS = {"SWITCH PRO": {"button_up": pygame.CONTROLLER_BUTTON_DPAD_UP, "button_down": pygame.CONTROLLER_BUTTON_DPAD_DOWN, "button_quicksave": pygame.CONTROLLER_BUTTON_BACK, "button_left": pygame.CONTROLLER_BUTTON_DPAD_LEFT, "button_right": pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "axis_vert": pygame.CONTROLLER_AXIS_LEFTY, "axis_horiz": pygame.CONTROLLER_AXIS_LEFTX, "button_crouch_uncrouch": pygame.CONTROLLER_BUTTON_B, "button_jump": pygame.CONTROLLER_BUTTON_A, "button_teleport_dash": pygame.CONTROLLER_BUTTON_X, "button_pause_unpause": pygame.CONTROLLER_BUTTON_START, "axis_attack": pygame.CONTROLLER_AXIS_TRIGGERRIGHT, "axis_block": pygame.CONTROLLER_AXIS_TRIGGERLEFT, "button_bullet_time": pygame.CONTROLLER_BUTTON_Y, "button_grow": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, "button_shrink": pygame.CONTROLLER_BUTTON_LEFTSHOULDER},
                        "XBOX": {"button_up": pygame.CONTROLLER_BUTTON_DPAD_UP, "button_down": pygame.CONTROLLER_BUTTON_DPAD_DOWN, "button_quicksave": pygame.CONTROLLER_BUTTON_BACK, "button_left": pygame.CONTROLLER_BUTTON_DPAD_LEFT, "button_right": pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "axis_vert": pygame.CONTROLLER_AXIS_LEFTY, "axis_horiz": pygame.CONTROLLER_AXIS_LEFTX, "button_crouch_uncrouch": pygame.CONTROLLER_BUTTON_B, "button_jump": pygame.CONTROLLER_BUTTON_A, "button_teleport_dash": pygame.CONTROLLER_BUTTON_X, "button_pause_unpause": pygame.CONTROLLER_BUTTON_START, "axis_attack": pygame.CONTROLLER_AXIS_TRIGGERRIGHT, "axis_block": pygame.CONTROLLER_AXIS_TRIGGERLEFT, "button_bullet_time": pygame.CONTROLLER_BUTTON_Y, "button_grow": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, "button_shrink": pygame.CONTROLLER_BUTTON_LEFTSHOULDER},
                        "PS4": {"button_up": pygame.CONTROLLER_BUTTON_DPAD_UP, "button_down": pygame.CONTROLLER_BUTTON_DPAD_DOWN, "button_quicksave": pygame.CONTROLLER_BUTTON_BACK, "button_left": pygame.CONTROLLER_BUTTON_DPAD_LEFT, "button_right": pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "axis_vert": pygame.CONTROLLER_AXIS_LEFTY, "axis_horiz": pygame.CONTROLLER_AXIS_LEFTX, "button_crouch_uncrouch": pygame.CONTROLLER_BUTTON_B, "button_jump": pygame.CONTROLLER_BUTTON_A, "button_teleport_dash": pygame.CONTROLLER_BUTTON_X, "button_pause_unpause": pygame.CONTROLLER_BUTTON_START, "axis_attack": pygame.CONTROLLER_AXIS_TRIGGERRIGHT, "axis_block": pygame.CONTROLLER_AXIS_TRIGGERLEFT, "button_bullet_time": pygame.CONTROLLER_BUTTON_Y, "button_grow": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, "button_shrink": pygame.CONTROLLER_BUTTON_LEFTSHOULDER},
                        "PS5": {"button_up": pygame.CONTROLLER_BUTTON_DPAD_UP, "button_down": pygame.CONTROLLER_BUTTON_DPAD_DOWN, "button_quicksave": pygame.CONTROLLER_BUTTON_BACK, "button_left": pygame.CONTROLLER_BUTTON_DPAD_LEFT, "button_right": pygame.CONTROLLER_BUTTON_DPAD_RIGHT, "axis_vert": pygame.CONTROLLER_AXIS_LEFTY, "axis_horiz": pygame.CONTROLLER_AXIS_LEFTX, "button_crouch_uncrouch": pygame.CONTROLLER_BUTTON_B, "button_jump": pygame.CONTROLLER_BUTTON_A, "button_teleport_dash": pygame.CONTROLLER_BUTTON_X, "button_pause_unpause": pygame.CONTROLLER_BUTTON_START, "axis_attack": pygame.CONTROLLER_AXIS_TRIGGERRIGHT, "axis_block": pygame.CONTROLLER_AXIS_TRIGGERLEFT, "button_bullet_time": pygame.CONTROLLER_BUTTON_Y, "button_grow": pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, "button_shrink": pygame.CONTROLLER_BUTTON_LEFTSHOULDER},
                        "NONE": {"button_up": None, "button_down": None, "button_quicksave": None, "button_left": None, "button_right": None, "axis_horiz": None, "hat_horiz": None, "button_crouch_uncrouch": None, "button_jump": None, "button_teleport_dash": None, "button_pause_unpause": None, "axis_attack": None, "axis_block": None, "button_bullet_time": None, "button_grow": None, "button_shrink": None}}
    JOYSTICK_TOLERANCE = 3500

    def __init__(self, level, win, layout=None, main_menu_music=None, steamworks=None, discord=None):
        self.win = win
        self.steamworks = steamworks.connection
        self.discord = discord
        self.should_store_steam_stats = False
        self.player_sprite_selected = None
        self.start_level: str | None = None
        self.difficulty = DifficultyScale.MEDIUM
        self.hud = None
        self.goto_load = self.goto_main = self.goto_restart = False
        self.has_dlc: dict[str, bool] = steamworks.has_dlc()
        self.force_retro: bool = False
        self.level = level
        self.next_level = None
        self.master_volume: dict[str, float] = {"master": 1.0, "background": 1.0, "player": 1.0, "non-player": 1.0, "cinematics": 1.0}
        dif = {"label": "Difficulty", "type": ButtonType.BAR, "snap": True, "value": self.difficulty, "range": (float(DifficultyScale.EASIEST), float(DifficultyScale.EASY), float(DifficultyScale.MEDIUM), float(DifficultyScale.HARD), float(DifficultyScale.HARDEST))}
        vol_mt = {"label": "Master volume", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["master"], "range": (0, 100)}
        vol_bg = {"label": "Music", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["background"], "range": (0, 100)}
        vol_pc = {"label": "Player", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["player"], "range": (0, 100)}
        vol_fx = {"label": "Effects", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["non-player"], "range": (0, 100)}
        vol_cn = {"label": "Cinematics", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["cinematics"], "range": (0, 100)}
        if self.has_dlc.get("gumshoe") is not None and self.has_dlc["gumshoe"]:
            self.main_menu = Menu(self, None, [{"label": "New game", "type": ButtonType.CLICK}, {"label": "Continue", "type": ButtonType.CLICK}, {"label": "Select a level", "type": ButtonType.CLICK}, {"label": "Settings", "type": ButtonType.CLICK}, {"label": "Toggle retro style", "type": ButtonType.CLICK}, {"label": "Quit to desktop", "type": ButtonType.CLICK}], music=main_menu_music)
        else:
            self.main_menu = Menu(self, None, [{"label": "New game", "type": ButtonType.CLICK}, {"label": "Continue", "type": ButtonType.CLICK}, {"label": "Select a level", "type": ButtonType.CLICK}, {"label": "Settings", "type": ButtonType.CLICK}, {"label": "Quit to desktop", "type": ButtonType.CLICK}], music=main_menu_music)
        self.pause_menu = Menu(self, "PAUSED", [{"label": "Resume", "type": ButtonType.CLICK}, {"label": "Load last save", "type": ButtonType.CLICK}, {"label": "Restart level", "type": ButtonType.CLICK}, {"label": "Settings", "type": ButtonType.CLICK}, {"label": "Quit to menu", "type": ButtonType.CLICK}, {"label": "Quit to desktop", "type": ButtonType.CLICK}])
        self.settings_menu = Menu(self, "SETTINGS", [dif, {"label": "Controls", "type": ButtonType.CLICK}, {"label": "Volume", "type": ButtonType.CLICK}, {"label": "Toggle fullscreen", "type": ButtonType.CLICK}, {"label": "Back", "type": ButtonType.CLICK}])
        self.volume_menu = Menu(self, "VOLUME", [vol_mt, vol_bg, vol_pc, vol_fx, vol_cn, {"label": "Back", "type": ButtonType.CLICK}])
        self.controls_menu = Menu(self, "CONTROLS", [{"label": "Keyboard", "type": ButtonType.CLICK}, {"label": "Controller", "type": ButtonType.CLICK}, {"label": "Back", "type": ButtonType.CLICK}])
        difficulty_images = [make_image_from_text(256, 128, "EASIEST", ["Agent is much stronger", "Agent can survive huge falls", "Enemies are much weaker", "Enemy sight ranges are visible"], border=5), make_image_from_text(256, 128, "EASY", ["Agent is stronger", "Agent can survive big falls", "Enemies are weaker", "Enemy sight ranges are visible"], border=5), make_image_from_text(256, 128, "MEDIUM", ["Agent is normal strength", "Agent can survive moderate falls", "Enemies are normal strength", "Enemy sight ranges are not visible"], border=5), make_image_from_text(256, 128, "HARD", ["Agent is weaker", "Agent can survive small falls", "Enemies are stronger", "Enemy sight ranges are not visible"], border=5), make_image_from_text(256, 128, "HARDEST", ["Agent is much weaker", "Agent can survive tiny falls", "Enemies are much stronger", "Enemy sight ranges are not visible"], border=5)]
        self.difficulty_picker = Selector(self, "CHOOSE DIFFICULTY", ["You can change this at any time."], difficulty_images, [DifficultyScale.EASIEST, DifficultyScale.EASY, DifficultyScale.MEDIUM, DifficultyScale.HARD, DifficultyScale.HARDEST], index=2)
        sprite_images, sprite_values = load_picker_sprites("Sprites")
        self.sprite_picker = Selector(self, "CHOOSE PLAYER", ["This is a visual choice only.", "Anyone can be an Agent."], sprite_images, sprite_values, index=2 * random.randrange(0, len(sprite_images['normal']) // 2))
        self.level_selected = None
        level_images, level_values = load_level_images("LevelImages")
        self.level_picker = Selector(self, "CHOOSE LEVEL", None, level_images, level_values)
        if layout is None:
            self.set_keyboard_layout("ARROW_MOVE")
        else:
            self.set_keyboard_layout(layout)
        self.gamepad = None
        self.active_gamepad_layout = None
        self.keyboard_layout_picker = Selector(self, "KEYBOARD LAYOUT", ["This can be cycled with the F9 key."], load_images("Menu", "Keyboards").values(), list(self.KEYBOARD_LAYOUTS.keys()))
        self.gamepad_layout_picker = Selector(self, "CONTROLLER LAYOUT", ["This is detected when you connect a controller."], load_images("Menu", "Controllers").values(), list(self.GAMEPAD_LAYOUTS.keys()), accept_only=True)
        self.music = None
        self.music_index = 0
        self.should_hot_swap_level = False
        self.should_scroll_to_point = None
        self.active_objective: str | None = None

    def activate_objective(self, text: str | None, popup: bool=True) -> None:
        if text is not None and self.hud is not None:
            if popup:
                display_text(f'New objective: {text}', self, retro=self.retro)
            self.active_objective = text
        self.hud.activate_objective(self.active_objective)

    def refresh_selector_images(self) -> None:
        for sel in [self.difficulty_picker, self.sprite_picker, self.level_picker, self.keyboard_layout_picker, self.gamepad_layout_picker]:
            sel.cycle_images(0)

    @property
    def retro(self) -> bool:
        return self.force_retro or (self.level is not None and self.level.retro)

    def save(self):
        save(self.level, self.hud, self)

    def save_player_profile(self):
        save_player_profile(self, self.level)

    def quit(self):
        self.save_player_profile()
        self.discord.close()
        if pygame._sdl2.controller.get_init():
            pygame._sdl2.controller.quit()
        if pygame.get_init():
            pygame.quit()
        sys.exit()

    def queue_track_list(self, music=None) -> None:
        if music is None:
            self.music = self.level.music
        else:
            self.music = music
        self.music_index = 0
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.queue(self.music[self.music_index])
        else:
            pygame.mixer.music.load(self.music[self.music_index])

    def cycle_music(self) -> None:
        if self.music is not None:
            self.music_index += 1
            if self.music_index >= len(self.music):
                self.queue_track_list()
            else:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.queue(self.music[self.music_index])
                else:
                    pygame.mixer.music.load(self.music[self.music_index])

    def set_difficulty(self) -> None:
        if self.level is not None:
            for ent in self.level.entities:
                ent.set_difficulty(self.difficulty)

    def disable_gamepad(self, notify=True) -> float:
        start = time.perf_counter()
        if self.gamepad is not None:
            self.gamepad.quit()
            self.gamepad = None
            self.set_gamepad_layout("NONE")
            if notify:
                display_text("Controller disconnected.", self, retro=self.retro)
        return time.perf_counter() - start

    def enable_gamepad(self, notify=True) -> float:
        start = time.perf_counter()
        if not pygame._sdl2.controller.get_init():
            pygame._sdl2.controller.init()
        self.gamepad = pygame._sdl2.controller.Controller(pygame._sdl2.controller.get_count() - 1)
        self.gamepad.init()
        match self.gamepad.name:
            case "Nintendo Switch Pro Controller":
                self.set_gamepad_layout("SWITCH PRO")
                msg = "Nintendo Switch controller detected."
            case "Controller (Xbox One For Windows)" | "Xbox One Game Controller":
                self.set_gamepad_layout("XBOX")
                msg = "Xbox controller detected."
            case "PS4 Controller":
                self.set_gamepad_layout("PS4")
                msg = "PS4 controller detected."
            case "Sony Interactive Entertainment Wireless Controller":
                self.set_gamepad_layout("PS5")
                msg = "PS5 controller detected."
            case "Wireless Gamepad":
                self.set_gamepad_layout("NONE")
                msg = "Nintendo Switch Joy-Con detected.\nIndividual Joy-Cons are not supported. Please connect the full controller."
            case _:
                self.set_gamepad_layout("XBOX")
                msg = "Unrecognized controller. Using default XBOX controller mapping."

        if notify:
            display_text([msg, 'Changing controllers during gameplay can confuse the system.', 'If controls behave strangely, try restarting with the controller connected.'], self, retro=self.retro)
        return time.perf_counter() - start

    def set_keyboard_layout(self, name) -> None:
        self.active_keyboard_layout = name

    def set_gamepad_layout(self, name) -> None:
        self.active_gamepad_layout = (None if name == "NONE" else name)

    def pick_from_selector(self, selector, clear_normal=None, clear_retro=None) -> bool:
        selector.fade_in()
        selector.clear_normal = clear_normal
        selector.clear_retro = clear_retro
        while True:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.save()
                        self.quit()
                    case pygame.KEYDOWN:
                        if event.key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return False
                    case pygame.JOYBUTTONDOWN:
                        if event.button == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return False
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            selector.draw()
            pygame.display.update()
            val = selector.loop()

            if len(selector.buttons) > 1:
                match val:
                    case 0:
                        selector.cycle_images(-1)
                    case 1:
                        selector.cycle_images(1)
                    case 2 | -1:
                        selector.fade_out()
                        return False
                    case 3:
                        selector.fade_out()
                        return True
                    case _:
                        pass
            else:
                match val:
                    case 0:
                        selector.fade_out()
                        return False
                    case _:
                        pass

    def volume(self, clear_normal=None, clear_retro=None) -> None:
        self.volume_menu.buttons[0].value = self.master_volume["master"] * 100
        self.volume_menu.buttons[1].value = self.master_volume["background"] * 100
        self.volume_menu.buttons[2].value = self.master_volume["player"] * 100
        self.volume_menu.buttons[3].value = self.master_volume["non-player"] * 100
        self.volume_menu.buttons[4].value = self.master_volume["cinematics"] * 100

        self.volume_menu.fade_in()
        self.volume_menu.clear_normal = clear_normal
        self.volume_menu.clear_retro = clear_retro

        mt_notch = self.volume_menu.buttons[0].value
        bg_notch = self.volume_menu.buttons[1].value
        while True:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.save()
                        self.quit()
                    case pygame.KEYDOWN:
                        if event.key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYBUTTONDOWN:
                        if event.button == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            if mt_notch != self.volume_menu.buttons[0].value:
                mt_notch = self.volume_menu.buttons[0].value
                for button in self.volume_menu.buttons[1:5]:
                    button.value = mt_notch
                for key in self.master_volume.keys():
                    self.master_volume[key] = mt_notch / 100
            elif bg_notch != self.volume_menu.buttons[1].value:
                bg_notch = self.volume_menu.buttons[1].value
                self.master_volume["background"] = bg_notch / 100
                pygame.mixer.music.set_volume(self.master_volume["background"])

            self.volume_menu.draw()
            pygame.display.update()
            val = self.volume_menu.loop()

            match val:
                case 0:
                    pass  #set master volume
                case 1:
                    pass  #set background music volume
                case 2:
                    pass  #set player volume
                case 3:
                    pass  #set effects volume
                case 4:
                    pass  #set cinematics volume
                case 5 | -1:
                    self.volume_menu.fade_out()
                    self.master_volume["player"] = self.volume_menu.buttons[2].value / 100
                    self.master_volume["non-player"] = self.volume_menu.buttons[3].value / 100
                    self.master_volume["cinematics"] = self.volume_menu.buttons[4].value / 100
                    return
                case _:
                    pass

    def controls(self, clear_normal=None, clear_retro=None) -> None:
        self.controls_menu.buttons[1].is_enabled = bool(self.gamepad is not None)

        self.controls_menu.fade_in()
        self.controls_menu.clear_normal = clear_normal
        self.controls_menu.clear_retro = clear_retro

        while True:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.save()
                        self.quit()
                    case pygame.KEYDOWN:
                        if event.key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYBUTTONDOWN:
                        if event.button == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            if self.gamepad is not None:
                self.controls_menu.buttons[1].set_alpha(255)
            else:
                self.controls_menu.buttons[1].set_alpha(128)

            self.controls_menu.draw()
            pygame.display.update()
            val = self.controls_menu.loop()

            match val:
                case 0:
                    self.controls_menu.fade_out()
                    self.keyboard_layout_picker.set_index(self.keyboard_layout_picker.values.index(self.active_keyboard_layout))
                    if self.pick_from_selector(self.keyboard_layout_picker, clear_normal=self.controls_menu.clear_normal, clear_retro=self.controls_menu.clear_retro):
                        self.set_keyboard_layout(self.keyboard_layout_picker.values[self.keyboard_layout_picker.image_index])
                    self.controls_menu.fade_in()
                case 1:
                    if self.controls_menu.buttons[1].is_enabled:
                        self.controls_menu.fade_out()
                        self.gamepad_layout_picker.set_index(self.gamepad_layout_picker.values.index(self.active_gamepad_layout))
                        self.pick_from_selector(self.gamepad_layout_picker, clear_normal=self.controls_menu.clear_normal, clear_retro=self.controls_menu.clear_retro)
                        self.controls_menu.fade_in()
                case 2 | -1:
                    self.controls_menu.fade_out()
                    return
                case _:
                    pass

    def settings(self, clear_normal=None, clear_retro=None) -> None:
        self.settings_menu.buttons[0].value = self.difficulty

        self.settings_menu.fade_in()
        self.settings_menu.clear_normal = clear_normal
        self.settings_menu.clear_retro = clear_retro
        while True:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.save()
                        self.quit()
                    case pygame.KEYDOWN:
                        if event.key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYBUTTONDOWN:
                        if event.button == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']:
                            pygame.mouse.set_visible(False)
                            return
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            self.settings_menu.draw()
            pygame.display.update()
            val = self.settings_menu.loop()

            match val:
                case 0:
                    pass #set difficulty
                case 1:
                    self.controls(clear_normal=self.settings_menu.clear_normal, clear_retro=self.settings_menu.clear_retro)
                case 2:
                    time.sleep(0.01)
                    self.volume(clear_normal=self.settings_menu.clear_normal, clear_retro=self.settings_menu.clear_retro)
                case 3:
                    pygame.display.toggle_fullscreen()
                case 4 | -1:
                    self.settings_menu.fade_out()
                    self.difficulty = DifficultyScale(self.settings_menu.buttons[0].value)
                    self.set_difficulty()
                    return
                case _:
                    pass

    def pause(self) -> float:
        self.pause_menu.clear_normal = self.pause_menu.clear_retro = None
        start = time.perf_counter()
        pygame.mixer.pause()
        self.pause_menu.fade_in()

        paused = True
        while paused:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.save()
                        self.quit()
                    case pygame.KEYDOWN:
                        if event.key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause']:
                            paused = False
                    case pygame.JOYBUTTONDOWN:
                        if event.button == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']:
                            paused = False
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            if not paused:
                break

            self.pause_menu.draw()
            pygame.display.update()
            val = self.pause_menu.loop()

            match val:
                case 0 | -1:
                    paused = False
                case 1:
                    self.goto_load = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    return 0
                case 2:
                    self.goto_restart = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    return 0
                case 3:
                    time.sleep(0.01)
                    self.settings(clear_normal=self.pause_menu.clear_normal, clear_retro=self.pause_menu.clear_retro)
                case 4:
                    self.save()
                    self.save_player_profile()
                    self.goto_main = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    return 0
                case 5:
                    self.save()
                    self.quit()
                case _:
                    pass

        self.pause_menu.fade_out()
        pygame.mixer.unpause()
        return time.perf_counter() - start

    def main(self) -> bool:
        self.main_menu.fade_in()
        self.main_menu.fade_music()
        self.level_selected = None

        while True:
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        self.quit()
                    case pygame.USEREVENT:
                        if self.main_menu.music is not None:
                            if "LOOP" in self.main_menu.music[self.main_menu.music_index].upper():
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_endevent()
                            else:
                                pygame.mixer.music.play()
                                self.main_menu.cycle_music()
                                pygame.mixer.music.queue(self.main_menu.music[self.main_menu.music_index])
                    case pygame.JOYDEVICEADDED:
                        self.enable_gamepad(notify=True)
                        if self.gamepad is not None:
                            pygame.mouse.set_visible(False)
                    case pygame.JOYDEVICEREMOVED:
                        self.disable_gamepad(notify=True)
                        pygame.mouse.set_visible(True)
                    case pygame.MOUSEMOTION:
                        if not pygame.mouse.get_visible():
                            pygame.mouse.set_visible(True)
                    case _:
                        pass

            self.main_menu.draw()
            pygame.display.update()
            val = self.main_menu.loop()

            match val:
                case 0:
                    self.main_menu.fade_out()
                    while True:
                        if self.pick_from_selector(self.sprite_picker, clear_normal=self.main_menu.clear_normal, clear_retro=self.main_menu.clear_retro):
                            self.player_sprite_selected = self.sprite_picker.values[self.sprite_picker.image_index]
                            if self.pick_from_selector(self.difficulty_picker, clear_normal=self.main_menu.clear_normal, clear_retro=self.main_menu.clear_retro):
                                self.difficulty = self.difficulty_picker.values[self.difficulty_picker.image_index]
                                pygame.mouse.set_visible(False)
                                self.main_menu.fade_music()
                                return True
                            if self.gamepad is not None:
                                self.main_menu.set_mouse_pos(0)
                        else:
                            if self.gamepad is not None:
                                self.main_menu.set_mouse_pos(0)
                            break
                    self.main_menu.fade_in()
                case 1:
                    self.main_menu.fade_out()
                    self.goto_load = True
                    self.main_menu.fade_music()
                    return False
                case 2:
                    self.main_menu.fade_out()
                    if self.pick_from_selector(self.level_picker, clear_normal=self.main_menu.clear_normal, clear_retro=self.main_menu.clear_retro):
                        self.level_selected = self.level_picker.values[self.level_picker.image_index]
                        pygame.mouse.set_visible(False)
                        self.main_menu.fade_music()
                        return bool(self.level_picker.image_index == 0)
                    else:
                        if self.gamepad is not None:
                            self.main_menu.set_mouse_pos(0)
                        self.main_menu.fade_in()
                case 3:
                    time.sleep(0.01)
                    self.settings(clear_normal=self.main_menu.clear_normal, clear_retro=self.main_menu.clear_retro)
                case 4:
                    if self.has_dlc.get("gumshoe") is not None and self.has_dlc["gumshoe"]:
                        self.force_retro = not self.force_retro
                        self.sprite_picker.cycle_images(0)
                        self.difficulty_picker.cycle_images(0)
                        self.level_picker.cycle_images(0)
                        self.keyboard_layout_picker.cycle_images(0)
                        self.gamepad_layout_picker.cycle_images(0)
                    else:
                        self.quit()
                case 5:
                    if self.has_dlc.get("gumshoe") is not None and self.has_dlc["gumshoe"]:
                        self.quit()
                    else:
                        pass
                case _:
                    pass

    def cycle_keyboard_layout(self, win) -> float:
        start = time.perf_counter()
        if self.active_keyboard_layout == "ARROW_MOVE":
            self.set_keyboard_layout("WASD_MOVE")
            text = "Control layout changed to WASD movement (left hand move, right hand interact)."
        elif self.active_keyboard_layout == "WASD_MOVE":
            self.set_keyboard_layout("NUMPAD_MOVE")
            text = "Control layout changed to number pad movement (ideal for right hand move, left hand interact)."
        elif self.active_keyboard_layout == "NUMPAD_MOVE":
            self.set_keyboard_layout("ALT_NUMPAD_MOVE")
            text = "Control layout changed to number pad movement (ideal for left hand move, right hand interact)."
        elif self.active_keyboard_layout == "ALT_NUMPAD_MOVE":
            self.set_keyboard_layout("ARROW_MOVE")
            text = "Control layout changed to arrow movement (right hand move, left hand interact)."
        else:
            text = None

        if text is not None:
            display_text(text, self, retro=self.retro)

        return time.perf_counter() - start

    def handle_pause_unpause(self, key) -> float:
        if key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']):
            return self.pause()
        else:
            return 0.0

    def handle_any_key(self) -> bool:
        if any(pygame.key.get_pressed()):
            return True
        elif self.gamepad is not None:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    return True
        return False

    def handle_single_input(self, key, win) -> float:
        if key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_pause_unpause'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_pause_unpause']):
            return self.pause()
        elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_quicksave'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_quicksave']):
            self.save()
        elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_cycle_layout']:
            return self.cycle_keyboard_layout(win)
        elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_fullscreen_toggle']:
            pygame.display.toggle_fullscreen()
        elif self.should_scroll_to_point is None:
            if key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_crouch_uncrouch'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_crouch_uncrouch']):
                self.level.player.toggle_crouch()
            elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_jump'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_jump']):
                self.level.player.jump()
            elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_teleport_dash'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_teleport_dash']):
                self.level.player.teleport()
            elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_bullet_time'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_bullet_time']):
                self.level.player.bullet_time()
            elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_grow'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_grow']):
                self.level.player.grow()
            elif key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_shrink'] or (self.gamepad is not None and key == Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_shrink']):
                self.level.player.shrink()
        return 0.0

    def handle_continuous_input(self) -> float:
        dtime_offset: float = 0.0
        if self.should_scroll_to_point is not None:
            return 0.0

        player_is_moving = False
        player_is_attacking = False

        if self.gamepad is not None:
            stick = self.gamepad.get_axis(Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['axis_horiz'])
            if not player_is_moving and stick is not None:
                if stick > Controller.JOYSTICK_TOLERANCE:
                    player_is_moving = True
                    self.level.player.move_right()
                elif stick < -Controller.JOYSTICK_TOLERANCE:
                    player_is_moving = True
                    self.level.player.move_left()

            if not player_is_moving and Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_right'] is not None and Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_left'] is not None:
                if self.gamepad.get_button(Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_right']):
                    player_is_moving = True
                    self.level.player.move_right()
                elif self.gamepad.get_button(Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['button_left']):
                    player_is_moving = True
                    self.level.player.move_left()

            stick = self.gamepad.get_axis(Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['axis_attack'])
            if not player_is_attacking and stick is not None and stick > Controller.JOYSTICK_TOLERANCE:
                player_is_attacking = True
                dtime_offset += self.level.player.attack()

        keys = pygame.key.get_pressed()

        if not player_is_moving:
            for input_key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_right']:
                if keys[input_key]:
                    player_is_moving = True
                    self.level.player.move_right()
                    break
        if not player_is_moving:
            for input_key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_left']:
                if keys[input_key]:
                    player_is_moving = True
                    self.level.player.move_left()
                    break

        if not player_is_attacking:
            for input_key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_attack']:
                if keys[input_key]:
                    player_is_attacking = True
                    dtime_offset += self.level.player.attack()
                    break

        if not player_is_attacking:
            self.level.player.is_attacking = False

        if not player_is_moving:
            self.level.player.stop()

        if self.gamepad is not None:
            stick = self.gamepad.get_axis(Controller.GAMEPAD_LAYOUTS[self.active_gamepad_layout]['axis_block'])
            if stick is not None and stick > Controller.JOYSTICK_TOLERANCE:
                self.level.player.block()
        for input_key in Controller.KEYBOARD_LAYOUTS[self.active_keyboard_layout]['keys_block']:
            if keys[input_key]:
                self.level.player.block()
                break

        return dtime_offset
