import pygame
from SteamworksConnection import SteamworksConnection
from Helpers import load_json_dict, load_object_dicts, load_levels, load_audios, display_text, DifficultyScale, \
    handle_exception, load_text_from_file, ASSETS_FOLDER, GAME_DATA_FOLDER, FIRST_LEVEL_NAME, retroify_image, \
    load_images
from os.path import join, isfile, abspath
from DiscordConnection import DiscordConnection
from SimpleVFX.SimpleVFX import VisualEffectsManager

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
    handle_exception(f'File {FileNotFoundError(abspath(icon))} not found.')

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

    controller = Controller(None, win, main_menu_music=(None if meta_dict.get("MAIN_MENU") is None or meta_dict["MAIN_MENU"].get("music") is None else list(meta_dict["MAIN_MENU"]["music"].split(' '))), steamworks=steamworks, discord=discord)
    controller.get_gamepad(notify=False)
    controller.has_dlc.update(steamworks.has_dlc())

    if meta_dict.get("MAIN_MENU") is not None and meta_dict["MAIN_MENU"].get("start_cinematics") is not None:
        start_cinematics = meta_dict["MAIN_MENU"]["start_cinematics"]
    else:
        start_cinematics = {}
    if meta_dict.get("MAIN_MENU") is not None and meta_dict["MAIN_MENU"].get("recap_cinematics") is not None:
        recap_cinematics = meta_dict["MAIN_MENU"]["recap_cinematics"]
    else:
        recap_cinematics = {}
    if meta_dict.get("MAIN_MENU") is not None and meta_dict["MAIN_MENU"].get("end_cinematics") is not None:
        end_cinematics = meta_dict["MAIN_MENU"]["end_cinematics"]
    else:
        end_cinematics = {}

    cinematics_files = start_cinematics + recap_cinematics + end_cinematics
    cinematics = CinematicsManager(cinematics_files, controller)
    loading_screens = load_images("LoadingScreens", None)

    if meta_dict.get("MAIN_MENU") is not None and meta_dict["MAIN_MENU"].get("title_screen") is not None:
        title_screen_file = join(ASSETS_FOLDER, "Screens", meta_dict["MAIN_MENU"]["title_screen"])
    else:
        title_screen_file = join(ASSETS_FOLDER, "Screens", "title.png")

    if meta_dict.get("MAIN_MENU") is not None and meta_dict["MAIN_MENU"].get("title_screen_retro") is not None:
        title_screen_retro_file = join(ASSETS_FOLDER, "Screens", meta_dict["MAIN_MENU"]["title_screen_retro"])
    else:
        title_screen_retro_file = title_screen_file

    camera = Camera(win)

    while True:
        if len(load_player_profile(controller)) == 0:
            pygame.display.toggle_fullscreen()
        if not controller.goto_main:
            for cinematic in start_cinematics:
                cinematics.play(cinematic["name"], win)
        controller.refresh_selector_images()
        pygame.mixer.music.set_volume(controller.master_volume["background"])
        new_game = False
        if isfile(title_screen_file):
            slide = pygame.image.load(title_screen_file).convert_alpha()
            slide = pygame.transform.scale_by(slide, (win.get_width() / slide.get_width(), win.get_height() / slide.get_height()))
            slide_retro = pygame.image.load(title_screen_retro_file).convert_alpha()
            slide_retro = retroify_image(pygame.transform.scale_by(slide_retro, (win.get_width() / slide_retro.get_width(), win.get_height() / slide_retro.get_height())))
            controller.main_menu.clear_normal = slide.copy()
            controller.main_menu.clear_retro = slide_retro.copy()
            black = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)
            black.fill((0, 0, 0))
            if not controller.goto_main:
                for i in range(64):
                    win.blit((slide_retro if controller.retro else slide), ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                    black.set_alpha(255 - (4 * i))
                    win.blit(black, (0, 0))
                    pygame.display.update()
                    time.sleep(0.01)
            controller.main_menu.buttons[1].is_enabled = isfile(join(GAME_DATA_FOLDER, "save.p"))
            new_game = controller.main()
            for i in range(64):
                win.blit((slide_retro if controller.retro else slide), ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                #win.blit(overlay, ((win.get_width() - slide.get_width()) // 2, (win.get_height() - slide.get_height()) // 2))
                black.set_alpha(4 * i)
                win.blit(black, (0, 0))
                pygame.display.update()
                time.sleep(0.01)
        else:
            handle_exception(f'File {FileNotFoundError(abspath(title_screen_file))} not found.')
        controller.goto_main = False
        load_data = None
        cur_level = None
        while True:
            # THIS PART LOADS EVERYTHING: #
            loading_screen = list(loading_screens.values())[random.randint(0, len(loading_screens) - 1)]
            if controller.retro:
                loading_screen = retroify_image(loading_screen)
            win.fill((0, 0, 0))
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text("Loading mission... [1/3]", controller, min_pause_time=0, should_sleep=False, retro=controller.retro)
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
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text("Loading mission... [2/3]", controller, min_pause_time=0, should_sleep=False, retro=controller.retro)
            player_audio = enemy_audio = load_audios("Actors")
            block_audio = load_audios("Blocks")
            message_audio = load_audios("Messages", dir2=cur_level)
            vfx_manager = VisualEffectsManager(join(ASSETS_FOLDER, "VisualEffects"))
            win.fill((0, 0, 0))
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text("Loading mission... [3/3]", controller, min_pause_time=0, should_sleep=False, retro=controller.retro)
            controller.level = level = Level(cur_level, levels, meta_dict, objects_dict, {}, {}, player_audio, enemy_audio, block_audio, message_audio, vfx_manager, win, controller, loading_screen)

            win.fill((0, 0, 0))
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text("Loading agent...", controller, min_pause_time=0, should_sleep=False, retro=level.retro)
            if controller.player_abilities is not None:
                for key in controller.player_abilities:
                    setattr(level.player, key, controller.player_abilities[key])
            else:
                controller.player_abilities = {"can_wall_jump": level.player.can_wall_jump, "can_teleport": level.player.can_teleport, "can_bullet_time": level.player.can_bullet_time, "can_resize": level.player.can_resize, "can_heal": level.player.can_heal, "max_jumps": level.player.max_jumps}

            win.fill((0, 0, 0))
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            display_text("Initializing controls...", controller, min_pause_time=0, should_sleep=False, retro=level.retro)
            controller.hud = hud = HUD(level.player, win, retro=level.retro)

            if should_load:
                load_part2(load_data, controller.level)
            controller.save()
            controller.get_gamepad()

            win.fill((0, 0, 0))
            win.blit(loading_screen, ((win.get_width() - loading_screen.get_width()) / 2, (win.get_height() - loading_screen.get_height()) / 2))
            funny_loading_text = ["Applying finishing touches", "Applying one last coat of paint", "Almost done", "Any minute now", "Nearly there", "One more thing", "Tidying up", "Training agent", "Catching the train", "Finishing lunch", "Folding laundry"]
            display_text(f'{funny_loading_text[random.randint(0, len(funny_loading_text) - 1)]}...', controller, min_pause_time=0, should_sleep=False, retro=level.retro)

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
                display_text(load_text_from_file(level.start_message), controller, should_type_text=True, retro=level.retro)
    
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
                        level.player.stop()
                    elif event.type == pygame.JOYBUTTONDOWN:
                        dtime_offset += controller.handle_single_input(event.button, win)
                    elif event.type == pygame.JOYBUTTONUP:
                        level.player.stop()
                    elif event.type == pygame.USEREVENT:
                        pygame.mixer.music.play()
                        if "LOOP" not in controller.music[controller.music_index].upper():
                            controller.cycle_music()
                controller.handle_continuous_input()
                if (controller.goto_load and isfile(join(GAME_DATA_FOLDER, "save.p"))) or controller.goto_main or controller.goto_restart:
                    break

                result = level.player.loop(dtime)
                if result[1] is not None:
                    next_level = result[1]
                    break
                dtime_offset += result[0]
                if level.player.hp <= 0:
                    if controller.difficulty >= DifficultyScale.HARDEST:
                        controller.goto_restart = True
                        break
                    else:
                        dtime_offset += level.player.revert()

                vfx_manager.manage(dtime)
                for ent in level.get_entities():
                    if (not isinstance(ent, Actor) and type(ent).__name__.upper() != "BLOCK") or (isinstance(ent, Actor) and math.dist(ent.rect.center, (camera.focus_x, camera.focus_y)) < win.get_width() * 1.5):
                        if hasattr(ent, "patrol") and callable(ent.patrol):
                            ent.patrol(dtime)
                        ent.loop(dtime)
                        if isinstance(ent, NonPlayer) and ent.queued_message is not None:
                            dtime_offset += ent.play_queued_message()

                level.purge()

                for effect in level.particle_effects:
                    effect.loop(dtime)

                if level.can_glitch and glitch_timer <= 0 and random.randint(0, 100) / 100 > level.player.hp / level.player.max_hp:
                    glitches = glitch((1 - max(level.player.hp / level.player.max_hp, 0)) / 2, win)
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
                display_text("Updating your steam achievements...", controller, min_pause_time=0, should_sleep=False, retro=level.retro)
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
                    display_text(load_text_from_file(level.end_message), controller, should_type_text=True, retro=level.retro)
                controller.save_player_profile()
                camera.fade_out(controller)
                if level.end_cinematic is not None:
                    for cinematic in level.end_cinematic:
                        level.cinematics.play(cinematic, win)
                for cinematic in recap_cinematics:
                    cinematics.cinematics[cinematic["name"]].text = ["Mission successful."] + level.get_recap_text()
                    cinematics.play(cinematic["name"], win)
                cur_level = next_level

        if not controller.goto_main:
            for cinematic in end_cinematics:
                cinematics.play(cinematic["name"], win)


if __name__ == "__main__":
    try:
        main(WINDOW)
    except Exception as e:
        traceback.print_exception(e)
        handle_exception(str(e))
