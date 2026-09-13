"""Sanity checks on the test harness itself."""
from __future__ import annotations

from pathlib import Path

import Helpers
import pygame


def test_assets_folder_is_the_synthetic_tree(assets_root: Path) -> None:
    assert Helpers.ASSETS_FOLDER == assets_root
    assert (assets_root / "Terrain" / "Terrain.png").is_file()


def test_game_data_is_sandboxed(game_data_dir: Path) -> None:
    assert "agentglitch-tests-home-" in str(game_data_dir)


def test_display_is_up() -> None:
    assert pygame.display.get_surface() is not None


def test_player_constructs(player) -> None:
    assert player.rect is not None
    assert player.hp == player.max_hp


def test_enemy_constructs(make_enemy) -> None:
    enemy = make_enemy()
    assert enemy.rect.width > 0
