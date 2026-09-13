"""Tests for ``Helpers`` -- the module everything else imports from.

``Helpers`` holds the enums, the asset loaders, the text pipeline and the small
geometry/property utilities.  It is almost all pure logic, so it gets the densest
coverage in the suite: a regression here surfaces everywhere.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pygame
import pytest

import Helpers
from Helpers import (
    DifficultyScale,
    FALLBACK_GAMEPAD_LAYOUT,
    GAMEPAD_BUTTON_NAMES,
    MovementDirection,
    PathPoint,
    describe_binding,
    flip,
    gamepad_button_name,
    glitch,
    image_to_retro,
    link_trigger,
    load_audios,
    load_images,
    load_json_dict,
    load_level_images,
    load_levels,
    load_object_dicts,
    load_path,
    load_picker_sprites,
    load_sprite_sheets,
    load_text_from_file,
    make_image_from_text,
    process_text,
    set_property,
    set_sound_source,
    validate_file_list,
)
from support.assets import FRAME, FRAMES, LEVEL_NAME, MOVEMENT_STATES
from support.patches import HandledError


# --------------------------------------------------------------------------- #
# enums and constants
# --------------------------------------------------------------------------- #
class TestMovementDirection:
    def test_values_are_the_sign_of_travel(self) -> None:
        assert int(MovementDirection.LEFT) == -1
        assert int(MovementDirection.RIGHT) == 1

    def test_str_is_the_name_because_sprite_keys_use_it(self) -> None:
        # Actor looks sprites up as f"{state}_{facing}", so this is load-bearing.
        assert str(MovementDirection.LEFT) == "LEFT"
        assert str(MovementDirection.RIGHT) == "RIGHT"

    def test_swap_is_its_own_inverse(self) -> None:
        for direction in MovementDirection:
            assert direction.swap().swap() is direction
        assert MovementDirection.LEFT.swap() is MovementDirection.RIGHT

    def test_multiplies_like_an_int(self) -> None:
        assert MovementDirection.LEFT * 4 == -4
        assert float(MovementDirection.RIGHT) == 1.0


class TestDifficultyScale:
    def test_scales_bracket_medium(self) -> None:
        assert float(DifficultyScale.EASIEST) < float(DifficultyScale.MEDIUM)
        assert float(DifficultyScale.HARDEST) > float(DifficultyScale.MEDIUM)
        assert float(DifficultyScale.MEDIUM) == 1.0

    def test_str_swaps_underscores_for_spaces(self) -> None:
        assert str(DifficultyScale.EASIEST) == "EASIEST"

    def test_compares_against_plain_floats(self) -> None:
        # NonPlayer.draw gates the vision cone on `difficulty <= DifficultyScale.EASY`.
        assert 0.5 <= DifficultyScale.EASY
        assert not (1.0 <= DifficultyScale.EASY)


def test_rumble_duration_is_not_zero() -> None:
    # A zero duration rumbles forever; the source comment calls this out explicitly.
    assert Helpers.RUMBLE_EFFECT_DURATION > 0


def test_colour_constants_are_opaque_rgba() -> None:
    for colour in (Helpers.NORMAL_WHITE, Helpers.RETRO_WHITE,
                   Helpers.NORMAL_BLACK, Helpers.RETRO_BLACK):
        assert len(colour) == 4
        assert colour[3] == 255


# --------------------------------------------------------------------------- #
# handle_exception (the real one)
# --------------------------------------------------------------------------- #
def test_real_handle_exception_writes_a_timestamped_log(
        monkeypatch: pytest.MonkeyPatch, game_data_dir: Path) -> None:
    """The crash handler's one durable side effect is the log file."""
    shown: list[dict] = []
    monkeypatch.setattr(Helpers.messagebox, "showerror",
                        lambda **kwargs: shown.append(kwargs))
    monkeypatch.setattr(Helpers.sys, "exit", lambda *a: (_ for _ in ()).throw(SystemExit()))
    # Skip the pygame.quit() branch -- tearing the display down would break the
    # rest of the session, and it is not what this test is about.
    monkeypatch.setattr(Helpers.pygame, "get_init", lambda: False)

    with pytest.raises(SystemExit):
        Helpers.real_handle_exception("boom")

    logs = list(game_data_dir.glob("glitch_*.log"))
    assert len(logs) == 1
    assert "Error encountered at GMT" in logs[0].read_text()
    assert shown and "boom" in shown[0]["message"]


# --------------------------------------------------------------------------- #
# link_trigger
# --------------------------------------------------------------------------- #
class _NamedTrigger:
    def __init__(self, name: str) -> None:
        self.name = name


class TestLinkTrigger:
    def test_matches_on_case_insensitive_prefix(self) -> None:
        triggers = [_NamedTrigger("Alarm (0, 0)"), _NamedTrigger("Gate (96, 0)")]
        assert link_trigger(["alarm"], triggers) == [triggers[0]]

    def test_returns_one_match_per_name_in_request_order(self) -> None:
        triggers = [_NamedTrigger("Gate A"), _NamedTrigger("Alarm B")]
        assert link_trigger(["Alarm", "Gate"], triggers) == [triggers[1], triggers[0]]

    def test_stops_at_the_first_match_for_each_name(self) -> None:
        triggers = [_NamedTrigger("Gate A"), _NamedTrigger("Gate B")]
        assert link_trigger(["Gate"], triggers) == [triggers[0]]

    def test_unmatched_names_are_dropped_silently(self) -> None:
        assert link_trigger(["Nope"], [_NamedTrigger("Gate")]) == []

    def test_empty_prefix_matches_everything_first(self) -> None:
        # "".startswith("") is True, so a blank token grabs the first trigger.
        triggers = [_NamedTrigger("Gate")]
        assert link_trigger([""], triggers) == [triggers[0]]


# --------------------------------------------------------------------------- #
# validate_file_list
# --------------------------------------------------------------------------- #
class TestValidateFileList:
    def test_returns_resolved_paths_for_files_that_exist(self) -> None:
        out = validate_file_list("Music", ["track_one.mp3", "track_two.mp3"], "mp3")
        assert [p.name for p in out] == ["track_one.mp3", "track_two.mp3"]
        assert all(p.is_absolute() for p in out)

    def test_drops_missing_files(self) -> None:
        out = validate_file_list("Music", ["track_one.mp3", "nope.mp3"], "mp3")
        assert [p.name for p in out] == ["track_one.mp3"]

    def test_extension_filter_is_applied_case_insensitively(self) -> None:
        assert validate_file_list("Music", ["wrong_ext.ogg"], "mp3") == []
        assert len(validate_file_list("Music", ["wrong_ext.ogg"], "OGG")) == 0
        assert len(validate_file_list("Music", ["wrong_ext.ogg"], "ogg")) == 1

    def test_no_extension_filter_accepts_anything_present(self) -> None:
        assert len(validate_file_list("Music", ["wrong_ext.ogg"], None)) == 1

    def test_missing_directory_yields_an_empty_list_not_an_error(self) -> None:
        assert validate_file_list("NoSuchDirectory", ["a.mp3"], "mp3") == []


# --------------------------------------------------------------------------- #
# image helpers
# --------------------------------------------------------------------------- #
class TestImageHelpers:
    def test_image_to_retro_preserves_size(self) -> None:
        source = pygame.Surface((24, 10), pygame.SRCALPHA)
        source.fill((10, 200, 40, 255))
        assert image_to_retro(source).get_size() == (24, 10)

    def test_image_to_retro_collapses_hue_towards_the_retro_palette(self) -> None:
        source = pygame.Surface((4, 4), pygame.SRCALPHA)
        source.fill((0, 255, 0, 255))
        r, g, b, _ = image_to_retro(source).get_at((0, 0))
        # Greyscale then multiplied by RETRO_WHITE, so the channels land in the
        # same proportion as the palette rather than staying pure green.
        assert r >= g >= b

    def test_flip_returns_new_surfaces_in_order(self) -> None:
        sprites = []
        for shade in (10, 200):
            surface = pygame.Surface((4, 2), pygame.SRCALPHA)
            surface.fill((shade, 0, 0, 255))
            surface.set_at((0, 0), (0, 0, 255, 255))
            sprites.append(surface)

        flipped = flip(sprites)
        assert len(flipped) == 2
        assert flipped[0] is not sprites[0]
        assert flipped[0].get_at((3, 0)) == pygame.Color(0, 0, 255, 255)

    def test_make_image_from_text_is_at_least_the_requested_size(self) -> None:
        image = make_image_from_text(256, 128, "HEADER", ["one", "two"])
        assert image.get_width() >= 256
        assert image.get_height() >= 128

    def test_make_image_from_text_grows_for_long_bodies(self) -> None:
        short = make_image_from_text(10, 10, "H", ["a"])
        tall  = make_image_from_text(10, 10, "H", ["a"] * 12)
        assert tall.get_height() > short.get_height()


# --------------------------------------------------------------------------- #
# asset loaders
# --------------------------------------------------------------------------- #
class TestLoadImages:
    def test_keys_are_uppercased_file_stems(self) -> None:
        images = load_images("Icons", "Timer")
        assert set("0123456789") <= set(images)
        assert "COLON" in images and "DECIMAL" in images

    def test_single_level_directories_work_too(self) -> None:
        images = load_images("Background", None)
        assert "BLUE" in images

    def test_missing_directory_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_images("NotThere", None)

    def test_directory_without_pngs_is_fatal(self, assets_root: Path) -> None:
        (assets_root / "EmptyDir").mkdir(exist_ok = True)
        with pytest.raises(HandledError):
            load_images("EmptyDir", None)


class TestLoadSpriteSheets:
    def test_splits_a_sheet_into_square_frames_and_doubles_them(
            self, sprite_master: dict) -> None:
        sheets = load_sprite_sheets("Sprites", "TestAgent", sprite_master, direction = True)
        frames = sheets["IDLE_RIGHT"]
        assert len(frames) == FRAMES
        assert frames[0].get_size() == (FRAME * 2, FRAME * 2)

    def test_direction_true_produces_a_left_and_right_key_per_sheet(
            self, sprite_master: dict) -> None:
        sheets = load_sprite_sheets("Sprites", "TestAgent", sprite_master, direction = True)
        for state in MOVEMENT_STATES:
            assert f"{state}_RIGHT" in sheets
            assert f"{state}_LEFT" in sheets

    def test_direction_false_leaves_the_bare_stem(self, sprite_master: dict) -> None:
        sheets = load_sprite_sheets("Sprites", "TestAnim", sprite_master, direction = False)
        assert "ANIMATE" in sheets
        assert "ANIMATE_RIGHT" not in sheets

    def test_result_is_cached_per_directory(self, sprite_master: dict) -> None:
        first  = load_sprite_sheets("Sprites", "TestAgent", sprite_master, direction = True)
        second = load_sprite_sheets("Sprites", "TestAgent", sprite_master, direction = True)
        assert first is second
        assert list(sprite_master) == ["TestAgent"]

    def test_the_cache_ignores_a_later_retro_request(self, sprite_master: dict) -> None:
        """Documented behaviour, and a sharp edge worth knowing about.

        The cache key is the directory name alone, so whichever of the retro/normal
        variants is requested *first* is the one every later caller gets.  Player
        sidesteps this by keeping separate directories for its two sprite sets.
        """
        normal = load_sprite_sheets("Sprites", "TestAgent", sprite_master, retro = False)
        retro  = load_sprite_sheets("Sprites", "TestAgent", sprite_master, retro = True)
        assert retro is normal

    def test_falls_back_to_a_random_longer_directory_with_the_same_prefix(
            self, sprite_master: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Helpers.random, "randint", lambda a, b: a)
        sheets = load_sprite_sheets("Sprites", "PrefixMatch", sprite_master, direction = True)
        assert "IDLE_RIGHT" in sheets
        # cached under the resolved directory, not the requested prefix
        assert "PrefixMatch" not in sprite_master

    def test_missing_directory_with_no_prefix_match_is_fatal(self, sprite_master: dict) -> None:
        with pytest.raises(HandledError):
            load_sprite_sheets("Sprites", "DefinitelyNotASprite", sprite_master)

    def test_retro_variant_differs_from_the_normal_one(self, sprite_master: dict) -> None:
        plain = load_sprite_sheets("Sprites", "TestAgent", {}, direction = True)
        retro = load_sprite_sheets("Sprites", "TestAgent", {}, direction = True, retro = True)
        assert plain["IDLE_RIGHT"][0].get_at((1, 1)) != retro["IDLE_RIGHT"][0].get_at((1, 1))


class TestPickerAndLevelImages:
    def test_load_picker_sprites_pairs_normal_and_retro_entries(self) -> None:
        images, values = load_picker_sprites("Sprites")
        assert len(images["normal"]) == len(values)
        assert len(images["retro"]) == len(images["normal"])

    def test_picker_values_are_the_trailing_character_of_the_folder(self) -> None:
        _, values = load_picker_sprites("Sprites")
        assert set(values) == {"1", "2"}

    def test_load_level_images_uppercases_stems_and_sorts(self) -> None:
        images, values = load_level_images("LevelImages")
        assert values == sorted(values)
        assert "TESTLEVEL" in values
        assert len(images) == len(values)

    def test_load_level_images_on_a_missing_folder_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_level_images("NoSuchFolder")


class TestDataLoaders:
    def test_load_json_dict_parses(self) -> None:
        data = load_json_dict("ReferenceDicts/GameObjects", f"{LEVEL_NAME.lower()}.agd")
        assert data["B"]["type"] == "Block"

    def test_load_json_dict_missing_file_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_json_dict("ReferenceDicts/GameObjects", "nope.agd")

    def test_load_object_dicts_keys_on_uppercased_stem(self) -> None:
        dicts = load_object_dicts("ReferenceDicts/GameObjects")
        assert LEVEL_NAME in dicts
        assert dicts[LEVEL_NAME]["P"]["type"] == "Player"

    def test_load_object_dicts_ignores_non_agd_files(self, assets_root: Path) -> None:
        folder = assets_root / "ReferenceDicts" / "GameObjects"
        (folder / "README.txt").write_text("ignore me")
        try:
            assert "README" not in load_object_dicts("ReferenceDicts/GameObjects")
        finally:
            (folder / "README.txt").unlink()

    def test_load_levels_returns_a_row_list_per_level(self) -> None:
        levels = load_levels("Levels")
        assert LEVEL_NAME in levels
        rows = levels[LEVEL_NAME]
        assert all(len(row) == len(rows[0]) for row in rows)

    def test_load_levels_on_a_missing_folder_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_levels("NoSuchFolder")


class TestLoadAudios:
    def test_keys_are_uppercased_sub_directory_names(self) -> None:
        audios = load_audios("blocks")
        assert "DOOR" in audios and "SMASH_BOX" in audios

    def test_every_entry_is_a_list_of_sounds(self) -> None:
        audios = load_audios("player")
        assert all(isinstance(s, pygame.mixer.Sound) for s in audios["RUN"])
        assert len(audios["RUN"]) == 2

    def test_the_same_file_yields_the_same_shared_sound_object(self) -> None:
        """The de-duplication pass in load_audios is what keeps memory flat."""
        audios = load_audios("player")
        first  = load_audios("player")
        # Within one call, identical paths collapse onto one Sound; across calls the
        # cache is rebuilt, so only the within-call guarantee is asserted.
        assert len({id(s) for s in audios["RUN"]}) == len(audios["RUN"])
        assert set(first) == set(audios)

    def test_missing_directory_is_fatal_unless_suppressed(self) -> None:
        with pytest.raises(HandledError):
            load_audios("no_such_group")
        assert load_audios("no_such_group", suppress_error = True) is None


class TestLoadTextFromFile:
    def test_strips_newlines(self) -> None:
        assert load_text_from_file("message.txt") == ["First line.", "Second line."]

    def test_missing_file_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_text_from_file("nope.txt")

    def test_empty_file_yields_an_empty_list(self) -> None:
        assert load_text_from_file("empty.txt") == []


# --------------------------------------------------------------------------- #
# set_sound_source
# --------------------------------------------------------------------------- #
class _FakeChannel:
    def __init__(self) -> None:
        self.volumes: list[tuple[float, float]] = []

    def set_volume(self, left: float, right: float) -> None:
        self.volumes.append((left, right))


class TestSetSoundSource:
    @pytest.fixture
    def channel(self) -> _FakeChannel:
        return _FakeChannel()

    def test_source_to_the_right_is_louder_on_the_right(self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(300, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        left, right = channel.volumes[-1]
        assert right > left

    def test_source_to_the_left_is_louder_on_the_left(self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(0, 0, 10, 10), pygame.Rect(300, 0, 10, 10), 1.0, channel)
        left, right = channel.volumes[-1]
        assert left > right

    def test_beyond_a_kilopixel_horizontally_the_sound_is_silent(
            self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(2000, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        assert channel.volumes[-1] == (0, 0)

    def test_vertical_distance_attenuates_both_channels(self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(300, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        near = channel.volumes[-1]
        set_sound_source(pygame.Rect(300, 500, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        far = channel.volumes[-1]
        assert far[1] < near[1]

    def test_the_volume_modifier_scales_the_result(self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(300, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        full = channel.volumes[-1]
        set_sound_source(pygame.Rect(300, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 0.5, channel)
        half = channel.volumes[-1]
        assert half[1] == pytest.approx(full[1] * 0.5)

    def test_a_co_located_source_is_still_attenuated_by_height(
            self, channel: _FakeChannel) -> None:
        """Directly above the player means no panning, but not full volume.

        The dx == 0 branch used to skip the height attenuation entirely, so a source
        was loud or quiet purely on whether its x matched exactly.
        """
        set_sound_source(pygame.Rect(0, 900, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        left, right = channel.volumes[-1]
        assert left == right
        assert left == pytest.approx(0.1)

    def test_a_source_on_top_of_the_player_plays_at_full_volume(
            self, channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(0, 0, 10, 10), pygame.Rect(0, 0, 10, 10), 1.0, channel)
        assert channel.volumes[-1] == (1.0, 1.0)

    @pytest.mark.parametrize("source, player, modifier", [
        (None,                     pygame.Rect(0, 0, 1, 1), 1.0),
        (pygame.Rect(0, 0, 1, 1),  None,                    1.0),
        (pygame.Rect(0, 0, 1, 1),  pygame.Rect(0, 0, 1, 1), None),
    ])
    def test_missing_arguments_are_a_no_op(self, channel: _FakeChannel,
                                           source, player, modifier) -> None:
        set_sound_source(source, player, modifier, channel)
        assert channel.volumes == []

    def test_a_deliberately_muted_channel_is_set_to_silence(self,
                                                            channel: _FakeChannel) -> None:
        """0.0 is a real volume, not a missing argument.

        The guard used to test truthiness, so muting a channel left it at whatever
        volume it already had.
        """
        set_sound_source(pygame.Rect(0, 0, 1, 1), pygame.Rect(0, 0, 1, 1), 0.0, channel)
        assert channel.volumes[-1] == (0.0, 0.0)

    def test_a_zero_size_rect_is_still_a_position(self,
                                                  channel: _FakeChannel) -> None:
        set_sound_source(pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 1, 1), 1.0, channel)
        assert channel.volumes

    def test_a_missing_channel_is_a_no_op(self) -> None:
        set_sound_source(pygame.Rect(0, 0, 1, 1), pygame.Rect(0, 0, 1, 1), 1.0, None)


# --------------------------------------------------------------------------- #
# process_text
# --------------------------------------------------------------------------- #
class TestProcessText:
    def test_plain_text_passes_through(self, controller) -> None:
        assert process_text("Hello.", controller) == ("Hello.", False, False)

    def test_bold_and_italic_markers_are_stripped_and_reported(self, controller) -> None:
        line, bold, italic = process_text("<b><i>Loud.", controller)
        assert (line, bold, italic) == ("Loud.", True, True)

    def test_a_single_bound_key_is_substituted_by_name(self, controller) -> None:
        controller.set_keyboard_layout("ARROW_MOVE")
        expected = pygame.key.name(pygame.K_UP).title()
        assert process_text("Press <key=keys_jump>.", controller)[0] == f"Press {expected}."

    def test_two_bound_keys_are_joined_with_or(self, controller) -> None:
        controller.set_keyboard_layout("ARROW_MOVE")
        line = process_text("Use <key=keys_bullet_time>.", controller)[0]
        assert " or " in line
        assert "," not in line

    def test_three_or_more_keys_use_an_oxford_list(self, controller) -> None:
        controller.set_keyboard_layout("ARROW_MOVE")
        line = process_text("Dash with <key=keys_teleport_dash>.", controller)[0]
        assert ", " in line and ", or " in line

    def test_the_first_unknown_key_reports_key_not_found(self, controller) -> None:
        assert process_text("<key=keys_nope>", controller)[0] == "KEY NOT FOUND"

    def test_every_unknown_key_reports_key_not_found(self, controller) -> None:
        """A second unresolved tag on a line used to vanish instead of announcing itself."""
        line = process_text("<key=keys_jump> then <key=keys_nope>", controller)[0]
        assert line.endswith(" then KEY NOT FOUND")

    def test_falls_back_to_the_gamepad_layout_when_the_keyboard_lacks_the_action(
            self, controller) -> None:
        """Gamepad layout values are bare ints, not lists -- this used to raise."""
        controller.set_keyboard_layout("ARROW_MOVE")
        controller.set_gamepad_layout("XBOX")
        # "button_up" exists only on the gamepad side.
        assert process_text("<key=button_up>", controller)[0] == "D-Pad Up"

    def test_a_gamepad_button_is_never_named_as_a_key_code(self, controller) -> None:
        """pygame.key.name() on a button index produces nonsense, so it is not used."""
        controller.set_gamepad_layout("XBOX")
        line = process_text("<key=button_jump>", controller)[0]
        assert line == "A"
        assert line != pygame.key.name(int(pygame.CONTROLLER_BUTTON_A)).title()

    def test_an_unmapped_button_index_still_renders_something_readable(
            self, controller, monkeypatch: pytest.MonkeyPatch) -> None:
        controller.set_gamepad_layout("XBOX")
        monkeypatch.delitem(Helpers.GAMEPAD_BUTTON_NAMES["XBOX"], pygame.CONTROLLER_BUTTON_A)
        assert process_text("<key=button_jump>", controller)[0].startswith("Button ")

    def test_the_prompt_follows_the_pad_in_the_players_hands(self, controller) -> None:
        """The same binding, named the way it is printed on each controller."""
        expected = {"XBOX": "A", "PS4": "Cross", "PS5": "Cross", "SWITCH PRO": "A"}
        for layout, label in expected.items():
            controller.set_gamepad_layout(layout)
            assert process_text("<key=button_jump>", controller)[0] == label

    def test_repeated_tags_are_all_replaced(self, controller) -> None:
        line = process_text("<key=keys_jump> and <key=keys_jump>", controller)[0]
        assert "<key=" not in line


# --------------------------------------------------------------------------- #
# gamepad button labels
# --------------------------------------------------------------------------- #
class TestGamepadButtonNames:
    """Prompts have to read the way the button is printed on the pad in use.

    The SDL constants are positional on an Xbox pad, so every other family is a
    relabel of the same indices rather than a different set of them.
    """

    def _bound_buttons(self, controller, layout: str) -> set[int]:
        """The button indices a layout actually binds (its axes and Nones excluded)."""
        return {value for action, value in controller.GAMEPAD_LAYOUTS[layout].items()
                if action.startswith("button_") and value is not None}

    def test_every_layout_that_binds_buttons_has_a_name_table(self, controller) -> None:
        binding = {name for name in controller.GAMEPAD_LAYOUTS
                   if self._bound_buttons(controller, name)}
        assert binding <= set(GAMEPAD_BUTTON_NAMES)

    def test_every_bound_button_has_a_label_in_its_own_layout(self, controller) -> None:
        """A new binding with no label would silently print "Button 7" in-game."""
        missing = {
            (layout, button)
            for layout in GAMEPAD_BUTTON_NAMES
            for button in self._bound_buttons(controller, layout)
            if button not in GAMEPAD_BUTTON_NAMES[layout]
        }
        assert missing == set()

    def test_labels_within_a_layout_are_distinct(self) -> None:
        for layout, names in GAMEPAD_BUTTON_NAMES.items():
            assert len(set(names.values())) == len(names), f"duplicate label in {layout}"

    def test_no_label_is_blank(self) -> None:
        for names in GAMEPAD_BUTTON_NAMES.values():
            assert all(label.strip() for label in names.values())

    @pytest.mark.parametrize(("layout", "expected"), [
        ("XBOX",       {pygame.CONTROLLER_BUTTON_A: "A",
                        pygame.CONTROLLER_BUTTON_B: "B",
                        pygame.CONTROLLER_BUTTON_X: "X",
                        pygame.CONTROLLER_BUTTON_Y: "Y"}),
        ("PS4",        {pygame.CONTROLLER_BUTTON_A: "Cross",
                        pygame.CONTROLLER_BUTTON_B: "Circle",
                        pygame.CONTROLLER_BUTTON_X: "Square",
                        pygame.CONTROLLER_BUTTON_Y: "Triangle"}),
        ("PS5",        {pygame.CONTROLLER_BUTTON_A: "Cross",
                        pygame.CONTROLLER_BUTTON_B: "Circle",
                        pygame.CONTROLLER_BUTTON_X: "Square",
                        pygame.CONTROLLER_BUTTON_Y: "Triangle"}),
        # SDL_HINT_GAMECONTROLLER_USE_BUTTON_LABELS defaults to "1", so a Switch pad
        # reports its face buttons by their printed label, not by position -- which
        # means CONTROLLER_BUTTON_A really is the button marked A and no swap applies.
        ("SWITCH PRO", {pygame.CONTROLLER_BUTTON_A: "A",
                        pygame.CONTROLLER_BUTTON_B: "B",
                        pygame.CONTROLLER_BUTTON_X: "X",
                        pygame.CONTROLLER_BUTTON_Y: "Y"}),
    ])
    def test_face_buttons_carry_the_families_own_names(self, layout, expected) -> None:
        for button, label in expected.items():
            assert gamepad_button_name(button, layout) == label

    @pytest.mark.parametrize(("layout", "expected"), [
        ("XBOX",       ("LB", "RB")),
        ("PS4",        ("L1", "R1")),
        ("PS5",        ("L1", "R1")),
        ("SWITCH PRO", ("L",  "R")),
    ])
    def test_shoulders_carry_the_families_own_names(self, layout, expected) -> None:
        assert (gamepad_button_name(pygame.CONTROLLER_BUTTON_LEFTSHOULDER, layout),
                gamepad_button_name(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, layout)) == expected

    @pytest.mark.parametrize(("layout", "back", "start"), [
        ("XBOX",       "View",   "Menu"),
        ("PS4",        "Share",  "Options"),
        ("PS5",        "Create", "Options"),
        ("SWITCH PRO", "Minus",  "Plus"),
    ])
    def test_system_buttons_carry_the_families_own_names(self, layout, back, start) -> None:
        """PS4's Share became PS5's Create -- the one place the two Sony pads differ."""
        assert gamepad_button_name(pygame.CONTROLLER_BUTTON_BACK, layout) == back
        assert gamepad_button_name(pygame.CONTROLLER_BUTTON_START, layout) == start

    def test_the_d_pad_reads_the_same_everywhere(self) -> None:
        for layout in GAMEPAD_BUTTON_NAMES:
            assert gamepad_button_name(pygame.CONTROLLER_BUTTON_DPAD_UP, layout) == "D-Pad Up"

    def test_an_unknown_layout_falls_back_rather_than_raising(self) -> None:
        """An unrecognised pad is set up with the XBOX bindings, so it gets XBOX labels."""
        fallback = GAMEPAD_BUTTON_NAMES[FALLBACK_GAMEPAD_LAYOUT]
        for layout in (None, "NONE", "STEAM DECK", ""):
            assert gamepad_button_name(pygame.CONTROLLER_BUTTON_A, layout) == \
                fallback[pygame.CONTROLLER_BUTTON_A]

    def test_an_unmapped_index_renders_as_its_number(self) -> None:
        assert gamepad_button_name(pygame.CONTROLLER_BUTTON_MAX, "XBOX") == \
            f"Button {int(pygame.CONTROLLER_BUTTON_MAX)}"

    def test_describe_binding_uses_the_active_layout(self, controller) -> None:
        controller.set_gamepad_layout("PS5")
        assert describe_binding("button_bullet_time", controller) == "Triangle"
        controller.set_gamepad_layout("XBOX")
        assert describe_binding("button_bullet_time", controller) == "Y"

    def test_switching_pads_mid_session_changes_the_prompt(self, controller) -> None:
        """A player unplugging an Xbox pad for a DualSense should see the prompt follow."""
        controller.set_gamepad_layout("XBOX")
        before = describe_binding("button_shrink", controller)
        controller.set_gamepad_layout("PS4")
        assert describe_binding("button_shrink", controller) != before


# --------------------------------------------------------------------------- #
# glitch
# --------------------------------------------------------------------------- #
class TestGlitch:
    @pytest.fixture
    def screen(self) -> pygame.Surface:
        surface = pygame.Surface((400, 300), pygame.SRCALPHA)
        surface.fill((30, 60, 90, 255))
        return surface

    def test_returns_surface_position_pairs(self, screen: pygame.Surface) -> None:
        random.seed(7)
        for fragment, position in glitch(1.0, screen):
            assert isinstance(fragment, pygame.Surface)
            assert len(position) == 2

    def test_zero_odds_produces_nothing(self, screen: pygame.Surface) -> None:
        assert glitch(0.0, screen) == []

    def test_fragments_stay_inside_the_screen(self, screen: pygame.Surface) -> None:
        random.seed(11)
        for fragment, (x, y) in glitch(2.0, screen):
            assert 0 <= x <= screen.get_width() - fragment.get_width()
            assert 0 <= y <= screen.get_height() - fragment.get_height()

    def test_is_deterministic_for_a_fixed_seed(self, screen: pygame.Surface) -> None:
        random.seed(3)
        first = [(f.get_size(), p) for f, p in glitch(1.5, screen)]
        random.seed(3)
        second = [(f.get_size(), p) for f, p in glitch(1.5, screen)]
        assert first == second

    def test_does_not_mutate_the_source_surface(self, screen: pygame.Surface) -> None:
        before = screen.get_at((0, 0))
        random.seed(5)
        glitch(2.0, screen)
        assert screen.get_at((0, 0)) == before


# --------------------------------------------------------------------------- #
# paths
# --------------------------------------------------------------------------- #
class TestLoadPath:
    def test_none_or_empty_input_yields_none(self) -> None:
        assert load_path(None, 0, 0, 96) is None
        assert load_path([], 0, 0, 96) is None

    def test_offsets_are_relative_to_the_entity_tile(self) -> None:
        path = load_path(["12"], i = 3, j = 4, block_size = 96)
        assert (path[0].x, path[0].y) == ((1 + 4) * 96, (2 + 3) * 96)

    def test_a_repeated_point_flags_a_wait_rather_than_adding_a_node(self) -> None:
        path = load_path(["00", "20", "20"], 0, 0, 96)
        assert len(path) == 2
        assert path[-1].wait is True
        assert path[0].wait is False

    def test_points_start_without_a_wait_flag(self) -> None:
        assert load_path(["00", "10"], 0, 0, 96)[0].wait is False

    def test_a_non_numeric_point_is_fatal(self) -> None:
        with pytest.raises(HandledError):
            load_path(["ab"], 0, 0, 96)

    def test_accepts_a_tuple_as_well_as_a_list(self) -> None:
        assert len(load_path(("00", "11"), 0, 0, 96)) == 2


def test_path_point_holds_coordinates_and_a_wait_flag() -> None:
    point = PathPoint(4, 5)
    assert (point.x, point.y, point.wait) == (4, 5, False)


# --------------------------------------------------------------------------- #
# set_property
# --------------------------------------------------------------------------- #
class _PropTarget:
    def __init__(self, name: str) -> None:
        self.name      = name
        self.hp        = 100
        self.speed     = 1.0
        self.abilities = {"can_fly": False}


class _PropLevel:
    def __init__(self, entities: list) -> None:
        self.entities = entities


class _Trigger:
    def __init__(self, entities: list) -> None:
        self.level = _PropLevel(entities)


class TestSetProperty:
    def _trigger(self, *names: str) -> tuple[_Trigger, list[_PropTarget]]:
        targets = [_PropTarget(name) for name in names]
        return _Trigger(targets), targets

    def test_sets_a_single_property_on_a_matching_entity(self) -> None:
        trigger, (guard,) = self._trigger("Guard (0, 0)")
        set_property(trigger, {"target": "Guard", "property": "hp", "value": 42})
        assert guard.hp == 42

    def test_matches_every_entity_sharing_the_prefix(self) -> None:
        trigger, targets = self._trigger("Guard A", "Guard B", "Civilian")
        set_property(trigger, {"target": "Guard", "property": "hp", "value": 1})
        assert [t.hp for t in targets] == [1, 1, 100]

    def test_matching_is_case_insensitive(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "guard", "property": "hp", "value": 7})
        assert guard.hp == 7

    def test_parallel_lists_are_applied_pairwise(self) -> None:
        trigger, (guard, civ) = self._trigger("Guard", "Civilian")
        set_property(trigger, {
            "target":   ["Guard", "Civilian"],
            "property": ["hp", "speed"],
            "value":    [10, 2.5],
        })
        assert (guard.hp, civ.speed) == (10, 2.5)

    def test_mismatched_list_lengths_do_nothing(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": ["Guard", "Other"], "property": ["hp"],
                               "value": [1]})
        assert guard.hp == 100

    @pytest.mark.parametrize("raw, expected", [
        ("true",  True),
        ("TRUE",  True),
        ("False", False),
        ("12",    12),
    ])
    def test_string_values_are_coerced(self, raw: str, expected) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": raw})
        assert guard.speed == expected
        assert isinstance(guard.speed, type(expected))

    def test_decimal_strings_are_coerced(self) -> None:
        """``"12.5".isnumeric()`` is False, so decimals used to be assigned as strings."""
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": "12.5"})
        assert guard.speed == 12.5
        assert isinstance(guard.speed, float)

    def test_negative_number_strings_are_coerced(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": "-3"})
        assert guard.speed == -3
        assert isinstance(guard.speed, int)

    def test_a_non_numeric_string_is_left_alone(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": "fast"})
        assert guard.speed == "fast"

    @pytest.mark.parametrize("raw", [
        "fast", "Slow Patrol", "TESTLEVEL", "Guard A", "north-east",
        "3 blocks", "v1.2", "true-ish", "", " ", "-", "+", ".",
    ])
    def test_string_values_survive_the_numeric_coercion(self, raw: str) -> None:
        """Coercion only fires on values float() accepts; everything else is untouched."""
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": raw})
        assert guard.speed == raw
        assert isinstance(guard.speed, str)

    @pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "Infinity"])
    def test_non_finite_number_words_neither_crash_nor_coerce(self, raw: str) -> None:
        """float() takes all five and int() refuses all five, which used to raise."""
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": raw})
        assert guard.speed == raw
        assert isinstance(guard.speed, str)

    def test_real_numbers_pass_through_untouched(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "speed", "value": 0.25})
        assert guard.speed == 0.25

    def test_a_whole_numbered_string_becomes_an_int_not_a_float(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "hp", "value": "3"})
        assert guard.hp == 3 and isinstance(guard.hp, int)

    def test_can_prefixed_names_fall_through_to_the_abilities_dict(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "can_fly", "value": "true"})
        assert guard.abilities["can_fly"] is True

    def test_an_unknown_ability_is_added_to_the_dict(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "can_swim", "value": True})
        assert guard.abilities["can_swim"] is True

    def test_an_unknown_non_ability_property_is_ignored(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {"target": "Guard", "property": "nonsense", "value": 1})
        assert not hasattr(guard, "nonsense")

    def test_an_empty_specification_is_a_no_op(self) -> None:
        trigger, (guard,) = self._trigger("Guard")
        set_property(trigger, {})
        assert guard.hp == 100


# --------------------------------------------------------------------------- #
# display_text (the real one, driven in its non-blocking configuration)
# --------------------------------------------------------------------------- #
class TestRealDisplayText:
    def test_renders_without_sleeping_when_asked_not_to(self, controller) -> None:
        Helpers.real_display_text("Hello agent.", controller, should_type_text = False,
                                  should_sleep = False)

    def test_empty_output_returns_immediately(self, controller) -> None:
        assert Helpers.real_display_text("", controller, should_sleep = False) is None
        assert Helpers.real_display_text([], controller, should_sleep = False) is None

    def test_accepts_a_bare_string_as_well_as_a_list(self, controller) -> None:
        Helpers.real_display_text(["a", "b"], controller, should_type_text = False,
                                  should_sleep = False)

    def test_retro_framing_draws_without_error(self, controller) -> None:
        Helpers.real_display_text("Retro.", controller, should_type_text = False,
                                  should_sleep = False, retro = True, background = True)


# --------------------------------------------------------------------------- #
# the generated asset fixture itself
# --------------------------------------------------------------------------- #
def test_generated_sprite_states_match_the_real_movement_state_enum() -> None:
    """Guards the hard-coded state list in ``tests/support/assets.py``.

    If a state is added to ``MovementState`` without a matching generated sheet,
    ``Actor.update_sprite`` would KeyError deep inside an unrelated test; fail here
    instead, with a clear message.
    """
    from Actor import MovementState

    assert set(MOVEMENT_STATES) == {state.name for state in MovementState}


def test_generated_object_dict_is_valid_json(assets_root: Path) -> None:
    path = assets_root / "ReferenceDicts" / "GameObjects" / f"{LEVEL_NAME.lower()}.agd"
    assert json.loads(path.read_text())
