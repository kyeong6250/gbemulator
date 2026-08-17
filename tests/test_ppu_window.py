from gbemulator.core.ppu import PPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def _set_tile(mmu, tile_index, rows):
    base = 0x8000 + tile_index * 16
    for i, (lo, hi) in enumerate(rows):
        mmu.mem[base + i * 2] = lo
        mmu.mem[base + i * 2 + 1] = hi


def test_window_drawn_when_enabled_and_within_bounds():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # bg tile: color 0
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # window tile: row0 color 3
    for i in range(32):
        mmu.mem[0x9800 + i] = 0  # BG map all tile 0
        mmu.mem[0x9C00 + i] = 5  # window map all tile 5
    mmu.mem[0xFF40] = 0xF1  # LCDC: BG on, window on (bit5), window map 0x9C00 (bit6), tile data 0x8000 (bit4)
    mmu.mem[0xFF47] = 0xE4  # BGP identity
    mmu.mem[0xFF4A] = 0  # WY = 0
    mmu.mem[0xFF4B] = 7  # WX = 7 -> window starts at screen x=0
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 3


def test_window_not_drawn_above_wy():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
        mmu.mem[0x9C00 + i] = 5
    mmu.mem[0xFF40] = 0xF1
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF4A] = 10  # WY = 10, window hasn't started at ly=0
    mmu.mem[0xFF4B] = 7
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 0


def test_window_disabled_leaves_background():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
        mmu.mem[0x9C00 + i] = 5
    mmu.mem[0xFF40] = 0x91  # window disabled (bit5 clear)
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF4A] = 0
    mmu.mem[0xFF4B] = 7
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 0
