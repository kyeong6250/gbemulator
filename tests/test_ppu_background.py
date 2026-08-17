from gbemulator.core.ppu import PPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def _set_tile(mmu, tile_index, rows):
    """rows: list of 8 (low_byte, high_byte) tuples, unsigned tile data at 0x8000."""
    base = 0x8000 + tile_index * 16
    for i, (lo, hi) in enumerate(rows):
        mmu.mem[base + i * 2] = lo
        mmu.mem[base + i * 2 + 1] = hi


def test_decode_tile_row_msb_first():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    # low=0b10000001, high=0b11000011 -> pixel0: hi=1,lo=1->3; pixel7: hi=1,lo=1->3
    pixels = ppu._decode_tile_row(0b10000001, 0b11000011)
    assert pixels[0] == 3
    assert pixels[7] == 3
    assert pixels[1] == 2  # hi=1,lo=0


def test_background_row_uses_tile_data_and_palette():
    mmu = FakeMMU()
    # Tile 0: solid color index 3 on every pixel of row 0
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    # BG tilemap at 0x9800: all tile index 0
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
    mmu.mem[0xFF40] = 0x91  # LCDC: BG enabled (bit0), tile data 0x8000 (bit4), BG map 0x9800 (bit3=0)
    mmu.mem[0xFF47] = 0xE4  # BGP: identity mapping (00->0,01->1,10->2,11->3)
    mmu.mem[0xFF42] = 0  # SCY
    mmu.mem[0xFF43] = 0  # SCX
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    assert ppu.framebuffer[0][0] == 3
    assert ppu.framebuffer[0][7] == 3


def test_background_row_respects_scroll():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # tile 0: all color 0
    _set_tile(mmu, 1, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # tile 1: row0 all color 3
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
    mmu.mem[0x9800 + 1] = 1  # second tile in the map is tile 1
    mmu.mem[0xFF40] = 0x91
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF42] = 0
    mmu.mem[0xFF43] = 8  # scroll right by 8 -> first visible tile is map tile index 1
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    assert ppu.framebuffer[0][0] == 3


def test_background_disabled_leaves_framebuffer_blank():
    mmu = FakeMMU()
    mmu.mem[0xFF40] = 0x90  # bit0 (BG enable) clear
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu.tick(456)  # runs a full scanline through _render_scanline
    assert ppu.framebuffer[0][0] == 0
