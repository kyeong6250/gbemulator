from gbemulator.core.cartridge import Cartridge


def _make_mbc1_rom(num_banks=4, ram_size_code=0x02):
    rom = bytearray(0x4000 * num_banks)
    rom[0x147] = 0x01  # MBC1
    rom[0x148] = {2: 0x00, 4: 0x01, 8: 0x02}[num_banks]
    rom[0x149] = ram_size_code
    for bank in range(num_banks):
        rom[bank * 0x4000] = bank  # marker byte at start of each bank
    return bytes(rom)


def test_nomb_reads_rom_directly():
    rom = bytearray(32 * 1024)
    rom[0x150] = 0xAB
    cart = Cartridge(bytes(rom))
    assert cart.read(0x150) == 0xAB


def test_nomb_ram_read_write():
    cart = Cartridge(bytes(bytearray(32 * 1024)))
    cart.ram_size = 0  # ROM-only carts typically have no RAM; write should be ignored safely
    assert cart.mbc.read(0xA000) == 0xFF


def test_mbc1_bank0_fixed():
    cart = Cartridge(_make_mbc1_rom())
    assert cart.read(0x0000) == 0  # bank 0 marker


def test_mbc1_default_bank1_switchable_area():
    cart = Cartridge(_make_mbc1_rom())
    assert cart.read(0x4000) == 1  # defaults to bank 1


def test_mbc1_bank_switch():
    cart = Cartridge(_make_mbc1_rom(num_banks=4))
    cart.write(0x2000, 0x03)  # select bank 3
    assert cart.read(0x4000) == 3


def test_mbc1_bank_switch_zero_maps_to_one():
    cart = Cartridge(_make_mbc1_rom(num_banks=4))
    cart.write(0x2000, 0x00)  # writing 0 selects bank 1 per SM83 quirk
    assert cart.read(0x4000) == 1


def test_mbc1_ram_requires_enable():
    cart = Cartridge(_make_mbc1_rom(ram_size_code=0x02))
    cart.write(0xA000, 0x42)  # RAM disabled by default, write ignored
    assert cart.read(0xA000) == 0xFF
    cart.write(0x0000, 0x0A)  # enable RAM
    cart.write(0xA000, 0x42)
    assert cart.read(0xA000) == 0x42
