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

    def _render_scanline(self):
        pass  # filled in by Tasks 18-20
