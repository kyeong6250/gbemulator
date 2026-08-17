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


def _set_sprite(mmu, slot, y, x, tile, attrs):
    base = 0xFE00 + slot * 4
    mmu.mem[base] = y
    mmu.mem[base + 1] = x
    mmu.mem[base + 2] = tile
    mmu.mem[base + 3] = attrs


def test_sprite_drawn_at_correct_position():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # row0 color 3
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)  # screen pos: y=0, x=0
    mmu.mem[0xFF40] = 0x93  # LCDC: BG+sprites enabled, 8x8 sprites
    mmu.mem[0xFF48] = 0xE4  # OBP0 identity
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 3


def test_sprite_off_screen_not_drawn():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    _set_sprite(mmu, 0, y=0, x=8, tile=0, attrs=0x00)  # y=16-16=0 -> off top of screen
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 0


def test_sprite_color_0_is_transparent():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # all color 0
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu.framebuffer[0][0] = 2  # pre-existing background pixel
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 2  # untouched, sprite pixel was transparent


def test_sprites_disabled_via_lcdc():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)
    mmu.mem[0xFF40] = 0x91  # bit1 (sprite enable) clear
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 0


def test_x_flip_mirrors_tile_row():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0b10000000, 0b10000000)] + [(0x00, 0x00)] * 7)  # only pixel0 = color3
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x20)  # bit5 = x-flip
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][7] == 3  # flipped from position 0 to position 7
