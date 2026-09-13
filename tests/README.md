# Agent Glitch test suite

```bash
python3.12 -m pip install -r requirements-dev.txt
./run_tests.sh                    # or: python3.12 -m pytest
```

Around 1,130 tests, ~26 seconds, no display, no audio device, no game assets required.
Python 3.12 or newer — `SteamworksConnection.py` nests same-style quotes inside an
f-string, which only parses from 3.12 (PEP 701), so the repo cannot be imported at all
on 3.11.

Useful invocations:

```bash
./run_tests.sh -m "not slow"            # skip the render/playback tests (~8s faster)
./run_tests.sh -m integration           # only the end-to-end level tests
./run_tests.sh -k trigger               # anything matching "trigger"
./run_tests.sh --cov=. --cov-report=term-missing
```

## The problem this harness solves

Agent Glitch is hard to test for three specific reasons, and everything in
`tests/support/` exists to deal with one of them.

**It does real work at import time.** `Helpers` creates `~/.agentglitch` when it is
imported. `Objective` loads `Assets/Icons/Pointer/pointer.png` and calls
`convert_alpha()` in its *class body*, so importing it needs both a live display and a
real asset tree. That means the environment has to be standing before the first game
import, which is why `tests/conftest.py` calls `bootstrap.boot()` at module level and
the game imports below it carry `# noqa: E402`.

**It depends on packages that are not in the repo.** `SimpleVFX` is not committed;
`steamworks` needs the SDK and the platform libraries; `discordrp` and `cv2` reach out
to the world when touched.

**Two `Helpers` functions end or block the process.** `handle_exception` calls
`pygame.quit()`, writes a crash log, opens a Tk dialog and `sys.exit()`s.
`display_text` renders and then spins in `time.sleep` loops for as long as the text
takes to read — and `EntityFactory.build_level` calls it once per grid row.

## What `bootstrap.boot()` does, in order

1. Forces the dummy SDL video and audio drivers, and repoints `HOME` at a throwaway
   directory. **Nothing in the suite can read or overwrite a real save file, profile or
   crash log** — `GAME_DATA_FOLDER` resolves inside the sandbox, and an autouse fixture
   gives every test its own empty copy of it.
2. Installs stand-ins for `SimpleVFX`, `steamworks`, `discordrp` and `cv2`
   (`tests/support/stubs.py`).
3. Starts pygame and opens a 1280x720 dummy display.
4. Generates a complete synthetic `Assets/` tree in a temp directory
   (`tests/support/assets.py`) and points `Helpers.ASSETS_FOLDER` at it.
5. Replaces `Helpers.handle_exception` and `Helpers.display_text` with recorders
   (`tests/support/patches.py`).

Steps 2 and 5 work because the rest of the codebase does `from Helpers import
handle_exception` at *its* import time — patch `Helpers` first and every module binds
the replacement.

## Design decisions worth knowing about

**Assets are always synthetic, never yours.** The repo ships no `Assets/`, so a
suite that used the real tree would behave differently on every machine and would
break whenever a file was renamed. `tests/support/assets.py` generates sprite sheets,
terrain, icons, menu art, `.wav` files, `.agl` grids and `.agd` object dicts with
pygame and the stdlib `wave` module — no binary fixtures in the repo. Sprite sheets are
32px-per-frame so that a loaded actor sprite comes out at 64x64, the same as
`Actor.SIZE`. `test_helpers.py` cross-checks the generated sprite-state list against
the real `MovementState` enum, so adding a state without a sheet fails loudly instead
of KeyError-ing somewhere unrelated.

**`handle_exception` raises instead of returning.** The real one never returns — it
exits the process. A stub that returned would let tests assert on code paths the game
can never reach, so the replacement raises `support.patches.HandledError` and tests use
`pytest.raises`.

**Third-party packages are stubbed unconditionally**, even when the real one is
installed, so a run is identical on your machine, on CI and on a fresh clone. That
buys determinism at the cost of one thing: a stub accepts any call, so it cannot notice
drift. `tests/test_thirdparty_seams.py` closes that gap — it runs in a subprocess where
`sys.modules` is clean, checks that the *real* `VisualEffect` still accepts every
keyword set the game passes it, and skips when the package is not installed.

**`StubLevel` is a real `Level` subclass.** Only `__init__` is replaced; every method
under test (`get_entities_in_range`, `purge`, `entities`, `award_achievements`,
`formatted_time`, …) is the shipped implementation. `StubController` borrows the real
`KEYBOARD_LAYOUTS`/`GAMEPAD_LAYOUTS` tables for the same reason. The tests in
`test_controller.py` build a genuine `Controller`, menus and selectors included.

**The menu screens are driven through `menu.loop()`.** `pause`, `settings`, `volume`,
`controls`, `main` and `pick_from_selector` are `while True` loops fed by a single
method; scripting that method (`_ScriptedLoop`) is what makes the flows testable. The
script raises once exhausted, so a flow that never terminates fails the test rather
than hanging it — which matters, because `Controller.main` has no "back" case.

## Layout

```
tests/
  conftest.py                   bootstrap + every shared fixture
  support/
    bootstrap.py                the ordered environment setup
    stubs.py                    SimpleVFX / steamworks / discordrp / cv2 stand-ins
    assets.py                   synthetic Assets/ tree generator
    patches.py                  handle_exception / display_text recorders
    doubles.py                  StubController, StubLevel, RecordingVFXManager, StubGamepad
  test_helpers.py               enums, asset loaders, text pipeline, geometry utilities
  test_entity.py                the base class every game object inherits
  test_actor.py                 movement, jumping, damage, resizing, animation states
  test_player.py                abilities, per-level stats, input-facing verbs
  test_nonplayer.py             patrol routes, alert state machine, detection
  test_difficulty.py            the hits-to-kill / hits-to-die contract, end to end
  test_boss.py                  on-screen presence, health bar, boss music
  test_block.py                 terrain, breakables, movers, doors, hazards
  test_projectile.py            travel, range clamping, impact
  test_objective.py             collection, grouping, pointer, persistence
  test_trigger.py               all fifteen trigger classes
  test_level.py                 entity registry, spatial index, achievements
  test_entity_factory.py        token-to-entity construction, grid parsing
  test_camera.py                focus tracking, offset clamping, layer composition
  test_hud.py                   health bars, ability icons, mission timer
  test_menu.py                  buttons, sliders, focus navigation, input loop
  test_controller.py            input dispatch, settings, menu flows
  test_particle_effect.py       rain, snow, film grain
  test_cinematic.py             loading, queueing, slide and video playback
  test_saveload.py              profile and save-game round trips
  test_connections.py           Steamworks and Discord error handling
  test_integration_level.py     build a real Level from .agl/.agd and run frames
  test_engine_import.py         Engine imports cleanly (subprocess)
  test_thirdparty_seams.py      real-package signature checks (subprocess, skippable)
  test_bootstrap_smoke.py       sanity checks on the harness itself
```

## Markers

- `slow` — render loops, fades and cinematic playback. `-m "not slow"` skips them.
- `integration` — builds a genuine `Level` end to end.

## Known defects

None outstanding. Twenty real defects turned up while this suite was written; all of
them are fixed, and every test asserts the corrected behaviour rather than pinning the
old one. `BUGS_FOUND.md` at the repo root records what each one was, what changed, and
which test covers it — three of them changed how the game plays and are marked there.

If you fix something the suite has an opinion about in future, the convention used here
is worth keeping: write the test against the behaviour you *want*, and if you are not
ready to fix it yet, mark it `@pytest.mark.xfail(strict=True)` so the marker fails the
build once the bug goes away and forces you to clean it up.
