import numpy as np

from gbemulator.frontend.pygame_app import framebuffer_to_rgb, SHADE_COLORS


def test_framebuffer_to_rgb_maps_shades_to_colors():
    framebuffer = np.zeros((144, 160), dtype=np.uint8)
    framebuffer[0][0] = 3
    rgb = framebuffer_to_rgb(framebuffer)
    assert rgb.shape == (160, 144, 3)
    assert tuple(rgb[0][0]) == SHADE_COLORS[3]
    assert tuple(rgb[1][0]) == SHADE_COLORS[0]
