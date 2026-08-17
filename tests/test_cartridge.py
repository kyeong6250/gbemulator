import pytest
from gbemulator.core.cartridge import Cartridge


def _make_rom(cart_type=0x00, rom_size_code=0x00, ram_size_code=0x00, title=b"TESTROM"):
    rom = bytearray(32 * 1024)
    rom[0x134:0x134 + len(title)] = title
    rom[0x147] = cart_type
    rom[0x148] = rom_size_code
    rom[0x149] = ram_size_code
    return bytes(rom)


def test_parses_title():
    cart = Cartridge(_make_rom(title=b"ZELDA"))
    assert cart.title == "ZELDA"


def test_parses_rom_and_ram_size():
    cart = Cartridge(_make_rom(rom_size_code=0x01, ram_size_code=0x02))
    assert cart.rom_size == 64 * 1024
    assert cart.ram_size == 8 * 1024


def test_unsupported_cart_type_raises():
    with pytest.raises(ValueError):
        Cartridge(_make_rom(cart_type=0x1B))  # MBC5, unsupported in v1
