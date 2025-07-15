import math
import random
import time
import pygame
import sys
import pickle
import traceback
from os.path import join, isfile
from Actor import Actor
from Block import BreakableBlock
from Controls import Controller
from Helpers import load_json_dict, load_levels, load_audios, display_text, glitch, DifficultyScale, handle_exception, load_text_from_file
from Level import Level
from HUD import HUD

pygame.init()

WIDTH, HEIGHT = 1920, 1080
FPS_TARGET = 60

icon = join("Assets", "Icons", "icon.png")
if isfile(icon):
    pygame.display.set_icon(pygame.image.load(icon))
else:
    handle_exception(FileNotFoundError(icon))

WINDOW = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.SCALED)
pygame.display.set_caption("AGENT GLITCH")


def get_offset(level, offset_x, offset_y, width, height):
    scroll_area_width = width * 0.375
    scroll_area_height = height * 0.25

    if level.get_player().rect.right - scroll_area_width < offset_x:
        offset_x = level.get_player().rect.right - scroll_area_width
    elif level.get_player().rect.left + scroll_area_width > offset_x + width:
        offset_x = level.get_player().rect.left - (width - scroll_area_width)
    if offset_x < level.level_bounds[0][0]:
        offset_x = level.level_bounds[0][0]
    elif offset_x > level.level_bounds[1][0] - width:
        offset_x = level.level_bounds[1][0] - width

    if level.get_player().rect.bottom - (2 * scroll_area_height) < offset_y:
        offset_y = level.get_player().rect.bottom - (2 * scroll_area_height)
    elif level.get_player().rect.top - (height - scroll_area_height) > offset_y:
        offset_y = level.get_player().rect.top - (height - scroll_area_height)
    if offset_y < level.level_bounds[0][1]:
        offset_y = level.level_bounds[0][1]
    elif offset_y > level.level_bounds[1][1] - height:
        offset_y = level.level_bounds[1][1] - height
    return offset_x, offset_y

def get_background(level):
    file = join("Assets", "Background", level.background)
    if not isfile(file):
        file = join("Assets", "Background", "Blue.png")
    image = pygame.image.load(file).convert_alpha()
    if level.grayscale:
        image = pygame.transform.grayscale(image)
    _, _, width, height = image.get_rect()

    tiles = []
    for i in range(max((level.level_bounds[1][0] // width), 1)):
        for j in range(max((level.level_bounds[1][1] // height), 1)):
            tiles.append((i * width, j * height))

    return tiles, image


def get_foreground(level):
    if level.foreground is None:
        return None
    else:
        file = join("Assets", "Foreground", level.foreground)
        if isfile(file):
            image = pygame.image.load(file).convert_alpha()
            if level.grayscale:
                image = pygame.transform.grayscale(image)
            return image
        else:
            return None


def play_slide(slide, controller, text=None, should_glitch=False, win=WINDOW):
    ffwd = False
    if text is not None:
        for i in range(len(text)):
            text_line = pygame.font.SysFont("courier", 32).render(text[i], True, (0, 0, 0))
            slide.blit(text_line, (slide.get_width() // 5, (slide.get_height() // 5) + (i * text_line.get_height())))

    black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
    black.fill((0, 0, 0))
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


def fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, direction="in", win=WINDOW):
    black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
    black.fill((0, 0, 0))
    for i in range(64):
        draw(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller.master_volume, 1, win=win)
        if direction == "in":
            black.set_alpha(255 - (4 * i))
            volume = (i + 1) / 64
        elif direction == "out":
            black.set_alpha(4 * i)
            volume = 1 - ((i + 1) / 64)
        else:
            volume = 1
        win.blit(black, (0, 0))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                controller.save_player_profile(controller)
                pygame.quit()
                sys.exit()
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume((controller.master_volume["background"]) * volume)
        time.sleep(0.01)


def fade_in(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win=WINDOW):
    fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, direction="in", win=win)


def fade_out(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, win=WINDOW):
    fade(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller, direction="out", win=win)


def draw(background, bg_image, fg_image, level, hud, offset_x, offset_y, master_volume, fps, glitches=None, win=WINDOW):
    screen = pygame.Rect(offset_x, offset_y, win.get_width(), win.get_height())

    if len(background) == 1:
        win.blit(bg_image.subsurface(screen), (0, 0))
    else:
        for tile in background:
            win.blit(bg_image, (tile[0] - offset_x, tile[1] - offset_y))

    level.output(win, offset_x, offset_y, master_volume, fps)

    if fg_image is not None:
        win.blit(fg_image.subsurface(screen), (0, 0))

    hud.output()

    if glitches is not None:
        for spot in glitches:
            win.blit(spot[0], spot[1])


def save_player_profile(controller, level=None):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
    else:
        data = None

    if level is None:
        if data is not None and data.get("level") is not None:
            cur_level = data["level"]
        else:
            cur_level = "__START__"
    else:
        cur_level = level.name

    data = {"level": cur_level, "master volume": controller.master_volume, "keyboard layout": controller.active_keyboard_layout, "gamepad layout": controller.active_gamepad_layout, "is fullscreen": pygame.display.is_fullscreen(), "difficulty": controller.difficulty, "selected sprite": controller.player_sprite_selected, "player abilities": controller.player_abilities}
    pickle.dump(data, open("GameData/profile.p", "wb"))


def load_player_profile(controller):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
        controller.master_volume = data["master volume"]
        controller.set_keyboard_layout(data["keyboard layout"])
        controller.difficulty = data["difficulty"]
        controller.player_sprite_selected = data["selected sprite"]
        controller.player_abilities = data["player abilities"]
        if not data["is fullscreen"]:
            pygame.display.toggle_fullscreen()
        return data["level"]
    else:
        return []


def save(level, hud):
    if hud is not None:
        hud.save_icon_timer = 1.0

    data = {"level": level.name}
    for obj in [level.get_player()] + level.get_objects():
        obj_data = obj.save()
        if obj_data is not None:
            data.update(obj_data)
    pickle.dump(data, open("GameData/save.p", "wb"))


def load_part1():
    if not isfile("GameData/save.p"):
        return None
    else:
        data = pickle.load(open("GameData/save.p", "rb"))
        if data is None:
            return None
        else:
            return data


def load_part2(data, level):
    if data is None or level is None:
        return False
    else:
        for obj in [level.get_player()] + level.get_objects():
            obj_data = data.get(obj.name)
            if obj_data is not None:
                if hasattr(obj, "has_fired") and obj.has_fired:
                    level.queue_purge(obj)
                else:
                    obj.load(obj_data)
            elif isinstance(obj, Actor) or isinstance(obj, BreakableBlock):
                level.queue_purge(obj)
        level.purge()
        return True


def main(win):
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    levels = load_levels("Levels")
    objects_dict = load_json_dict("ReferenceDicts", "objects_dict.txt")
    meta_dict = load_json_dict("ReferenceDicts", "meta_dict.txt")
    sprite_master = {}
    image_master = {}

    controller = Controller(None, win, save, save_player_profile, main_menu_music=(None if meta_dict.get("MAIN_MENU") is None or meta_dict["MAIN_MENU"].get("music") is None else list(meta_dict["MAIN_MENU"]["music"].split(' '))))
    controller.get_gamepad(notify=False)

    while True:
        if len(load_player_profile(controller)) == 0:
            pygame.display.toggle_fullscreen()
        if not controller.goto_main:
            if isfile(join("Assets", "Screens", "credit1.png")):
                play_slide(pygame.image.load(join("Assets", "Screens", "credit1.png")), controller, should_glitch=True)
            if isfile(join("Assets", "Screens", "credit2.png")):
                play_slide(pygame.image.load(join("Assets", "Screens", "credit2.png")), controller, should_glitch=True)
        pygame.mixer.music.set_volume(controller.master_volume["background"])
        new_game = False
        if isfile(join("Assets", "Screens", "title.png")):
            slide = pygame.image.load(join("Assets", "Screens", "title.png"))
            overlay = pygame.image.load(join("Assets", "Screens", "title_overlay.png"))
            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill((0, 0, 0))
            if not controller.goto_main:
                for i in range(64):
                    win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                    win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                    black.set_alpha(255 - (4 * i))
                    win.blit(black, (0, 0))
                    pygame.display.update()
                    time.sleep(0.01)
            if isfile("GameData/save.p"):
                controller.main_menu.buttons[1][1].set_alpha(255)
                controller.main_menu.buttons[1][2].set_alpha(255)
            else:
                controller.main_menu.buttons[1][1].set_alpha(128)
                controller.main_menu.buttons[1][2].set_alpha(128)
            new_game = controller.main()
            for i in range(64):
                win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                pygame.display.update()
                time.sleep(0.01)
        else:
            handle_exception(FileNotFoundError(join("Assets", "Screens", "title.png")))
        controller.goto_main = False
        load_data = None
        cur_level = None
        while True:
            should_load = False
            if new_game:
                cur_level = "__START__"
                save_player_profile(controller)
                new_game = False
            elif controller.goto_load:
                load_data = load_part1()
                cur_level = load_player_profile(controller)
                if cur_level == load_data["level"]:
                    should_load = True
            elif controller.goto_restart:
                controller.goto_restart = False
            elif controller.level_selected is not None:
                cur_level = controller.level_selected
                controller.level_selected = None
            controller.goto_load = False

            player_audio = enemy_audio = load_audios("Actors")
            block_audio = load_audios("Blocks")
            level = controller.level = Level(cur_level, levels, meta_dict, objects_dict, sprite_master, image_master, player_audio, enemy_audio, block_audio, win, controller)

            if level.music is not None:
                controller.queue_track_list()
                pygame.mixer.music.set_volume(controller.master_volume["background"])
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                pygame.mixer.music.play(fade_ms=2000)
                controller.cycle_music()

            if level.start_screen is not None:
                if isfile(join("Assets", "Screens", str(level.start_screen))):
                    play_slide(pygame.image.load(join("Assets", "Screens", str(level.start_screen))), controller)
                elif isinstance(level.start_screen, list):
                    for item in level.start_screen:
                        if isfile(join("Assets", "Screens", item)):
                            play_slide(pygame.image.load(join("Assets", "Screens", item)), controller)
                else:
                    print("Starting level " + level.name)

            if controller.player_abilities is not None:
                for key in controller.player_abilities:
                    setattr(level.get_player(), key, controller.player_abilities[key])
            else:
                controller.player_abilities = {"can_wall_jump": level.get_player().can_wall_jump, "can_teleport": level.get_player().can_teleport, "can_bullet_time": level.get_player().can_bullet_time, "can_resize": level.get_player().can_resize, "can_heal": level.get_player().can_heal, "max_jumps": level.get_player().max_jumps}

            hud = HUD(level.get_player(), win, grayscale=level.grayscale)
            controller.hud = hud

            if should_load:
                load_part2(load_data, controller.level)

            save(controller.level, None)

            controller.get_gamepad()

            background, bg_image = get_background(level)
            fg_image = get_foreground(level)

            offset_x = offset_y = 0
            offset_x, offset_y = get_offset(level, offset_x, offset_y, win.get_width(), win.get_height())

            fade_in(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller)
            if level.start_message is not None:
                display_text(load_text_from_file(level.start_message), win, controller)
    
            dtime_offset = 0
            level.time = 0
            glitch_timer = 0
            glitches = None
            next_level = None
            clock.tick(FPS_TARGET)
            while True:
                dtime = clock.tick(FPS_TARGET) - dtime_offset
                level.time += dtime
                if hud.save_icon_timer > 0:
                    hud.save_icon_timer -= dtime / 250
                if glitch_timer > 0:
                    glitch_timer -= dtime / 250
                    if glitch_timer <= 0:
                        glitch_timer = 0
                        glitches = None
                dtime_offset = 0

                dtime_offset += controller.get_gamepad()
    
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        save_player_profile(controller, level)
                        if controller.level is not None:
                            controller.save(controller.level, controller.hud)
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        dtime_offset += controller.handle_single_input(event.key, win)
                    elif event.type == pygame.KEYUP:
                        # DEV ONLY if event.key == pygame.K_F2:
                        # DEV ONLY    level.gen_background()
                        level.get_player().stop()
                    elif event.type == pygame.JOYBUTTONDOWN:
                        dtime_offset += controller.handle_single_input(event.button, win)
                    elif event.type == pygame.JOYBUTTONUP:
                        level.get_player().stop()
                    elif event.type == pygame.USEREVENT:
                        pygame.mixer.music.play()
                        if "LOOP" not in controller.music[controller.music_index].upper():
                            controller.cycle_music()
                controller.handle_continuous_input()
                if (controller.goto_load and isfile("GameData/save.p")) or controller.goto_main or controller.goto_restart:
                    break

                result = level.get_player().loop(FPS_TARGET, dtime)
                if result[1] is not None:
                    next_level = result[1]
                    break
                dtime_offset += result[0]
                if level.get_player().hp <= 0:
                    if controller.difficulty >= DifficultyScale.HARDEST:
                        controller.goto_restart = True
                        break
                    else:
                        level.get_player().revert()
    
                for obj in level.get_objects():
                    if (not isinstance(obj, Actor) and type(obj).__name__.upper() != "BLOCK") or (isinstance(obj, Actor) and math.dist(obj.rect.topleft, level.get_player().rect.topleft) < win.get_width() * 1.5):
                        if hasattr(obj, "patrol") and callable(obj.patrol):
                            obj.patrol(dtime)
                        obj.loop(FPS_TARGET, dtime)

                level.purge()

                if level.weather is not None:
                    level.weather.move(dtime)

                if level.can_glitch and glitch_timer <= 0 and random.randint(0, 100) / 100 > level.get_player().hp / level.get_player().max_hp:
                    glitches = glitch((1 - max(level.get_player().hp / level.get_player().max_hp, 0)) / 2, win)
                    glitch_timer = 0.5
                draw(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller.master_volume, FPS_TARGET, glitches=glitches)
                pygame.display.update()

                offset_x, offset_y = get_offset(level, offset_x, offset_y, win.get_width(), win.get_height())

            if controller.music is not None:
                pygame.mixer.music.fadeout(1000)
                pygame.mixer.music.unload()

            if controller.goto_main:
                break
            elif next_level is not None:
                if level.end_message is not None:
                    display_text(load_text_from_file(level.end_message), win, controller)
                save_player_profile(controller, level)
                fade_out(background, bg_image, fg_image, level, hud, offset_x, offset_y, controller)
                if level.end_screen is not None:
                    if isfile(join("Assets", "Screens", str(level.end_screen))):
                        play_slide(pygame.image.load(join("Assets", "Screens", str(level.end_screen))), controller)
                    elif isinstance(level.end_screen, list):
                        for item in level.end_screen:
                            if isfile(join("Assets", "Screens", item)):
                                play_slide(pygame.image.load(join("Assets", "Screens", item)), controller)
                    if isfile(join("Assets", "Screens", "recap.png")):
                        play_slide(pygame.image.load(join("Assets", "Screens", "recap.png")), controller, text=["Mission successful.", "Mission time: " + controller.get_formatted_level_time() + "."])
                if level.grayscale:
                    sprite_master.clear()
                    image_master.clear()
                cur_level = next_level

        if not controller.goto_main:
            if isfile(join("Assets", "Screens", "all_done.png")):
                play_slide(pygame.image.load(join("Assets", "Screens", "all_done.png")), controller)


if __name__ == "__main__":
    try:
        main(WINDOW)
    except Exception as e:
        print(traceback.print_exception(e))
