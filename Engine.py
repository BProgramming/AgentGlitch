import pygame
from SteamworksConnection import SteamworksConnection
from Helpers import load_json_dict, load_object_dicts, load_levels, load_audios, display_text, DifficultyScale, handle_exception, load_text_from_file, ASSETS_FOLDER, GAME_DATA_FOLDER, FIRST_LEVEL_NAME
from os.path import join, isfile
from VisualEffects import VisualEffectsManager
from DiscordConnection import DiscordConnection


# This stuff happens in the middle of imports because some classes require pygame display available before they can be imported
# And steam is initialized first because it doesn't work having it after pygame.init for... reasons?
steamworks = SteamworksConnection()
discord = DiscordConnection()
discord.set_status(details="In the menu:", state="Gathering intel")

pygame.init()
WIDTH, HEIGHT = 1920, 1080
FPS_TARGET = 60

icon = join(ASSETS_FOLDER, "Icons", "icon_small.png")
if isfile(icon):
    pygame.display.set_icon(pygame.image.load(icon))
else:
    handle_exception("File " + str(FileNotFoundError(icon)) + " not found.")

WINDOW = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.SCALED)
pygame.display.set_caption("AGENT GLITCH")


import math
import random
import time
import sys
import traceback
from Cinematics import *
from Controller import Controller
from Level import Level
from HUD import HUD
from NonPlayer import NonPlayer
from Camera import Camera
from SaveLoadFunctions import *

def main(win):

    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    levels = load_levels("Levels")
    objects_dict = load_object_dicts("ReferenceDicts\\GameObjects")
    meta_dict = load_json_dict("ReferenceDicts", "meta.agd")
    sprite_master = {}
    image_master = {}

    controller = Controller(None, win, main_menu_music=(None if meta_dict.get("MAIN_MENU") is None or meta_dict["MAIN_MENU"].get("music") is None else list(meta_dict["MAIN_MENU"]["music"].split(' '))), steamworks=steamworks, discord=discord)
    controller.get_gamepad(notify=False)
    controller.has_dlc.update(steamworks.has_dlc())

    cinematics_files = [{"name": "credit1", "file": "credit1.png", "type": "SLIDE", "should_glitch": "TRUE"},
                        {"name": "credit2", "file": "credit2.png", "type": "SLIDE", "should_glitch": "TRUE"},
                        {"name": "recap", "file": "recap.png", "type": "SLIDE"},
                        {"name": "all_done", "file": "all_done.png", "type": "SLIDE"}]
    cinematics = CinematicsManager(cinematics_files, controller)

    camera = Camera(win)

    while True:
        if len(load_player_profile(controller)) == 0:
            pygame.display.toggle_fullscreen()
        if not controller.goto_main:
            cinematics.play("credit1", win)
            cinematics.play("credit2", win)
        pygame.mixer.music.set_volume(controller.master_volume["background"])
        new_game = False
        title_screen_file = join(ASSETS_FOLDER, "Screens", "title2.0.png")
        if isfile(title_screen_file):
            slide = pygame.transform.scale2x(pygame.image.load(title_screen_file).convert_alpha())
            slide_grayscale = pygame.transform.grayscale(slide)
            controller.main_menu.clear = slide.copy()
            controller.main_menu.clear_grayscale = slide_grayscale.copy()
            #overlay = pygame.image.load(join(ASSETS_FOLDER, "Screens", "title_overlay.png"))
            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill((0, 0, 0))
            if not controller.goto_main:
                for i in range(64):
                    win.blit((slide_grayscale if controller.force_grayscale else slide), ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                    #win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                    black.set_alpha(255 - (4 * i))
                    win.blit(black, (0, 0))
                    pygame.display.update()
                    time.sleep(0.01)
            if isfile(join(GAME_DATA_FOLDER, "save.p")):
                controller.main_menu.buttons[1][1].set_alpha(255)
                controller.main_menu.buttons[1][2].set_alpha(255)
            else:
                controller.main_menu.buttons[1][1].set_alpha(128)
                controller.main_menu.buttons[1][2].set_alpha(128)
            new_game = controller.main()
            for i in range(64):
                win.blit((slide_grayscale if controller.force_grayscale else slide), ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                #win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                pygame.display.update()
                time.sleep(0.01)
        else:
            handle_exception("File " + str(FileNotFoundError(title_screen_file)) + " not found.")
        controller.goto_main = False
        load_data = None
        cur_level = None
        while True:
            # THIS PART LOADS EVERYTHING: #
            win.fill((0, 0, 0))
            display_text("Loading mission.   [1/3]", controller, min_pause_time=0, should_sleep=False)
            should_load = False
            if new_game:
                cur_level = FIRST_LEVEL_NAME
                controller.save_player_profile()
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
            win.fill((0, 0, 0))
            display_text("Loading mission..  [2/3]", controller, min_pause_time=0, should_sleep=False)
            player_audio = enemy_audio = load_audios("Actors")
            block_audio = load_audios("Blocks")
            message_audio = load_audios("Messages", dir2=cur_level)
            vfx_manager = VisualEffectsManager(controller)
            win.fill((0, 0, 0))
            display_text("Loading mission... [3/3]", controller, min_pause_time=0, should_sleep=False)
            controller.level = level = Level(cur_level, levels, meta_dict, objects_dict, sprite_master, image_master, player_audio, enemy_audio, block_audio, message_audio, vfx_manager, win, controller)

            win.fill((0, 0, 0))
            display_text("Loading agent...", controller, min_pause_time=0, should_sleep=False)
            if controller.player_abilities is not None:
                for key in controller.player_abilities:
                    setattr(level.get_player(), key, controller.player_abilities[key])
            else:
                controller.player_abilities = {"can_wall_jump": level.get_player().can_wall_jump, "can_teleport": level.get_player().can_teleport, "can_bullet_time": level.get_player().can_bullet_time, "can_resize": level.get_player().can_resize, "can_heal": level.get_player().can_heal, "max_jumps": level.get_player().max_jumps}

            win.fill((0, 0, 0))
            display_text("Initializing controls...", controller, min_pause_time=0, should_sleep=False)
            controller.hud = hud = HUD(level.get_player(), win, grayscale=level.grayscale)

            if should_load:
                load_part2(load_data, controller.level)
            controller.save()
            controller.get_gamepad()

            win.fill((0, 0, 0))
            funny_loading_text = ["Applying finishing touches", "Applying one last coat of paint", "Almost done", "Any minute now", "Nearly there", "One more thing", "Tidying up", "Training agent", "Catching the train", "Finishing lunch", "Folding laundry"]
            display_text(funny_loading_text[random.randint(0, len(funny_loading_text) - 1)] + "...", controller, min_pause_time=0, should_sleep=False)

            camera.prepare(level, hud)
            camera.scroll_to_player(0)

            controller.discord.set_status(details="On a mission:", state=controller.level.display_name)

            # FROM HERE, THE LEVEL ACTUALLY STARTS: #
            if level.start_cinematic is not None:
                for cinematic in level.start_cinematic:
                    level.cinematics.play(cinematic, win)

            if level.music is not None:
                controller.queue_track_list()
                pygame.mixer.music.set_volume(controller.master_volume["background"])
                pygame.mixer.music.set_endevent(pygame.USEREVENT)
                pygame.mixer.music.play(fade_ms=2000)
                controller.cycle_music()

            camera.fade_in(controller)
            if level.start_message is not None:
                display_text(load_text_from_file(level.start_message), controller, should_type_text=True)
    
            dtime_offset = 0
            glitch_timer = 0
            glitches = None
            next_level = None
            clock.tick(FPS_TARGET)

            # MAIN GAME LOOP: #
            while True:
                dtime = clock.tick(FPS_TARGET) - dtime_offset
                dtime_offset = 0
                level.time += dtime

                if hud.save_icon_timer > 0:
                    hud.save_icon_timer -= dtime / 250
                if glitch_timer > 0:
                    glitch_timer -= dtime / 250
                    if glitch_timer <= 0:
                        glitch_timer = 0
                        glitches = None

                while len(level.cinematics.queued) > 0:
                    dtime_offset += level.cinematics.play_queue(win)

                dtime_offset += controller.get_gamepad()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        controller.save()
                        controller.quit()
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
                if (controller.goto_load and isfile(join(GAME_DATA_FOLDER, "save.p"))) or controller.goto_main or controller.goto_restart:
                    break

                result = level.get_player().loop(dtime)
                if result[1] is not None:
                    next_level = result[1]
                    break
                dtime_offset += result[0]
                if level.get_player().hp <= 0:
                    if controller.difficulty >= DifficultyScale.HARDEST:
                        controller.goto_restart = True
                        break
                    else:
                        dtime_offset += level.get_player().revert()

                for ent in level.get_entities():
                    if (not isinstance(ent, Actor) and type(ent).__name__.upper() != "BLOCK") or (isinstance(ent, Actor) and math.dist(ent.rect.center, (camera.focus_x, camera.focus_y)) < win.get_width() * 1.5):
                        if hasattr(ent, "patrol") and callable(ent.patrol):
                            ent.patrol(dtime)
                        ent.loop(dtime)
                        if isinstance(ent, NonPlayer) and ent.queued_message is not None:
                            dtime_offset += ent.play_queued_message()

                level.purge()

                if level.weather is not None:
                    level.weather.move(dtime)

                if level.can_glitch and glitch_timer <= 0 and random.randint(0, 100) / 100 > level.get_player().hp / level.get_player().max_hp:
                    glitches = glitch((1 - max(level.get_player().hp / level.get_player().max_hp, 0)) / 2, win)
                    glitch_timer = 0.5

                camera.draw(controller.master_volume, FPS_TARGET, glitches=glitches)
                pygame.display.update()

                if controller.should_scroll_to_point is not None:
                    camera.focus_player = False
                    if camera.scroll_to_point(dtime, controller.should_scroll_to_point["coords"][0], controller.should_scroll_to_point["coords"][1], target_wait_time=controller.should_scroll_to_point["time"]):
                        camera.focus_player = True
                        controller.should_scroll_to_point = None
                else:
                    camera.scroll_to_player(dtime)

                if controller.should_hot_swap_level:
                    controller.should_hot_swap_level = False
                    if level.hot_swap_level is not None:
                        cur_time = level.time
                        cur_achievements = level.achievements
                        cur_target_time = level.target_time
                        cur_objectives_collected = level.objectives_collected
                        controller.level = level = level.hot_swap_level
                        camera.prepare(level, hud)
                        level.time += cur_time
                        level.achievements.update(cur_achievements)
                        level.target_time += cur_target_time
                        level.objectives_collected += cur_objectives_collected

            if controller.music is not None:
                pygame.mixer.music.fadeout(1000)
                pygame.mixer.music.unload()

            controller.should_store_steam_stats = bool(controller.should_store_steam_stats or level.award_achievements(controller.steamworks))

            if controller.should_store_steam_stats and controller.steamworks is not None:
                controller.should_store_steam_stats = False
                win.fill((0, 0, 0))
                display_text("Updating your steam achievements...", controller, min_pause_time=0, should_sleep=False)
                while True:
                    if controller.steamworks.UserStats.StoreStats():
                        break
                    else:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                controller.quit()

            if controller.goto_main:
                break
            elif next_level is not None:
                if level.end_message is not None:
                    display_text(load_text_from_file(level.end_message), controller, should_type_text=True)
                controller.save_player_profile()
                camera.fade_out(controller)
                if level.end_cinematic is not None:
                    for cinematic in level.end_cinematic:
                        level.cinematics.play(cinematic, win)
                cinematics.cinematics["recap"].text = ["Mission successful."] + level.get_recap_text()
                cinematics.play("recap", win)
                if level.grayscale:
                    sprite_master.clear()
                    image_master.clear()
                cur_level = next_level

        if not controller.goto_main:
            cinematics.play("all_done", win)


if __name__ == "__main__":
    try:
        main(WINDOW)
    except Exception as e:
        traceback.print_exception(e)
        handle_exception(str(e))
