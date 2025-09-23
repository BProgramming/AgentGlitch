import random
import time
import pygame
import sys
from Menu import Menu, Selector, ButtonType
from Helpers import display_text, DifficultyScale, load_images, load_level_images, load_picker_sprites, make_image_from_text


class Controller:
    KEYBOARD_LAYOUTS = {"ARROW_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_LEFT], "keys_right": [pygame.K_RIGHT], "keys_crouch_uncrouch": [pygame.K_DOWN], "keys_jump": [pygame.K_UP], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS], "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_d], "keys_block": [pygame.K_a], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]},
                        "WASD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_a], "keys_right": [pygame.K_d], "keys_crouch_uncrouch": [pygame.K_s], "keys_jump": [pygame.K_w], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS], "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_LEFT, pygame.K_KP4], "keys_block": [pygame.K_RIGHT, pygame.K_KP6], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_UP, pygame.K_KP8], "keys_shrink": [pygame.K_DOWN, pygame.K_KP5]},
                        "NUMPAD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_KP4], "keys_right": [pygame.K_KP6], "keys_crouch_uncrouch": [pygame.K_KP5], "keys_jump": [pygame.K_KP8], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS],  "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_d], "keys_block": [pygame.K_a], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]},
                        "ALT_NUMPAD_MOVE": {"keys_quicksave": [pygame.K_F5], "keys_cycle_layout": [pygame.K_F9], "keys_fullscreen_toggle": [pygame.K_F11], "keys_left": [pygame.K_KP4], "keys_right": [pygame.K_KP6], "keys_crouch_uncrouch": [pygame.K_KP5], "keys_jump": [pygame.K_KP8], "keys_teleport_dash": [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_KP_PLUS],  "keys_pause_unpause": [pygame.K_ESCAPE], "keys_attack": [pygame.K_a], "keys_block": [pygame.K_d], "keys_bullet_time": [pygame.K_SPACE, pygame.K_KP0], "keys_grow": [pygame.K_w], "keys_shrink": [pygame.K_s]}}
    GAMEPAD_LAYOUTS = {"SWITCH PRO": {"button_menu_up": 11, "button_menu_down": 12, "button_quicksave": 15, "button_left": 13, "button_right": 14, "axis_horiz": 0, "hat_horiz": None, "button_crouch_uncrouch": 0, "button_jump": 1, "button_teleport_dash": 3, "button_pause_unpause": 5, "axis_attack": 5, "axis_block": 4, "button_bullet_time": 2, "button_grow": 10, "button_shrink": 9},
                        "XBOX": {"button_menu_up": None, "button_menu_down": None, "button_quicksave": 6, "button_left": None, "button_right": None, "axis_horiz": 0, "hat_horiz": 0, "button_crouch_uncrouch": 1, "button_jump": 0, "button_teleport_dash": 2, "button_pause_unpause": 7, "axis_attack": 5, "axis_block": 4, "button_bullet_time": 3, "button_grow": 5, "button_shrink": 4},
                        "PS4": {"button_menu_up": 11, "button_menu_down": 12, "button_quicksave": 4, "button_left": 13, "button_right": 14, "axis_horiz": 0, "hat_horiz": None, "button_crouch_uncrouch": 1, "button_jump": 0, "button_teleport_dash": 2, "button_pause_unpause": 6, "axis_attack": 5, "axis_block": 4, "button_bullet_time": 3, "button_grow": 10, "button_shrink": 9},
                        "PS5": {"button_menu_up": None, "button_menu_down": None, "button_quicksave": 8, "button_left": None, "button_right": None, "axis_horiz": 0, "hat_horiz": 0, "button_crouch_uncrouch": 1, "button_jump": 0, "button_teleport_dash": 2, "button_pause_unpause": 9, "axis_attack": 5, "axis_block": 2, "button_bullet_time": 3, "button_grow": 5, "button_shrink": 4},
                        "NONE": {"button_menu_up": None, "button_menu_down": None, "button_quicksave": None, "button_left": None, "button_right": None, "axis_horiz": None, "hat_horiz": None, "button_crouch_uncrouch": None, "button_jump": None, "button_teleport_dash": None, "button_pause_unpause": None, "axis_attack": None, "axis_block": None, "button_bullet_time": None, "button_grow": None, "button_shrink": None}}
    JOYSTICK_TOLERANCE = 0.1

    def __init__(self, level, win, save, save_player_profile, layout=None, main_menu_music=None, steamworks=None):
        self.win = win
        self.save = save
        self.save_player_profile = save_player_profile
        self.steamworks = steamworks
        self.should_store_steam_stats = False
        self.player_sprite_selected = [None, None]
        self.player_abilities = None
        self.difficulty = DifficultyScale.MEDIUM
        self.hud = None
        self.goto_load = self.goto_main = self.goto_restart = False
        self.level = level
        self.master_volume = {"background": 1.0, "player": 1.0, "non-player": 1.0, "cinematics": 1.0}
        dif = {"label": "Difficulty", "type": ButtonType.BAR, "snap": True, "value": self.difficulty, "range": (float(DifficultyScale.EASIEST), float(DifficultyScale.EASY), float(DifficultyScale.MEDIUM), float(DifficultyScale.HARD), float(DifficultyScale.HARDEST))}
        vol_bg = {"label": "Music", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["background"], "range": (0, 100)}
        vol_pc = {"label": "Player", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["player"], "range": (0, 100)}
        vol_fx = {"label": "Effects", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["non-player"], "range": (0, 100)}
        vol_cn = {"label": "Cinematics", "type": ButtonType.BAR, "snap": False, "value": self.master_volume["cinematics"], "range": (0, 100)}
        self.main_menu = Menu(win, "MAIN MENU", [{"label": "New game", "type": ButtonType.CLICK}, {"label": "Continue", "type": ButtonType.CLICK}, {"label": "Select a level", "type": ButtonType.CLICK}, {"label": "Settings", "type": ButtonType.CLICK}, {"label": "Quit to desktop", "type": ButtonType.CLICK}], music=main_menu_music)
        self.pause_menu = Menu(win, "PAUSED", [{"label": "Resume", "type": ButtonType.CLICK}, {"label": "Load last save", "type": ButtonType.CLICK}, {"label": "Restart level", "type": ButtonType.CLICK}, {"label": "Settings", "type": ButtonType.CLICK}, {"label": "Quit to menu", "type": ButtonType.CLICK}, {"label": "Quit to desktop", "type": ButtonType.CLICK}])
        self.settings_menu = Menu(win, "SETTINGS", [dif, {"label": "Controls", "type": ButtonType.CLICK}, {"label": "Volume", "type": ButtonType.CLICK}, {"label": "Toggle fullscreen", "type": ButtonType.CLICK}, {"label": "Back", "type": ButtonType.CLICK}])
        self.volume_menu = Menu(win, "VOLUME", [vol_bg, vol_pc, vol_fx, vol_cn, {"label": "Back", "type": ButtonType.CLICK}])
        self.controls_menu = Menu(win, "CONTROLS", [{"label": "Keyboard", "type": ButtonType.CLICK}, {"label": "Controller", "type": ButtonType.CLICK}, {"label": "Back", "type": ButtonType.CLICK}])
        difficulty_images = [make_image_from_text(256, 128, "EASIEST", ["Agent is much stronger", "Enemies are much weaker", "Enemy sight ranges are visible"], border=5), make_image_from_text(256, 128, "EASY", ["Agent is stronger", "Enemies are weaker", "Enemy sight ranges are visible"], border=5), make_image_from_text(256, 128, "MEDIUM", ["Agent is normal strength", "Enemies are normal strength", "Enemy sight ranges are not visible"], border=5), make_image_from_text(256, 128, "HARD", ["Agent is weaker", "Enemies are stronger", "Enemy sight ranges are not visible"], border=5), make_image_from_text(256, 128, "HARDEST", ["Agent is much weaker", "Enemies are much stronger", "Enemy sight ranges are not visible"], border=5)]
        self.difficulty_picker = Selector(win, "CHOOSE DIFFICULTY", ["You can change this at any time."], difficulty_images, [DifficultyScale.EASIEST, DifficultyScale.EASY, DifficultyScale.MEDIUM, DifficultyScale.HARD, DifficultyScale.HARDEST], index=2)
        sprite_images, sprite_values = load_picker_sprites("Sprites")
        self.sprite_picker = Selector(win, "CHOOSE PLAYER", ["This is a visual choice only.", "Anyone can be an Agent."], sprite_images, sprite_values, index=2 * random.randrange(0, len(sprite_images) // 2))
        self.level_selected = None
        level_images, level_values = load_level_images("LevelImages")
        self.level_picker = Selector(win, "CHOOSE LEVEL", None, level_images, level_values)
        if layout is None:
            self.set_keyboard_layout("ARROW_MOVE")
        else:
            self.set_keyboard_layout(layout)
        self.gamepad = None
        self.active_gamepad_layout = None
        self.keyboard_layout_picker = Selector(win, "KEYBOARD LAYOUT", ["This can be cycled with the F9 key."], load_images("Menu", "Keyboards").values(), list(self.KEYBOARD_LAYOUTS.keys()))
        self.gamepad_layout_picker = Selector(win, "CONTROLLER LAYOUT", ["This is detected when you connect a controller."], load_images("Menu", "Controllers").values(), list(self.GAMEPAD_LAYOUTS.keys()), accept_only=True)
        self.music = None
        self.music_index = 0
        self.should_hot_swap_level = False
        self.should_scroll_to_point = None

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
            for ent in [self.level.get_player()] + self.level.get_entities():
                ent.set_difficulty(self.difficulty)

    def get_gamepad(self, notify=True) -> int:
        start = time.perf_counter_ns()
        if pygame.joystick.get_count() > 0:
            gamepad = pygame.joystick.Joystick(0)
        else:
            gamepad = None

        if gamepad != self.gamepad:
            self.gamepad = gamepad

            if self.gamepad is None:
                self.set_gamepad_layout("NONE")
                msg = "Controller disconnected."
            else:
                name = self.gamepad.get_name()
                if name == "Nintendo Switch Pro Controller":
                    self.set_gamepad_layout("SWITCH PRO")
                    msg = "Nintendo Switch controller detected."
                elif name == "Controller (Xbox One For Windows)":
                    self.set_gamepad_layout("XBOX")
                    msg = "Xbox controller detected."
                elif name == "PS4 Controller":
                    self.set_gamepad_layout("PS4")
                    msg = "PS4 controller detected."
                elif name == "Sony Interactive Entertainment Wireless Controller":
                    self.set_gamepad_layout("PS5")
                    msg = "PS5 controller detected."
                elif name == "Wireless Gamepad":
                    self.set_gamepad_layout("NONE")
                    msg = ["Nintendo Switch Joy-Con detected.", "Individual Joy-Cons are not supported. Please connect the full controller."]
                else:
                    self.set_gamepad_layout("NONE")
                    msg = "Sorry, this controller type is not supported."

            if notify:
                display_text(msg, self)
        return (time.perf_counter_ns() - start) // 1000000

    def set_keyboard_layout(self, name) -> None:
        layout = Controller.KEYBOARD_LAYOUTS[name]
        self.keys_quicksave = layout["keys_quicksave"]
        self.keys_cycle_layout = layout["keys_cycle_layout"]
        self.keys_fullscreen_toggle = layout["keys_fullscreen_toggle"]
        self.keys_left = layout["keys_left"]
        self.keys_right = layout["keys_right"]
        self.keys_crouch_uncrouch = layout["keys_crouch_uncrouch"]
        self.keys_jump = layout["keys_jump"]
        self.keys_teleport_dash = layout["keys_teleport_dash"]
        self.keys_pause_unpause = layout["keys_pause_unpause"]
        self.keys_attack = layout["keys_attack"]
        self.keys_block = layout["keys_block"]
        self.keys_bullet_time = layout["keys_bullet_time"]
        self.keys_grow = layout["keys_grow"]
        self.keys_shrink = layout["keys_shrink"]
        self.active_keyboard_layout = name

    def set_gamepad_layout(self, name) -> None:
        layout = Controller.GAMEPAD_LAYOUTS[name]
        self.button_menu_up = layout["button_menu_up"]
        self.button_menu_down = layout["button_menu_down"]
        self.button_quicksave = layout["button_quicksave"]
        self.button_left = layout["button_left"]
        self.button_right = layout["button_right"]
        self.axis_horiz = layout["axis_horiz"]
        self.hat_horiz = layout["hat_horiz"]
        self.button_crouch_uncrouch = layout["button_crouch_uncrouch"]
        self.button_jump = layout["button_jump"]
        self.button_teleport_dash = layout["button_teleport_dash"]
        self.button_pause_unpause = layout["button_pause_unpause"]
        self.axis_attack = layout["axis_attack"]
        self.axis_block = layout["axis_block"]
        self.button_bullet_time = layout["button_bullet_time"]
        self.button_grow = layout["button_grow"]
        self.button_shrink = layout["button_shrink"]
        self.active_gamepad_layout = (None if name == "NONE" else name)

    def pick_from_selector(self, selector, clear=None) -> bool:
        pygame.mouse.set_visible(True)
        if self.active_gamepad_layout is not None:
            selector.set_mouse_pos(self.win)
        selector.fade_in(self.win)
        joystick_movement = 0
        selector.clear = clear
        while True:
            time.sleep(0.01)

            if len(selector.buttons) > 1:
                match selector.display(self.win):
                    case 0:
                        selector.cycle_images(-1)
                    case 1:
                        selector.cycle_images(1)
                    case 2:
                        selector.fade_out(self.win)
                        return False
                    case 3:
                        selector.fade_out(self.win)
                        return True
                    case _:
                        pass
            else:
                match selector.display(self.win):
                    case 0:
                        selector.fade_out(self.win)
                        return False
                    case _:
                        pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in self.keys_pause_unpause:
                    pygame.mouse.set_visible(False)
                    return False

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(0)) > Menu.JOYSTICK_TOLERANCE and len(selector.buttons) > 1:
                    selector.move_mouse_sideways(1 if self.gamepad.get_axis(0) >= 0 else -1)
                    should_process_event = False
                elif abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    selector.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

    def volume(self, clear=None) -> None:
        pygame.mouse.set_visible(True)
        self.volume_menu.notch_val[0] = self.master_volume["background"]
        self.volume_menu.notch_val[1] = self.master_volume["player"]
        self.volume_menu.notch_val[2] = self.master_volume["non-player"]
        self.volume_menu.notch_val[3] = self.master_volume["cinematics"]
        if self.active_gamepad_layout is not None:
            self.volume_menu.set_mouse_pos(self.win)
        self.volume_menu.fade_in(self.win)
        joystick_movement = 0
        self.volume_menu.clear = clear
        while True:
            time.sleep(0.01)

            match self.volume_menu.display(self.win):
                case 0:
                    pass  #set background music volume
                case 1:
                    pass  #set player volume
                case 2:
                    pass  #set effects volume
                case 3:
                    pass  #set cinematics volume
                case 4:
                    self.volume_menu.fade_out(self.win)
                    self.master_volume["background"] = self.volume_menu.notch_val[0]
                    pygame.mixer.music.set_volume(self.master_volume["background"])
                    self.master_volume["player"] = self.volume_menu.notch_val[1]
                    self.master_volume["non-player"] = self.volume_menu.notch_val[2]
                    self.master_volume["cinematics"] = self.volume_menu.notch_val[3]
                    return
                case _:
                    pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in self.keys_pause_unpause:
                    pygame.mouse.set_visible(False)
                    return

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    self.settings_menu.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

    def controls(self, clear=None) -> None:
        pygame.mouse.set_visible(True)
        if self.active_gamepad_layout is not None:
            self.controls_menu.set_mouse_pos(self.win)
            self.controls_menu.buttons[1][1].set_alpha(255)
            self.controls_menu.buttons[1][2].set_alpha(255)
        else:
            self.controls_menu.buttons[1][1].set_alpha(128)
            self.controls_menu.buttons[1][2].set_alpha(128)
        self.controls_menu.fade_in(self.win)
        joystick_movement = 0
        self.controls_menu.clear = clear
        while True:
            time.sleep(0.01)
            if self.active_gamepad_layout is not None:
                self.controls_menu.buttons[1][1].set_alpha(255)
                self.controls_menu.buttons[1][2].set_alpha(255)
            else:
                self.controls_menu.buttons[1][1].set_alpha(128)
                self.controls_menu.buttons[1][2].set_alpha(128)

            match self.controls_menu.display(self.win):
                case 0:
                    self.controls_menu.fade_out(self.win)
                    self.keyboard_layout_picker.set_index(self.keyboard_layout_picker.values.index(self.active_keyboard_layout))
                    if self.pick_from_selector(self.keyboard_layout_picker, clear=self.controls_menu.clear):
                        self.set_keyboard_layout(self.keyboard_layout_picker.values[self.keyboard_layout_picker.image_index])
                    self.controls_menu.fade_in(self.win)
                    if self.active_gamepad_layout is not None:
                        self.controls_menu.set_mouse_pos(self.win)
                case 1:
                    if self.active_gamepad_layout is not None:
                        self.controls_menu.fade_out(self.win)
                        self.gamepad_layout_picker.set_index(self.gamepad_layout_picker.values.index(self.active_gamepad_layout))
                        self.pick_from_selector(self.gamepad_layout_picker, clear=self.controls_menu.clear)
                        self.controls_menu.fade_in(self.win)
                        if self.active_gamepad_layout is not None:
                            self.controls_menu.set_mouse_pos(self.win)
                    else:
                        display_text("No controller connected.", self)
                case 2:
                    self.controls_menu.fade_out(self.win)
                    return
                case _:
                    pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in self.keys_pause_unpause:
                    pygame.mouse.set_visible(False)
                    return

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    self.controls_menu.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

    def settings(self, clear=None) -> None:
        pygame.mouse.set_visible(True)
        self.settings_menu.notch_val[0] = (self.difficulty - DifficultyScale.EASIEST) / (DifficultyScale.HARDEST - DifficultyScale.EASIEST)
        if self.active_gamepad_layout is not None:
            self.settings_menu.set_mouse_pos(self.win)
        self.settings_menu.fade_in(self.win)
        joystick_movement = 0
        self.settings_menu.clear = clear
        while True:
            time.sleep(0.01)

            match self.settings_menu.display(self.win):
                case 0:
                    pass #set difficulty
                case 1:
                    self.controls(self.settings_menu.clear)
                case 2:
                    time.sleep(0.01)
                    self.volume(self.settings_menu.clear)
                case 3:
                    pygame.display.toggle_fullscreen()
                case 4:
                    self.settings_menu.fade_out(self.win)
                    self.difficulty = DifficultyScale((self.settings_menu.notch_val[0] * (self.settings_menu.buttons[0][4][-1] - self.settings_menu.buttons[0][4][0])) + self.settings_menu.buttons[0][4][0])
                    self.set_difficulty()
                    return
                case _:
                    pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in self.keys_pause_unpause:
                    pygame.mouse.set_visible(False)
                    return

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    self.settings_menu.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

    def pause(self) -> int:
        pygame.mouse.set_visible(True)
        start = time.perf_counter_ns()
        pygame.mixer.pause()
        if self.active_gamepad_layout is not None:
            self.pause_menu.set_mouse_pos(self.win)
        self.pause_menu.fade_in(self.win)
        joystick_movement = 0
        paused = True
        while paused:
            time.sleep(0.01)

            match self.pause_menu.display(self.win):
                case 0:
                    paused = False
                case 1:
                    self.goto_load = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    self.pause_menu.clear = None
                    return 0
                case 2:
                    self.goto_restart = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    self.pause_menu.clear = None
                    return 0
                case 3:
                    time.sleep(0.01)
                    self.settings(self.pause_menu.clear)
                case 4:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    self.goto_main = True
                    pygame.mixer.unpause()
                    pygame.mouse.set_visible(False)
                    self.pause_menu.clear = None
                    return 0
                case 5:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    self.pause_menu.clear = None
                    pygame.quit()
                    sys.exit()
                case _:
                    pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.level is not None:
                        self.save(self.level, self.hud)
                        self.save_player_profile(self, self.level)
                    else:
                        self.save_player_profile(self)
                    self.pause_menu.clear = None
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN and event.key in self.keys_pause_unpause:
                    paused = False
                    pygame.mouse.set_visible(False)
                    break

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    self.pause_menu.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

        self.pause_menu.fade_out(self.win)
        self.pause_menu.clear = None
        pygame.mixer.unpause()
        pygame.mouse.set_visible(False)
        return (time.perf_counter_ns() - start) // 1000000

    def main(self) -> bool:
        self.main_menu.fade_music()
        pygame.mouse.set_visible(True)
        if self.active_gamepad_layout is not None:
            self.main_menu.set_mouse_pos(self.win)
        self.main_menu.fade_in(self.win)
        joystick_movement = 0
        self.level_selected = None
        while True:
            time.sleep(0.01)

            match self.main_menu.display(self.win):
                case 0:
                    self.main_menu.fade_out(self.win)
                    while True:
                        if self.pick_from_selector(self.sprite_picker, clear=self.main_menu.clear):
                            self.player_sprite_selected = [self.sprite_picker.values[self.sprite_picker.image_index][0], self.sprite_picker.values[self.sprite_picker.image_index][1]]
                            if self.pick_from_selector(self.difficulty_picker, clear=self.main_menu.clear):
                                self.difficulty = self.difficulty_picker.values[self.difficulty_picker.image_index]
                                pygame.mouse.set_visible(False)
                                self.main_menu.fade_music()
                                return True
                            if self.active_gamepad_layout is not None:
                                self.main_menu.set_mouse_pos(self.win)
                        else:
                            if self.active_gamepad_layout is not None:
                                self.main_menu.set_mouse_pos(self.win)
                            break
                    self.main_menu.fade_in(self.win)
                case 1:
                    self.main_menu.fade_out(self.win)
                    self.goto_load = True
                    pygame.mouse.set_visible(False)
                    self.main_menu.fade_music()
                    return False
                case 2:
                    self.main_menu.fade_out(self.win)
                    if self.pick_from_selector(self.level_picker, clear=self.main_menu.clear):
                        self.level_selected = self.level_picker.values[self.level_picker.image_index]
                        pygame.mouse.set_visible(False)
                        self.main_menu.fade_music()
                        return bool(self.level_picker.image_index == 0)
                    else:
                        if self.active_gamepad_layout is not None:
                            self.main_menu.set_mouse_pos(self.win)
                        self.main_menu.fade_in(self.win)
                case 3:
                    time.sleep(0.01)
                    self.settings(self.main_menu.clear)
                case 4:
                    self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                case _:
                    pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_player_profile(self)
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.USEREVENT:
                    if "LOOP" in self.main_menu.music[self.main_menu.music_index].upper():
                        pygame.mixer.music.play(-1)
                        pygame.mixer.music.set_endevent()
                    else:
                        pygame.mixer.music.play()
                        self.main_menu.cycle_music()
                        pygame.mixer.music.queue(self.main_menu.music[self.main_menu.music_index])

            self.get_gamepad()
            if self.active_gamepad_layout is not None:
                should_process_event = True
                if abs(self.gamepad.get_axis(1)) > Menu.JOYSTICK_TOLERANCE:
                    joystick_movement = self.gamepad.get_axis(1)
                    should_process_event = False
                elif self.gamepad.get_numhats() > 0 and abs(self.gamepad.get_hat(0)[1]) == 1:
                    joystick_movement = -self.gamepad.get_hat(0)[1]
                    should_process_event = False
                elif self.button_menu_up is not None and self.gamepad.get_button(self.button_menu_up):
                    joystick_movement = -1
                    should_process_event = False
                elif self.button_menu_down is not None and self.gamepad.get_button(self.button_menu_down):
                    joystick_movement = 1
                    should_process_event = False

                if should_process_event and abs(joystick_movement) > Menu.JOYSTICK_TOLERANCE:
                    self.main_menu.move_mouse_pos(self.win, 1 if joystick_movement >= 0 else -1)
                    joystick_movement = 0

    def cycle_keyboard_layout(self, win) -> int:
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
            text = ""

        text_output = pygame.font.SysFont("courier", 18).render(text, True, (0, 0, 0))
        text_box = pygame.Surface((text_output.get_width() + 10, text_output.get_height() + 10), pygame.SRCALPHA)
        text_box.fill((255, 255, 255, 128))
        win.blit(text_box, ((win.get_width() - text_box.get_width()) // 2, 3 * (win.get_height() - text_box.get_height()) // 4))
        win.blit(text_output, (((win.get_width() - text_box.get_width()) // 2) + 5, (3 * (win.get_height() - text_box.get_height()) // 4) + 5))
        pygame.display.update()
        time.sleep(1)

        return 1000

    def handle_pause_unpause(self, key) -> int:
        if key in self.keys_pause_unpause or (self.active_gamepad_layout is not None and self.button_pause_unpause is not None and key == self.button_pause_unpause):
            return self.pause()
        else:
            return 0

    def handle_any_key(self) -> bool:
        if any(pygame.key.get_pressed()):
            return True
        elif self.active_gamepad_layout is not None:
            for i in range(self.gamepad.get_numbuttons()):
                if self.gamepad.get_button(i):
                    return True
        return False

    def handle_single_input(self, key, win) -> int:
        if key in self.keys_pause_unpause or (self.active_gamepad_layout is not None and self.button_pause_unpause is not None and key == self.button_pause_unpause):
            return self.pause()
        elif key in self.keys_quicksave or (self.active_gamepad_layout is not None and self.button_quicksave is not None and key == self.button_quicksave):
            self.save(self.level, self.hud)
        elif key in self.keys_cycle_layout:
            return self.cycle_keyboard_layout(win)
        elif key in self.keys_fullscreen_toggle:
            pygame.display.toggle_fullscreen()
        elif (key in self.keys_crouch_uncrouch or (self.active_gamepad_layout is not None and self.button_crouch_uncrouch is not None and key == self.button_crouch_uncrouch)) and self.should_scroll_to_point is None:
            self.level.get_player().toggle_crouch()
        elif (key in self.keys_jump or (self.active_gamepad_layout is not None and self.button_jump is not None and key == self.button_jump)) and self.should_scroll_to_point is None:
            self.level.get_player().jump()
        elif (key in self.keys_teleport_dash or (self.active_gamepad_layout is not None and self.button_teleport_dash is not None and key == self.button_teleport_dash)) and self.should_scroll_to_point is None:
            self.level.get_player().teleport()
        elif (key in self.keys_bullet_time or (self.active_gamepad_layout is not None and self.button_bullet_time is not None and key == self.button_bullet_time)) and self.should_scroll_to_point is None:
            self.level.get_player().bullet_time()
        elif (key in self.keys_grow or (self.active_gamepad_layout is not None and self.button_grow is not None and key == self.button_grow)) and self.should_scroll_to_point is None:
            self.level.get_player().grow()
        elif (key in self.keys_shrink or (self.active_gamepad_layout is not None and self.button_shrink is not None and key == self.button_shrink)) and self.should_scroll_to_point is None:
            self.level.get_player().shrink()
        return 0

    def handle_continuous_input(self) -> None:
        if self.should_scroll_to_point is not None:
            return

        player_is_moving = False
        player_is_attacking = False

        if self.active_gamepad_layout is not None:
            stick = self.gamepad.get_axis(self.axis_horiz)
            hat = (None if self.hat_horiz is None else self.gamepad.get_hat(self.hat_horiz))
            if not player_is_moving and stick is not None:
                if stick > Controller.JOYSTICK_TOLERANCE:
                    player_is_moving = True
                    self.level.get_player().move_right()
                elif stick < -Controller.JOYSTICK_TOLERANCE:
                    player_is_moving = True
                    self.level.get_player().move_left()

            if not player_is_moving and hat is not None:
                if hat[0] > 0:
                    player_is_moving = True
                    self.level.get_player().move_right()
                elif hat[0] < 0:
                    player_is_moving = True
                    self.level.get_player().move_left()

            if not player_is_moving and self.button_right is not None and self.button_left is not None:
                if self.gamepad.get_button(self.button_right) > 0:
                    player_is_moving = True
                    self.level.get_player().move_right()
                elif self.gamepad.get_button(self.button_left) > 0:
                    player_is_moving = True
                    self.level.get_player().move_left()

            stick = self.gamepad.get_axis(self.axis_attack)
            if not player_is_attacking and stick is not None and stick > Controller.JOYSTICK_TOLERANCE:
                player_is_attacking = True
                self.level.get_player().attack()

        keys = pygame.key.get_pressed()
        if not player_is_moving:
            for input_key in self.keys_right:
                if keys[input_key]:
                    player_is_moving = True
                    self.level.get_player().move_right()
                    break
        if not player_is_moving:
            for input_key in self.keys_left:
                if keys[input_key]:
                    player_is_moving = True
                    self.level.get_player().move_left()
                    break

        if not player_is_attacking:
            for input_key in self.keys_attack:
                if keys[input_key]:
                    player_is_attacking = True
                    self.level.get_player().attack()
                    break

        if not player_is_attacking:
            self.level.get_player().is_attacking = False

        if not player_is_moving:
            self.level.get_player().stop()

        if self.active_gamepad_layout is not None:
            stick = self.gamepad.get_axis(self.axis_block)
            if stick is not None and stick > Controller.JOYSTICK_TOLERANCE:
                self.level.get_player().block()
        for input_key in self.keys_block:
            if keys[input_key]:
                self.level.get_player().block()
                break
