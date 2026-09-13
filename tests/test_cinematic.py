"""Tests for ``CinematicsManager`` and ``Cinematic`` -- loading, queueing and dispatch.

The playback routines themselves run their own blocking event/render loop, so these
tests cover loading, the queue, the slide/video dispatch decision and the lifecycle
around a play (mixer pause, delete-after-play), with the inner loop stubbed out.
"""

from __future__ import annotations

import cv2
import pygame
import pytest

from Cinematic import Cinematic, CinematicsManager, CinematicType
from Helpers import load_sprite_sheets
from support.patches import HandledError
from support.stubs import frames_are_available as stubs_frames_available


SLIDE = {"name": "intro", "type": "slide", "file": "slide.png"}
VIDEO = {"name": "outro", "type": "video", "file": "clip.mp4"}


@pytest.fixture
def manager(controller) -> CinematicsManager:
    return CinematicsManager([SLIDE, VIDEO], controller)


class TestLoading:
    def test_a_single_definition_is_accepted_without_a_list(self, controller) -> None:
        assert set(CinematicsManager(SLIDE, controller).cinematics) == {"intro"}

    def test_a_list_of_definitions_loads_them_all(self, manager) -> None:
        assert set(manager.cinematics) == {"intro", "outro"}

    def test_a_tuple_of_definitions_works_too(self, controller) -> None:
        assert set(CinematicsManager((SLIDE,), controller).cinematics) == {"intro"}

    def test_slides_load_as_surfaces(self, manager) -> None:
        assert manager.cinematics["intro"].type is CinematicType.SLIDE
        assert isinstance(manager.cinematics["intro"].cinematic, pygame.Surface)

    def test_videos_load_as_capture_handles(self, manager) -> None:
        assert manager.cinematics["outro"].type is CinematicType.VIDEO
        assert isinstance(manager.cinematics["outro"].cinematic, cv2.VideoCapture)

    def test_a_missing_file_is_fatal(self, controller) -> None:
        with pytest.raises(HandledError):
            CinematicsManager({"name": "x", "type": "slide", "file": "nope.png"},
                              controller)

    def test_a_null_file_is_skipped(self, controller) -> None:
        assert CinematicsManager({"name": "x", "type": "slide", "file": None},
                                 controller).cinematics == {}

    def test_the_type_is_matched_case_insensitively(self, controller) -> None:
        definition = dict(SLIDE, type = "SlIdE")
        assert CinematicsManager(definition, controller).cinematics["intro"].type \
            is CinematicType.SLIDE

    def test_playback_flags_default_sensibly(self, manager) -> None:
        slide = manager.cinematics["intro"]
        assert slide.should_fade_in is True
        assert slide.should_fade_out is True
        assert slide.should_glitch is False
        assert slide.delete_after_play is False

    def test_playback_flags_can_be_overridden(self, controller) -> None:
        definition = dict(SLIDE, should_glitch = True, should_fade_in = False,
                          stretch = True, delete = True)
        slide = CinematicsManager(definition, controller).cinematics["intro"]
        assert slide.should_glitch is True
        assert slide.should_fade_in is False
        assert slide.stretch is True
        assert slide.delete_after_play is True


class TestPlayerBlit:
    def test_a_player_sprite_can_be_composited_onto_a_slide(self, controller,
                                                            sprite_master) -> None:
        sprites = load_sprite_sheets("Sprites", "Player1", sprite_master,
                                     direction = True)
        definition = dict(SLIDE, player_blit = [
            {"animation": "idle", "facing": "right", "frame": 1, "coord": [10, 10]}])
        manager = CinematicsManager(definition, controller, player_sprites = sprites)
        assert manager.cinematics["intro"].cinematic is not None

    def test_negative_coordinates_are_measured_from_the_far_edge(self, controller,
                                                                 sprite_master) -> None:
        sprites = load_sprite_sheets("Sprites", "Player1", sprite_master,
                                     direction = True)
        blit = {"animation": "idle", "facing": "right", "frame": 1, "coord": [-40, -40]}
        CinematicsManager(dict(SLIDE, player_blit = [blit]), controller,
                          player_sprites = sprites)
        # The coordinate list is rewritten in place with the resolved position.
        assert blit["coord"][0] > 0 and blit["coord"][1] > 0

    def test_a_malformed_blit_specification_is_skipped(self, controller,
                                                       sprite_master) -> None:
        sprites = load_sprite_sheets("Sprites", "Player1", sprite_master,
                                     direction = True)
        definition = dict(SLIDE, player_blit = [{"animation": "idle"}])
        assert CinematicsManager(definition, controller,
                                 player_sprites = sprites).cinematics["intro"]

    def test_videos_never_take_a_player_blit(self, manager) -> None:
        assert isinstance(manager.cinematics["outro"].cinematic, cv2.VideoCapture)


class TestQueue:
    def test_queueing_records_the_name(self, manager) -> None:
        manager.queue("intro")
        assert manager.queued == ["intro"]

    def test_the_queue_preserves_order(self, manager) -> None:
        manager.queue("outro")
        manager.queue("intro")
        assert manager.queued == ["outro", "intro"]

    def test_clearing_empties_the_queue(self, manager) -> None:
        manager.queue("intro")
        manager.clear_queue()
        assert manager.queued == []

    def test_playing_the_queue_runs_each_entry_and_empties_it(
            self, manager, monkeypatch: pytest.MonkeyPatch, window) -> None:
        played: list = []
        for name, cinematic in manager.cinematics.items():
            monkeypatch.setattr(cinematic, "play",
                                lambda win, n = name: (played.append(n), 0.25)[1])
        manager.queue("intro")
        manager.queue("outro")

        assert manager.play_queue(window) == pytest.approx(0.5)
        assert played == ["intro", "outro"]
        assert manager.queued == []

    def test_an_empty_queue_costs_nothing(self, manager, window) -> None:
        assert manager.play_queue(window) == 0.0


class TestPlay:
    def test_playing_an_unknown_name_costs_nothing(self, manager, window) -> None:
        assert manager.play("missing", window) == 0.0

    def test_playing_returns_the_elapsed_time(self, manager, window,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(manager.cinematics["intro"], "play", lambda win: 1.5)
        assert manager.play("intro", window) == 1.5

    def test_a_delete_after_play_cinematic_is_dropped_once_shown(
            self, controller, window, monkeypatch: pytest.MonkeyPatch) -> None:
        manager = CinematicsManager(dict(SLIDE, delete = True), controller)
        monkeypatch.setattr(manager.cinematics["intro"], "play", lambda win: 0.0)
        manager.play("intro", window)
        assert "intro" not in manager.cinematics

    def test_a_repeatable_cinematic_survives(self, manager, window,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(manager.cinematics["intro"], "play", lambda win: 0.0)
        manager.play("intro", window)
        assert "intro" in manager.cinematics


class TestDispatch:
    def test_a_slide_is_routed_to_the_slide_player(self, manager, window,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(Cinematic, "__play_slide__",
                            staticmethod(lambda *a, **k: calls.append("slide")))
        monkeypatch.setattr(Cinematic, "__play_video__",
                            staticmethod(lambda *a, **k: calls.append("video")))
        manager.cinematics["intro"].play(window)
        assert calls == ["slide"]

    def test_a_video_is_routed_to_the_video_player(self, manager, window,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(Cinematic, "__play_slide__",
                            staticmethod(lambda *a, **k: calls.append("slide")))
        monkeypatch.setattr(Cinematic, "__play_video__",
                            staticmethod(lambda *a, **k: calls.append("video")))
        manager.cinematics["outro"].play(window)
        assert calls == ["video"]

    def test_playback_pauses_and_resumes_the_sound_effects_mixer(
            self, manager, window, monkeypatch: pytest.MonkeyPatch) -> None:
        events: list = []
        monkeypatch.setattr(pygame.mixer, "pause", lambda: events.append("pause"))
        monkeypatch.setattr(pygame.mixer, "unpause", lambda: events.append("unpause"))
        monkeypatch.setattr(Cinematic, "__play_slide__", staticmethod(lambda *a, **k: None))
        manager.cinematics["intro"].play(window)
        assert events == ["pause", "unpause"]

    def test_playback_reports_the_wall_clock_cost(self, manager, window,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Cinematic, "__play_slide__", staticmethod(lambda *a, **k: None))
        assert manager.cinematics["intro"].play(window) >= 0.0


def test_the_manager_has_no_get_method(manager) -> None:
    """Pins the defect behind the xfail in ``tests/test_trigger.py``.

    ``CinematicTrigger.collide`` calls ``level.cinematics.get(name)``.  Nothing on
    ``CinematicsManager`` provides that; the dictionary it wraps is ``.cinematics``.
    See BUGS_FOUND.md #6.
    """
    assert not hasattr(manager, "get")
    assert "intro" in manager.cinematics


# --------------------------------------------------------------------------- #
# playback
# --------------------------------------------------------------------------- #
class _SleepTimeout(Exception):
    """Raised by the patched sleep to break out of a loop that will not end."""


@pytest.fixture
def fast_sleep(monkeypatch: pytest.MonkeyPatch):
    """Replace ``time.sleep`` inside Cinematic with a counter that can time out.

    Playback is a render loop paced by ``time.sleep(0.01)``; without this a single
    slide would take several real seconds.  The returned helper also lets a test cap
    the number of iterations, so a loop that can never exit fails instead of hanging.
    """
    import time as time_module

    state = {"calls": 0, "limit": 100_000, "on_sleep": None}

    def _sleep(_seconds: float) -> None:
        state["calls"] += 1
        if state["on_sleep"] is not None:
            state["on_sleep"]()
        if state["calls"] > state["limit"]:
            raise _SleepTimeout(f"still looping after {state['calls']} frames")

    monkeypatch.setattr(time_module, "sleep", _sleep)
    return state


@pytest.mark.slow
class TestSlidePlayback:
    def _slide(self, width: int = 320, height: int = 180) -> pygame.Surface:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill((180, 180, 180, 255))
        return surface

    def test_a_plain_slide_plays_through(self, controller, window, fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(), controller, window)
        assert fast_sleep["calls"] > 0

    def test_skipping_the_fades_shortens_the_run(self, controller, window,
                                                 fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(), controller, window,
                                 should_fade_in = False, should_fade_out = False)
        without_fades = fast_sleep["calls"]
        fast_sleep["calls"] = 0
        Cinematic.__play_slide__(self._slide(), controller, window)
        assert fast_sleep["calls"] > without_fades

    def test_a_key_press_skips_the_slide(self, controller, window, fast_sleep) -> None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_SPACE))
        Cinematic.__play_slide__(self._slide(), controller, window)
        assert fast_sleep["calls"] <= 2

    def test_a_stretched_slide_fills_the_window(self, controller, window,
                                                fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(), controller, window, stretch = True,
                                 should_fade_in = False, should_fade_out = False)

    def test_scaling_can_be_refused_in_both_directions(self, controller, window,
                                                       fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(4000, 4000), controller, window,
                                 can_scale_down = False, should_fade_in = False,
                                 should_fade_out = False)
        Cinematic.__play_slide__(self._slide(8, 8), controller, window,
                                 can_scale_up = False, should_fade_in = False,
                                 should_fade_out = False)

    def test_caption_text_is_rendered_onto_the_slide(self, controller, window,
                                                     fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(), controller, window,
                                 text = ["Line one", "Line two"],
                                 should_fade_in = False, should_fade_out = False)

    def test_the_glitch_overlay_runs(self, controller, window, fast_sleep) -> None:
        Cinematic.__play_slide__(self._slide(), controller, window,
                                 should_glitch = True, should_fade_in = False)

    def test_a_dark_slide_gets_light_caption_text(self, controller, window,
                                                  fast_sleep) -> None:
        dark = pygame.Surface((320, 180), pygame.SRCALPHA)
        dark.fill((10, 10, 10, 255))
        Cinematic.__play_slide__(dark, controller, window, text = ["Dark"],
                                 should_fade_in = False, should_fade_out = False)

    def test_a_retro_slide_plays(self, controller, window, fast_sleep) -> None:
        controller.force_retro = True
        Cinematic.__play_slide__(self._slide(), controller, window,
                                 should_fade_in = False, should_fade_out = False)

    def test_a_quit_event_quits_the_game(self, controller, window, fast_sleep) -> None:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        Cinematic.__play_slide__(self._slide(), controller, window)
        assert controller.quit_calls == 1

    def test_a_pause_key_cinematic_can_never_be_dismissed(self, controller, window,
                                                          fast_sleep) -> None:
        """Characterisation of a game-freezing defect.

        The pause-to-continue gate resolves its accepted keys with
        ``hasattr(controller, key)`` -- but the bindings live in
        ``Controller.KEYBOARD_LAYOUTS[layout][key]``, not as attributes on the
        controller.  ``valid_keys`` therefore stays empty and the ``while True``
        never breaks, whatever the player presses.  Any cinematic authored with
        ``pause_key`` hard-locks the game.  See BUGS_FOUND.md #15.
        """
        # The 1-second "hold the slide" loop runs first and skips on any key press,
        # so the key is only offered once playback has reached the pause gate
        # (100 frames at 0.01s).
        fast_sleep["limit"] = 160
        fast_sleep["on_sleep"] = lambda: (
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_UP))
            if fast_sleep["calls"] > 105 else None)

        with pytest.raises(_SleepTimeout):
            Cinematic.__play_slide__(self._slide(), controller, window,
                                     pause_key = "keys_jump",
                                     should_fade_in = False, should_fade_out = False)

    def test_the_gate_does_open_when_the_binding_is_an_attribute(self, controller,
                                                                 window,
                                                                 fast_sleep) -> None:
        """The same gate, fed the shape it actually expects, does work.

        This is what the fix would look like from the outside: ``pause_key`` naming
        something ``getattr(controller, ...)`` can find, holding a list of key codes.
        """
        controller.keys_continue = [pygame.K_UP]
        fast_sleep["limit"] = 200
        fast_sleep["on_sleep"] = lambda: (
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_UP))
            if fast_sleep["calls"] > 105 else None)

        Cinematic.__play_slide__(self._slide(), controller, window,
                                 pause_key = "keys_continue",
                                 should_fade_in = False, should_fade_out = False)


@pytest.mark.slow
@pytest.mark.skipif(not stubs_frames_available(),
                    reason = "numpy is required to feed frames to pygame.surfarray")
class TestVideoPlayback:
    def test_a_video_plays_every_frame_and_releases_the_handle(self, controller,
                                                               window,
                                                               fast_sleep) -> None:
        capture = cv2.VideoCapture("clip.mp4")
        Cinematic.__play_video__(capture, controller, window,
                                 should_fade_in = False, should_fade_out = False)
        assert capture._released == 1

    def test_a_closed_capture_is_an_error(self, controller, window) -> None:
        capture = cv2.VideoCapture("clip.mp4")
        capture.release()
        with pytest.raises(IOError):
            Cinematic.__play_video__(capture, controller, window)

    def test_a_key_press_skips_the_video(self, controller, window, fast_sleep) -> None:
        capture = cv2.VideoCapture("clip.mp4")
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key = pygame.K_SPACE))
        Cinematic.__play_video__(capture, controller, window)
        assert fast_sleep["calls"] <= 2

    def test_caption_text_and_stretch_run(self, controller, window,
                                          fast_sleep) -> None:
        capture = cv2.VideoCapture("clip.mp4")
        Cinematic.__play_video__(capture, controller, window, text = ["Subtitle"],
                                 stretch = True, should_fade_in = False,
                                 should_fade_out = False)

    def test_the_fades_and_glitch_run(self, controller, window, fast_sleep) -> None:
        capture = cv2.VideoCapture("clip.mp4")
        Cinematic.__play_video__(capture, controller, window, should_glitch = True)
