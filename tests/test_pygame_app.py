import numpy as np

from gbemulator.frontend.pygame_app import framebuffer_to_rgb, resolve_rom_path, SHADE_COLORS


def test_framebuffer_to_rgb_maps_shades_to_colors():
    framebuffer = np.zeros((144, 160), dtype=np.uint8)
    framebuffer[0][0] = 3
    rgb = framebuffer_to_rgb(framebuffer)
    assert rgb.shape == (160, 144, 3)
    assert tuple(rgb[0][0]) == SHADE_COLORS[3]
    assert tuple(rgb[1][0]) == SHADE_COLORS[0]


def test_resolve_rom_path_uses_argv_when_present():
    assert resolve_rom_path(["gbemulator", "game.gb"], prompt_fn=lambda: "unused") == "game.gb"


def test_resolve_rom_path_falls_back_to_prompt_when_no_argv():
    assert resolve_rom_path(["gbemulator"], prompt_fn=lambda: "picked.gb") == "picked.gb"


def test_resolve_rom_path_returns_none_when_prompt_cancelled():
    assert resolve_rom_path(["gbemulator"], prompt_fn=lambda: "") is None
