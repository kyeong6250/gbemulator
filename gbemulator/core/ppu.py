import numpy as np

from . import interrupts

LY_ADDR = 0xFF44
STAT_ADDR = 0xFF41


class PPU:
    MODE_HBLANK = 0
    MODE_VBLANK = 1
    MODE_OAM = 2
    MODE_TRANSFER = 3

    def __init__(self, mmu):
        self.mmu = mmu
        self.mode = self.MODE_OAM
        self.mode_clock = 0
        self.ly = 0
        self.frame_ready = False
        self.framebuffer = np.zeros((144, 160), dtype=np.uint8)
        self._update_stat()

    def _update_stat(self):
        stat = self.mmu.mem[STAT_ADDR]
        self.mmu.mem[STAT_ADDR] = (stat & 0xFC) | (self.mode & 0x03)

    def tick(self, cycles):
        self.mode_clock += cycles
        while True:
            if self.mode == self.MODE_OAM:
                if self.mode_clock >= 80:
                    self.mode_clock -= 80
                    self.mode = self.MODE_TRANSFER
                else:
                    break
            elif self.mode == self.MODE_TRANSFER:
                if self.mode_clock >= 172:
                    self.mode_clock -= 172
                    self.mode = self.MODE_HBLANK
                    self._render_scanline()
                else:
                    break
            elif self.mode == self.MODE_HBLANK:
                if self.mode_clock >= 204:
                    self.mode_clock -= 204
                    self._advance_line()
                    if self.ly == 144:
                        self.mode = self.MODE_VBLANK
                        interrupts.request(self.mmu, interrupts.VBLANK)
                        self.frame_ready = True
                    else:
                        self.mode = self.MODE_OAM
                else:
                    break
            elif self.mode == self.MODE_VBLANK:
                if self.mode_clock >= 456:
                    self.mode_clock -= 456
                    self._advance_line()
                    if self.ly > 153:
                        self.ly = 0
                        self.mmu.mem[LY_ADDR] = 0
                        self.mode = self.MODE_OAM
                else:
                    break
        self._update_stat()

    def _advance_line(self):
        self.ly += 1
        self.mmu.mem[LY_ADDR] = self.ly & 0xFF

    def _decode_tile_row(self, low_byte, high_byte):
        return [
            (((high_byte >> (7 - i)) & 1) << 1) | ((low_byte >> (7 - i)) & 1)
            for i in range(8)
        ]

    def _apply_palette(self, color_index, palette_byte):
        return (palette_byte >> (color_index * 2)) & 0x03

    def _render_background_row(self):
        lcdc = self.mmu.mem[0xFF40]
        if not (lcdc & 0x01):
            return
        scy = self.mmu.mem[0xFF42]
        scx = self.mmu.mem[0xFF43]
        bgp = self.mmu.mem[0xFF47]
        tile_map_base = 0x9C00 if (lcdc & 0x08) else 0x9800
        tile_data_signed = not (lcdc & 0x10)

        y = (self.ly + scy) & 0xFF
        tile_row = y // 8
        pixel_row = y % 8

        for screen_x in range(160):
            x = (screen_x + scx) & 0xFF
            tile_col = x // 8
            pixel_col = x % 8

            map_index = tile_map_base + tile_row * 32 + tile_col
            tile_index = self.mmu.mem[map_index]
            if tile_data_signed:
                signed_index = tile_index - 256 if tile_index > 127 else tile_index
                tile_addr = 0x9000 + signed_index * 16
            else:
                tile_addr = 0x8000 + tile_index * 16

            row_addr = tile_addr + pixel_row * 2
            low_byte = self.mmu.mem[row_addr]
            high_byte = self.mmu.mem[row_addr + 1]
            color_index = self._decode_tile_row(low_byte, high_byte)[pixel_col]
            self.framebuffer[self.ly][screen_x] = self._apply_palette(color_index, bgp)

    def _render_window_row(self):
        lcdc = self.mmu.mem[0xFF40]
        if not (lcdc & 0x20):
            return
        wy = self.mmu.mem[0xFF4A]
        wx = self.mmu.mem[0xFF4B]
        if self.ly < wy:
            return

        bgp = self.mmu.mem[0xFF47]
        tile_map_base = 0x9C00 if (lcdc & 0x40) else 0x9800
        tile_data_signed = not (lcdc & 0x10)

        window_y = self.ly - wy
        tile_row = window_y // 8
        pixel_row = window_y % 8

        for screen_x in range(160):
            window_x = screen_x - (wx - 7)
            if window_x < 0:
                continue
            tile_col = window_x // 8
            pixel_col = window_x % 8

            map_index = tile_map_base + tile_row * 32 + tile_col
            tile_index = self.mmu.mem[map_index]
            if tile_data_signed:
                signed_index = tile_index - 256 if tile_index > 127 else tile_index
                tile_addr = 0x9000 + signed_index * 16
            else:
                tile_addr = 0x8000 + tile_index * 16

            row_addr = tile_addr + pixel_row * 2
            low_byte = self.mmu.mem[row_addr]
            high_byte = self.mmu.mem[row_addr + 1]
            color_index = self._decode_tile_row(low_byte, high_byte)[pixel_col]
            self.framebuffer[self.ly][screen_x] = self._apply_palette(color_index, bgp)

    def _render_scanline(self):
        self._render_background_row()
        self._render_window_row()
