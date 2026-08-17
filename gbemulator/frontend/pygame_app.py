import sys

import numpy as np
import pygame

from ..core.gameboy import GameBoy

SCALE = 3
SHADE_COLORS = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]
_PALETTE_LUT = np.array(SHADE_COLORS, dtype=np.uint8)

KEY_MAP = {
    pygame.K_RIGHT: "right",
    pygame.K_LEFT: "left",
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_x: "a",
    pygame.K_z: "b",
    pygame.K_SPACE: "select",
    pygame.K_RETURN: "start",
}


def framebuffer_to_rgb(framebuffer):
    rgb = _PALETTE_LUT[framebuffer]  # (144, 160, 3)
    return rgb.swapaxes(0, 1)  # pygame surfarray expects (width, height, 3)


def run(rom_path):
    gb = GameBoy(rom_path)
    pygame.init()
    screen = pygame.display.set_mode((160 * SCALE, 144 * SCALE))
    pygame.display.set_caption("gbemulator")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in KEY_MAP:
                gb.joypad.set_button(KEY_MAP[event.key], True)
            elif event.type == pygame.KEYUP and event.key in KEY_MAP:
                gb.joypad.set_button(KEY_MAP[event.key], False)

        framebuffer = gb.run_frame()
        rgb = framebuffer_to_rgb(framebuffer)
        surface = pygame.surfarray.make_surface(rgb)
        surface = pygame.transform.scale(surface, (160 * SCALE, 144 * SCALE))
        screen.blit(surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run(sys.argv[1])
