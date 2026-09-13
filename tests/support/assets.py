"""Builds a throwaway ``Assets/`` tree so the game modules can be imported and exercised.

The repository does not ship its art, audio or level data, and several modules touch
the asset tree at *import* time (``Objective`` loads the pointer sprite in its class
body) or at *construction* time (``Actor`` loads sprite sheets, ``Block`` slices the
terrain sheet, ``HUD`` loads every icon).  Rather than depend on a developer's local
copy -- which would make results machine-dependent and break whenever an asset is
renamed -- the test session generates a complete, minimal tree in a temp directory
and points ``Helpers.ASSETS_FOLDER`` at it.

Everything is generated with pygame and the stdlib ``wave`` module, so there are no
binary fixtures in the repo.  The layout mirrors what the code expects:

    Assets/
      Background/          Blue.png (the hard-coded fallback), Wide.png, Test.png
      Cinematics/          slide.png, clip.mp4
      Foreground/          Wide.png, border_retro.png (the HUD's retro corner)
      Icons/               jump.png, ... , save.png, icon_small.png
      Icons/Pointer/       pointer.png, pointer_retro.png
      Icons/Timer/         0-9.png, colon.png, decimal.png
      LevelImages/         *.png  (level picker)
      Levels/              *.agl  (CSV grid)
      Menu/Buttons/        button_normal.png, half_button_normal.png, ...
      Menu/Arrows/         arrow_white.png
      Menu/Keyboards/      *.png
      Menu/Controllers/    *.png
      Misc/                (output dir for Level.gen_image)
      Music/               *.mp3 placeholders
      Projectiles/<name>/  <name>.png
      ReferenceDicts/GameObjects/  *.agd (JSON)
      SoundEffects/<group>/<sound>/*.wav
      SoundEffects/triggers/*.wav
      Sprites/<name>/      one sheet per MovementState, plus picker.png for players
      Text/                *.txt

Sprite sheets are ``FRAME`` pixels tall and ``FRAME * frames`` wide, because
``Helpers.load_sprite_sheets`` derives the frame size from the sheet height and then
runs every frame through ``scale2x``.  ``FRAME`` is 32 so that a loaded actor sprite
ends up 64x64 -- the same as ``Actor.SIZE``.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pygame

#: source frame size; doubled by ``scale2x`` inside ``load_sprite_sheets``
FRAME: int = 32

#: how many frames each generated animation sheet holds.  Must be >= 3: a
#: ``FallingHazard`` reserves the last two frames for "falling" and "landed" and
#: animates over ``len(sprites) - 2``.
FRAMES: int = 4

#: the level built by :func:`build` and used by the integration tests
LEVEL_NAME: str = "TESTLEVEL"

#: every ``MovementState`` name, which is what ``Actor`` looks up as
#: ``f"{state}_{facing}"``.  Cross-checked against the real enum by
#: ``tests/test_assets_fixture.py`` so this list cannot silently drift.
MOVEMENT_STATES: tuple[str, ...] = (
    "IDLE", "RUN", "CROUCH", "JUMP", "DOUBLE_JUMP", "WALL_JUMP", "FALL", "HIT",
    "TELEPORT", "RESIZE", "SHOOT", "IDLE_ATTACK", "CROUCH_ATTACK", "RUN_ATTACK",
    "FALL_ATTACK", "JUMP_ATTACK", "DOUBLE_JUMP_ATTACK", "WIND_UP", "ATTACK_ANIM",
    "WIND_DOWN", "IDLE_CROUCH", "IDLE_CROUCH_ATTACK", "DEAD",
)

#: actor sprite sets the tests construct entities with
ACTOR_SPRITES: tuple[str, ...] = (
    "UnarmedAgent",   # Actor's built-in default
    "TestAgent",
    "Player1", "Player2",
    "RetroPlayer1", "RetroPlayer2",
    "PrefixMatchA", "PrefixMatchB",   # exercise load_sprite_sheets' prefix fallback
)

#: single-animation sprite sets used by hazards and objectives
ANIMATED_SPRITES: tuple[str, ...] = ("TestAnim",)

#: projectile sprite sets -- the directory name and the file stem must match,
#: because ``Actor`` indexes the result by ``proj_sprite.upper()``
PROJECTILE_SPRITES: tuple[str, ...] = ("Bullet", "TestProj")

#: ``load_audios(group)`` walks ``SoundEffects/<group>/`` and keys the result by
#: sub-directory name, uppercased
AUDIO_GROUPS: dict[str, tuple[str, ...]] = {
    "player": (
        "RUN", "JUMP", "DOUBLE_JUMP", "CROUCH", "HIT", "RESIZE", "TELEPORT",
        "ATTACK_MELEE", "ATTACK_RANGE", "BULLET_TIME", "DEAD",
    ),
    "enemies": ("RUN", "JUMP", "HIT", "ATTACK_MELEE", "ATTACK_RANGE", "DEAD"),
    "blocks": (
        "objective", "door", "door_locked", "smash_box", "block_drop", "block_land",
    ),
    "messages": ("INTRO", "OUTRO"),
}

#: text files ``load_text_from_file`` is pointed at
TEXT_FILES: dict[str, list[str]] = {
    "message.txt":  ["First line.", "Second line."],
    "bark.txt":     ["Halt!"],
    "markup.txt":   ["<b>Bold line.", "<i>Italic line.", "Press <key=keys_jump> to jump."],
    "empty.txt":    [],
}


# --------------------------------------------------------------------------- #
# primitives
# --------------------------------------------------------------------------- #
def _solid(width: int, height: int, colour: tuple[int, int, int, int]) -> pygame.Surface:
    """An opaque surface.  Opaque matters: ``pygame.mask.from_surface`` keys on alpha."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill(colour)
    return surface


def _save(surface: pygame.Surface, path: Path) -> None:
    path.parent.mkdir(parents = True, exist_ok = True)
    pygame.image.save(surface, str(path))


def _sheet(frames: int = FRAMES) -> pygame.Surface:
    """A horizontal strip of ``frames`` square cells, each a slightly different colour.

    Distinct colours mean a test can tell one animation frame from another by
    sampling a pixel, without depending on exact art.
    """
    sheet = pygame.Surface((FRAME * frames, FRAME), pygame.SRCALPHA)
    for i in range(frames):
        shade = 40 + (i * 50) % 200
        sheet.fill((shade, 90, 160, 255), pygame.Rect(i * FRAME, 0, FRAME, FRAME))
    return sheet


def _wav(path: Path, milliseconds: int = 20) -> None:
    """A valid, silent, 8-bit mono WAV that ``pygame.mixer.Sound`` will accept."""
    path.parent.mkdir(parents = True, exist_ok = True)
    rate   = 8000
    frames = max(1, (rate * milliseconds) // 1000)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(1)
        handle.setframerate(rate)
        handle.writeframes(b"\x80" * frames)


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #
def _build_sprites(root: Path) -> None:
    for name in ACTOR_SPRITES:
        folder = root / "Sprites" / name
        for state in MOVEMENT_STATES:
            _save(_sheet(), folder / f"{state}.png")
        if name.casefold().startswith(("player", "retroplayer")):
            _save(_solid(16, 16, (200, 120, 40, 255)), folder / "picker.png")

    for name in ANIMATED_SPRITES:
        folder = root / "Sprites" / name
        _save(_sheet(), folder / "ANIMATE.png")
        _save(_sheet(), folder / "ANIMATE_RETRO.png")

    for name in PROJECTILE_SPRITES:
        _save(_sheet(frames = 1), root / "Projectiles" / name / f"{name}.png")


def _build_terrain(root: Path) -> None:
    # Terrain.png is sliced by (coord_x, coord_y, width // 2, height // 2); 1024 is
    # comfortably larger than any coordinate the test object dicts use.
    _save(_solid(1024, 1024, (120, 120, 120, 255)), root / "Terrain" / "Terrain.png")
    _save(_solid(1024, 1024, (90, 80, 70, 255)),    root / "Terrain" / "Terrain_retro.png")


def _build_icons(root: Path) -> None:
    for name in ("jump", "double_jump", "block", "teleport", "wall_jump",
                 "resize", "bullet_time", "save"):
        _save(_solid(16, 16, (220, 220, 220, 255)), root / "Icons" / f"{name}.png")

    # Engine sets this as the window icon at import time and treats it as required.
    _save(_solid(32, 32, (200, 40, 40, 255)), root / "Icons" / "icon_small.png")

    _save(_solid(12, 20, (255, 240, 0, 255)), root / "Icons" / "Pointer" / "pointer.png")
    _save(_solid(12, 20, (250, 215, 195, 255)), root / "Icons" / "Pointer" / "pointer_retro.png")

    for digit in range(10):
        _save(_solid(14, 24, (255, 255, 255, 255)), root / "Icons" / "Timer" / f"{digit}.png")
    _save(_solid(8, 24, (255, 255, 255, 255)), root / "Icons" / "Timer" / "colon.png")
    _save(_solid(8, 24, (255, 255, 255, 255)), root / "Icons" / "Timer" / "decimal.png")


def _build_menu_images(root: Path) -> None:
    # Menu/Selector look these up by uppercased stem and halve them on load.
    for name, size, colour in (
        ("button_normal",         (512, 96), (60, 60, 90, 255)),
        ("button_mouseover",      (512, 96), (90, 90, 140, 255)),
        ("half_button_normal",    (256, 96), (60, 60, 90, 255)),
        ("half_button_mouseover", (256, 96), (90, 90, 140, 255)),
    ):
        _save(_solid(size[0], size[1], colour), root / "Menu" / "Buttons" / f"{name}.png")
    _save(_solid(64, 64, (255, 255, 255, 255)), root / "Menu" / "Arrows" / "arrow_white.png")

    for name in ("arrow_move", "wasd_move", "numpad_move", "alt_numpad_move"):
        _save(_solid(64, 32, (30, 30, 60, 255)), root / "Menu" / "Keyboards" / f"{name}.png")
    for name in ("xbox", "playstation", "nintendo"):
        _save(_solid(64, 32, (60, 30, 30, 255)), root / "Menu" / "Controllers" / f"{name}.png")


def _build_backgrounds(root: Path) -> None:
    # "Blue.png" is the hard-coded fallback in Camera.__get_background__.
    #
    # Camera.draw takes a subsurface of the background when the level needs only one
    # tile of it, and always takes one of the foreground -- so both of those images
    # have to be at least as large as the window.  "Test.png" is deliberately small
    # so the multi-tile branch gets exercised too.
    _save(_solid(1920, 1080, (20, 40, 90, 255)), root / "Background" / "Blue.png")
    _save(_solid(1920, 1080, (25, 25, 60, 255)), root / "Background" / "Wide.png")
    _save(_solid(320, 240, (40, 60, 20, 255)),   root / "Background" / "Test.png")
    _save(_solid(1920, 1080, (10, 10, 10, 60)),  root / "Foreground" / "Wide.png")
    # HUD.__make_border__ loads this corner piece unconditionally when it builds the
    # retro frame, and treats a missing file as fatal.
    _save(_solid(48, 48, (250, 215, 195, 255)), root / "Foreground" / "border_retro.png")


def _build_level_images(root: Path) -> None:
    for name in ("testlevel", "otherlevel"):
        _save(_solid(48, 32, (100, 100, 100, 255)), root / "LevelImages" / f"{name}.png")


def _build_audio(root: Path) -> None:
    for group, sounds in AUDIO_GROUPS.items():
        for sound in sounds:
            _wav(root / "SoundEffects" / group / sound / f"{sound.lower()}_a.wav")
            _wav(root / "SoundEffects" / group / sound / f"{sound.lower()}_b.wav")

    # SoundTrigger reads loose files straight out of SoundEffects/triggers/.
    _wav(root / "SoundEffects" / "triggers" / "beep.wav")
    (root / "SoundEffects" / "triggers" / "notes.txt").write_text("not audio\n")


def _build_music(root: Path) -> None:
    music = root / "Music"
    music.mkdir(parents = True, exist_ok = True)
    # validate_file_list only checks existence + suffix, so placeholders are enough.
    (music / "track_one.mp3").write_bytes(b"\x00")
    (music / "track_two.mp3").write_bytes(b"\x00")
    (music / "wrong_ext.ogg").write_bytes(b"\x00")


def _build_text(root: Path) -> None:
    folder = root / "Text"
    folder.mkdir(parents = True, exist_ok = True)
    for name, lines in TEXT_FILES.items():
        (folder / name).write_text("\n".join(lines) + ("\n" if lines else ""))


def _build_cinematics(root: Path) -> None:
    _save(_solid(320, 180, (200, 200, 200, 255)), root / "Cinematics" / "slide.png")
    (root / "Cinematics" / "clip.mp4").write_bytes(b"\x00")


# --------------------------------------------------------------------------- #
# level data
# --------------------------------------------------------------------------- #
#: object-dict entries for the generated level.  Keys are the tokens used in the
#: .agl grid.  ``build_level`` reads ``type``/``data`` from each entry, and reads
#: ``is_blocking`` from the *entry* (not ``data``) when deciding whether a tile
#: stacks -- hence the duplication on "B".
OBJECT_DICT: dict[str, dict] = {
    "P": {"type": "Player", "data": {"face_left": False}},
    "B": {
        "type": "Block",
        "is_blocking": True,
        "data": {"coord_x": 0, "coord_y": 0, "name": "Ground"},
    },
    "X": {
        "type": "BreakableBlock",
        "data": {"coord_x": 0, "coord_y": 0, "coord_x2": 48, "coord_y2": 0,
                 "name": "Crate"},
    },
    "M": {
        "type": "MovingBlock",
        "data": {"coord_x": 0, "coord_y": 0, "speed": 120, "path": ["00", "20"],
                 "name": "Lift"},
    },
    "V": {
        "type": "MovableBlock",
        "data": {"coord_x": 0, "coord_y": 0, "name": "Pushable"},
    },
    "D": {
        "type": "Door",
        "data": {"speed": 200, "direction": -1, "coord_x": 0, "coord_y": 0,
                 "name": "Gate"},
    },
    "H": {
        "type": "Hazard",
        "data": {"sprite": "TestAnim", "coord_x": 0, "coord_y": 0, "hit_sides": "udlr",
                 "name": "Spikes"},
    },
    "F": {
        "type": "FallingHazard",
        "data": {"sprite": "TestAnim", "coord_x": 0, "coord_y": 0, "drop_x": 1,
                 "drop_y": 3, "fire_once": False, "name": "Crusher"},
    },
    "E": {
        "type": "Enemy",
        "data": {"path": None, "hp": 100, "sprite": "TestAgent", "can_shoot": False,
                 "bark": "bark.txt", "name": "Guard"},
    },
    "G": {
        "type": "Enemy",
        "data": {"path": ["00", "30"], "hp": 100, "sprite": "TestAgent",
                 "can_shoot": True, "proj_sprite": "TestProj", "name": "Patroller"},
    },
    "O": {
        "type": "Objective",
        "data": {"sprite": "TestAnim", "is_active": True, "text": "Grab the packet",
                 "sound": "objective", "name": "Packet"},
    },
    "S": {
        "type": "SaveTrigger",
        "data": {"width": 1, "height": 1, "input": None, "name": "Autosave"},
    },
    "C": {
        "type": "ChangeLevelTrigger",
        "data": {"width": 1, "height": 1, "input": "otherlevel", "name": "Exit"},
    },
    "?": {"type": "NotARealType", "data": {}},
}

#: 8 columns x 6 rows.  Row 5 is the floor; the player spawns on it at column 1.
LEVEL_GRID: list[list[str]] = [
    ["",  "",  "",  "",  "",  "",  "",  ""],
    ["",  "",  "",  "F", "",  "",  "",  ""],
    ["",  "",  "",  "",  "",  "",  "",  ""],
    ["",  "P", "",  "O", "",  "E", "",  "C"],
    ["",  "S", "X", "V", "M", "",  "D", ""],
    ["B", "B", "B", "B", "B", "B", "B", "B"],
]

#: metadata dict in the shape ``Level.__init__`` expects
META_DICT: dict[str, dict] = {
    LEVEL_NAME: {
        "name":              "Test Level",
        "block_size":        "96",
        "background":        "Test.png",
        "foreground":        "Test.png",
        "music":             "track_one.mp3 track_two.mp3",
        "retro_music":       "track_two.mp3",
        "target_time":       120,
        "default_objective": "Find the exit",
        "achievements": {
            "target_time":    "ACH_FAST",
            "all_objectives": "ACH_COLLECTOR",
            "no_kills":       "ACH_PACIFIST",
            "all_kills":      "ACH_CLEANER",
            "no_death":       "ACH_SURVIVOR",
            "no_hit":         "ACH_UNTOUCHED",
            "no_seen":        "ACH_SHADOW",
        },
    },
    "RETROLEVEL": {
        "name":       "Retro Level",
        "block_size": "96",
        "retro":      True,
        "background": "Test.png",
    },
}


def _build_levels(root: Path) -> None:
    levels = root / "Levels"
    levels.mkdir(parents = True, exist_ok = True)
    for name in (LEVEL_NAME, "RETROLEVEL"):
        rows = ["\"" + "\",\"".join(row) + "\"" for row in LEVEL_GRID]
        (levels / f"{name.lower()}.agl").write_text("\n".join(rows) + "\n")

    dicts = root / "ReferenceDicts" / "GameObjects"
    dicts.mkdir(parents = True, exist_ok = True)
    for name in (LEVEL_NAME, "RETROLEVEL"):
        (dicts / f"{name.lower()}.agd").write_text(json.dumps(OBJECT_DICT, indent = 2))

    (root / "Misc").mkdir(parents = True, exist_ok = True)


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build(root: Path) -> Path:
    """Generate the whole tree under ``root`` and return ``root``.

    Requires a live pygame display (``convert_alpha`` and ``image.save`` both need
    one), so the caller must have called ``pygame.display.set_mode`` first.
    """
    root.mkdir(parents = True, exist_ok = True)
    _build_sprites(root)
    _build_terrain(root)
    _build_icons(root)
    _build_menu_images(root)
    _build_backgrounds(root)
    _build_level_images(root)
    _build_audio(root)
    _build_music(root)
    _build_text(root)
    _build_cinematics(root)
    _build_levels(root)
    return root
