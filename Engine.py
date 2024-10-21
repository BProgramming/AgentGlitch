import random
import time
import pygame
import sys
import pickle
from os.path import join, isfile
from Controls import Controller
from Helpers import load_json_dict, load_levels, load_audios, display_text, glitch, DifficultyScale, handle_exception
from LevelBuilder import build_level
from HUD import HUD
from Block import MovableBlock, MovingBlock

pygame.init()

WIDTH, HEIGHT = 1280, 960
FPS_TARGET = 60

icon = join("Assets", "Icons", "icon.png")
if isfile(icon):
    pygame.display.set_icon(pygame.image.load(icon))
else:
    handle_exception(FileNotFoundError(icon))

WINDOW = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.SCALED)
pygame.display.set_caption("AGENT GLITCH")


def get_background(name, level_bounds):
    file = join("Assets", "Background", name)
    if isfile(file):
        image = pygame.image.load(file).convert_alpha()
        _, _, width, height = image.get_rect()

        tiles = []
        for i in range((level_bounds[1][0] // width) + 1):
            for j in range((level_bounds[1][1] // height) + 1):
                tiles.append((i * width, j * height))

        return tiles, image
    else:
        handle_exception(FileNotFoundError(file))


def play_slide(slide, controller, text=None, should_glitch=False, win=WINDOW):
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
                controller.save_profile(controller)
                pygame.quit()
                sys.exit()
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
                controller.save_profile(controller)
                pygame.quit()
                sys.exit()
        if controller.handle_anykey():
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
                controller.save_profile(controller)
                pygame.quit()
                sys.exit()
        time.sleep(0.01)


def fade(background, bg_image, player, objects, hud, offset_x, offset_y, controller, direction="in", win=WINDOW):
    black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
    black.fill((0, 0, 0))
    for i in range(64):
        draw(background, bg_image, player, objects, hud, offset_x, offset_y, controller.master_volume, win=win)
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
                controller.save_profile(controller)
                pygame.quit()
                sys.exit()
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume((controller.master_volume["background"] / 100) * volume)
        time.sleep(0.01)


def fade_in(background, bg_image, player, objects, hud, offset_x, offset_y, controller, win=WINDOW):
    fade(background, bg_image, player, objects, hud, offset_x, offset_y, controller, direction="in", win=win)


def fade_out(background, bg_image, player, objects, hud, offset_x, offset_y, controller, win=WINDOW):
    fade(background, bg_image, player, objects, hud, offset_x, offset_y, controller, direction="out", win=win)


def draw(background, bg_image, player, objects, hud, offset_x, offset_y, master_volume, glitches=None, win=WINDOW):
    for tile in background:
        win.blit(bg_image, (tile[0] - offset_x, tile[1] - offset_y))

    for obj in objects:
        obj.output(win, offset_x, offset_y, player, master_volume)

    player.output(win, offset_x, offset_y, player, master_volume)
    hud.output()

    if glitches is not None:
        for spot in glitches:
            win.blit(spot[0], spot[1])


def save_player_profile(controller, level=None):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
    else:
        data = None

    if data is None:
        levels = []
    else:
        levels = data.get("levels completed")
        if level is None:
            pass
        elif level not in levels:
            levels.append(level)
        else:
            for i in range(len(levels)):
                if levels[i] == level:
                    levels = levels[:i]
                    break

    data = {"levels completed": levels, "master volume": controller.master_volume, "keyboard layout": controller.active_keyboard_layout, "gamepad layout": controller.active_gamepad_layout, "is fullscreen": pygame.display.is_fullscreen(), "difficulty": controller.difficulty, "selected sprite": controller.player_sprite_selected}
    pickle.dump(data, open("GameData/profile.p", "wb"))


def load_player_profile(controller):
    if isfile("GameData/profile.p"):
        data = pickle.load(open("GameData/profile.p", "rb"))
        controller.master_volume = data["master volume"]
        controller.set_keyboard_layout(data["keyboard layout"])
        controller.difficulty = data["difficulty"]
        controller.player_sprite_selected = data["selected sprite"]
        if data["is fullscreen"]:
            pygame.display.toggle_fullscreen()
        return data["levels completed"]
    else:
        return []


def save(objects, hud):
    if hud is not None:
        hud.save_icon_timer = 1.0

    data = {"level": objects[0]}
    for obj in objects[1]:
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


def load_part2(data, objects):
    if data is None or len(objects) < 2:
        return False
    else:
        for obj in objects[1]:
            obj_data = data.get(obj.name)
            if obj_data is not None:
                obj.load(obj_data)
        return True


def main(win):
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    levels = load_levels("Levels")
    objects_dict = load_json_dict("ReferenceDicts", "objects_dict.txt")
    meta_dict = load_json_dict("ReferenceDicts", "meta_dict.txt")
    sprite_master = {}
    image_master = {}

    controller = Controller(win, save, save_player_profile)
    controller.get_gamepad(notify=False)
    joystick_tolerance = 0.1

    while True:
        load_player_profile(controller)
        if isfile(join("Assets", "Screens", "credit.png")):
            play_slide(pygame.image.load(join("Assets", "Screens", "credit.png")), controller, should_glitch=True)
        pygame.mixer.music.set_volume(controller.master_volume["background"] / 100)
        new_game = False
        if isfile(join("Assets", "Screens", "title.png")):
            slide = pygame.image.load(join("Assets", "Screens", "title.png"))
            overlay = pygame.image.load(join("Assets", "Screens", "title_overlay.png"))
            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill((0, 0, 0))
            for i in range(64):
                win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(255 - (4 * i))
                win.blit(black, (0, 0))
                pygame.display.update()
                time.sleep(0.01)
            has_save = isfile("GameData/save.p")
            if has_save:
                controller.main_menu.buttons[0][1].set_alpha(255)
                controller.main_menu.buttons[0][2].set_alpha(255)
            else:
                controller.main_menu.buttons[0][1].set_alpha(128)
                controller.main_menu.buttons[0][2].set_alpha(128)
            new_game = controller.main(show_continue=has_save)
            for i in range(64):
                win.blit(slide, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                pygame.display.update()
                time.sleep(0.01)
        else:
            handle_exception(FileNotFoundError(join("Assets", "Screens", "title.png")))
        load_data = None
        level = None
        while True:
            should_load = controller.goto_load = False
            if new_game:
                level = sorted(levels)[0]
                save_player_profile(controller, level=level)
                new_game = False
            elif controller.goto_restart:
                controller.goto_restart = False
            else:
                load_data = load_part1()
                levels_completed = len(load_player_profile(controller))
                if load_data is None:
                    if levels_completed < len(levels):
                        level = sorted(levels)[levels_completed]
                    else:
                        break
                elif levels_completed < len(levels):
                    level = sorted(levels)[levels_completed]
                    if level == load_data["level"]:
                        should_load = True
                else:
                    break

            if meta_dict.get(level) is not None and meta_dict[level].get("music") is not None:
                file = join("Assets", "LevelMusic", meta_dict[level]["music"])
                if isfile(file):
                    pygame.mixer.music.load(file)
                    pygame.mixer.music.set_volume(controller.master_volume["background"] / 100)
                    pygame.mixer.music.play(loops=-1)

            if meta_dict.get(level) is not None and meta_dict[level].get("start") is not None:
                if isfile(join("Assets", "Screens", meta_dict[level]["start"])):
                    play_slide(pygame.image.load(join("Assets", "Screens", meta_dict[level]["start"])), controller)
                elif isinstance(meta_dict[level]["start"], list):
                    for item in meta_dict[level]["start"]:
                        if isfile(join("Assets", "Screens", item)):
                            play_slide(pygame.image.load(join("Assets", "Screens", item)), controller)
                else:
                    print("Starting level " + level)

            controller.objects = [level]
            level_bounds, player, blocks, triggers, hazards, enemies = build_level(levels[level], sprite_master, image_master, objects_dict, load_audios("PlayerAudio"), load_audios("EnemyAudio"), win, controller)
            controller.objects.append([player] + blocks + triggers + hazards + enemies)

            hud = HUD(player, win)
            controller.hud = hud

            if should_load:
                load_part2(load_data, controller.objects)

            save(controller.objects, None)

            controller.get_gamepad()

            background, bg_image = get_background(("Blue.png" if meta_dict.get(level) is None or meta_dict[level].get("background") is None or not isfile(join("Assets", "Background", meta_dict[level]["background"])) else meta_dict[level]["background"]), level_bounds)
            offset_x = 0
            offset_y = 0
            scroll_area_width = WIDTH * 0.375
            scroll_area_height = HEIGHT * 0.125
    
            for enemy in enemies:
                enemy.player = player

            fade_in(background, bg_image, player, blocks + hazards + enemies, hud, offset_x, offset_y, controller)
            display_text(["Arriving at mission " + controller.objects[0].replace("_", " ") + "."], win, controller)
    
            dtime_offset = 0
            level_time = 0
            glitch_timer = 0
            glitches = None
            level_completed = False
            clock.tick(FPS_TARGET)
            while True:
                dtime = clock.tick(FPS_TARGET) - dtime_offset
                level_time += dtime
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
                        save_player_profile(controller)
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        dtime_offset += controller.handle_single_input(event.key, player, win)
                    elif event.type == pygame.KEYUP:
                        player.stop()
                    elif event.type == pygame.JOYBUTTONDOWN:
                        dtime_offset += controller.handle_single_input(event.button, player, win)
                    elif event.type == pygame.JOYBUTTONUP:
                        player.stop()
                    elif event.type == pygame.JOYAXISMOTION and event.value > joystick_tolerance:
                        dtime_offset += controller.handle_single_input("a" + str(event.axis), player, win)
                controller.handle_continuous_input(player)
                if (controller.goto_load and isfile("GameData/save.p")) or controller.goto_main or controller.goto_restart:
                    break

                result = player.loop(FPS_TARGET, dtime, blocks + hazards + enemies, triggers, None)
                if result[1]:
                    level_completed = True
                    break
                dtime_offset += result[0]
                if player.hp <= 0:
                    if controller.difficulty >= DifficultyScale.HARDEST:
                        controller.goto_restart = True
                        break
                    else:
                        player.revert()
    
                for block in (blocks + hazards):
                    if block.hp <= 0:
                        blocks.remove(block)
                    elif isinstance(block, MovingBlock):
                        block.patrol()
                        block.loop(dtime)
                    elif isinstance(block, MovableBlock):
                        block.loop(dtime, blocks)
    
                for enemy in enemies:
                    if enemy.hp <= 0:
                        enemies.remove(enemy)
                    else:
                        enemy.loop(FPS_TARGET, dtime, blocks, None, player)
                        enemy.patrol()

                if glitch_timer <= 0 and random.randint(0, 100) / 100 > player.hp / player.max_hp:
                    glitches = glitch((1 - max(player.hp / player.max_hp, 0)) * 0.75, win)
                    glitch_timer = 0.5
                draw(background, bg_image, player, blocks + hazards + enemies, hud, offset_x, offset_y, controller.master_volume, glitches=glitches)
                pygame.display.update()

                if player.rect.right - scroll_area_width < offset_x:
                    offset_x = player.rect.right - scroll_area_width
                elif player.rect.left + scroll_area_width > offset_x + WIDTH:
                    offset_x = player.rect.left - (WIDTH - scroll_area_width)
                if offset_x < level_bounds[0][0]:
                    offset_x = level_bounds[0][0]
                elif offset_x > level_bounds[1][0] - WIDTH:
                    offset_x = level_bounds[1][0] - WIDTH
    
                if player.rect.bottom - (2 * scroll_area_height) < offset_y:
                    offset_y = player.rect.bottom - (2 * scroll_area_height)
                elif player.rect.top - (HEIGHT - scroll_area_height) > offset_y:
                    offset_y = player.rect.top - (HEIGHT - scroll_area_height)
                if offset_y < level_bounds[0][1]:
                    offset_y = level_bounds[0][1]
                elif offset_y > level_bounds[1][1] - HEIGHT:
                    offset_y = level_bounds[1][1] - HEIGHT

            if meta_dict.get(level) is not None and meta_dict[level].get("music") is not None and isfile(join("Assets", "LevelMusic", meta_dict[level]["music"])):
                pygame.mixer.music.unload()

            if controller.goto_main:
                break
            elif level_completed:
                save_player_profile(controller, level)
                fade_out(background, bg_image, player, blocks + hazards + enemies, hud, offset_x, offset_y, controller)
                if meta_dict.get(level) is not None and meta_dict[level].get("end") is not None:
                    if isfile(join("Assets", "Screens", meta_dict[level]["end"])):
                        play_slide(pygame.image.load(join("Assets", "Screens", meta_dict[level]["end"])), controller)
                    elif isinstance(meta_dict[level]["end"], list):
                        for item in meta_dict[level]["end"]:
                            if isfile(join("Assets", "Screens", item)):
                                play_slide(pygame.image.load(join("Assets", "Screens", item)), controller)
                    if isfile(join("Assets", "Screens", "recap.png")):
                        minutes = level_time // 60000
                        seconds = (level_time - (minutes * 60000)) // 1000
                        milliseconds = level_time - ((minutes * 60000) + (seconds * 1000))
                        formatted_time = ("0" if minutes < 10 else "") + str(minutes) + ":" + ("0" if seconds < 10 else "") + str(seconds) + "." + ("0" if milliseconds < 100 else "") + ("0" if milliseconds < 10 else "") + str(milliseconds)
                        play_slide(pygame.image.load(join("Assets", "Screens", "recap.png")), controller, text=["Mission successful.", "Mission time: " + formatted_time + "."])

        if not controller.goto_main:
            if isfile(join("Assets", "Screens", "all_done.png")):
                play_slide(pygame.image.load(join("Assets", "Screens", "all_done.png")), controller)
        else:
            controller.goto_main = False

if __name__ == "__main__":
    main(WINDOW)

# test switch pro and ps5 controllers
# bugs: get sight ranges to display properly in the first spawn
# assets:   levels
#           music
#           sounds for typing, speaking, breaking blocks, moving blocks, all empty audio folders
#           HUD icons
#           shooting sprites
#           player sprites
#           screens
#           story and dialogue
# then package with nuitka

# later:    bosses
#           sprite sheets for moving blocks, hazards, and moving hazards
#           bouncers, lasers
#           make missiles explode at end of range
