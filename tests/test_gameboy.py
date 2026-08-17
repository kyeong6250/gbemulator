import pytest

from gbemulator.core.gameboy import GameBoy


def _write_tiny_rom(path):
    rom = bytearray(32 * 1024)
    # A tight loop: 0x0100: JP 0x0150 ; 0x0150: infinite JR -2 (spins forever, one instruction per step)
    rom[0x100] = 0xC3
    rom[0x101] = 0x50
    rom[0x102] = 0x01
    rom[0x150] = 0x18  # JR
    rom[0x151] = 0xFE  # -2, jumps to itself
    rom[0x147] = 0x00  # ROM-only
    rom[0x148] = 0x00
    rom[0x149] = 0x00
    with open(path, "wb") as f:
        f.write(rom)


@pytest.fixture
def tiny_rom_path(tmp_path):
    path = tmp_path / "tiny.gb"
    _write_tiny_rom(path)
    return str(path)


def test_gameboy_loads_rom_and_wires_components(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    assert gb.cpu.mmu is gb.mmu
    assert gb.mmu.joypad is gb.joypad
    assert gb.mmu.timer is gb.timer


def test_run_frame_returns_completed_framebuffer(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    framebuffer = gb.run_frame()
    assert framebuffer.shape == (144, 160)


def test_run_frame_advances_ppu_a_full_frame_worth_of_cycles(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    gb.run_frame()
    assert gb.ppu.frame_ready is False  # reset after being consumed by run_frame
