from gbemulator.core.ppu import PPU
from gbemulator.core import interrupts


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def test_starts_in_oam_mode():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    assert ppu.mode == PPU.MODE_OAM


def test_transitions_oam_to_transfer_after_80_cycles():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(80)
    assert ppu.mode == PPU.MODE_TRANSFER


def test_transitions_transfer_to_hblank_after_172_more_cycles():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(80)
    ppu.tick(172)
    assert ppu.mode == PPU.MODE_HBLANK


def test_full_scanline_advances_ly_and_returns_to_oam():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(456)  # one full scanline: 80 + 172 + 204
    assert mmu.mem[0xFF44] == 1
    assert ppu.mode == PPU.MODE_OAM


def test_144th_scanline_enters_vblank_and_requests_interrupt():
    mmu = FakeMMU()
    mmu.write(0xFFFF, 0xFF)
    ppu = PPU(mmu)
    for _ in range(144):
        ppu.tick(456)
    assert ppu.mode == PPU.MODE_VBLANK
    assert ppu.frame_ready is True
    assert mmu.read(0xFF0F) & interrupts.VBLANK == interrupts.VBLANK


def test_after_154_scanlines_wraps_to_line_0_and_oam():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    for _ in range(154):
        ppu.tick(456)
    assert mmu.mem[0xFF44] == 0
    assert ppu.mode == PPU.MODE_OAM


def test_framebuffer_shape():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    assert ppu.framebuffer.shape == (144, 160)
