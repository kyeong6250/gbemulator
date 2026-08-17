_RAM_SIZES = {0: 0, 1: 2 * 1024, 2: 8 * 1024, 3: 32 * 1024, 4: 128 * 1024, 5: 64 * 1024}


class Cartridge:
    def __init__(self, rom_bytes):
        self.rom = rom_bytes
        self.title = rom_bytes[0x134:0x144].split(b"\x00")[0].decode("ascii", errors="ignore")
        self.cart_type = rom_bytes[0x147]
        self.rom_size = 32 * 1024 * (1 << rom_bytes[0x148])
        self.ram_size = _RAM_SIZES.get(rom_bytes[0x149], 0)
        self.mbc = self._make_mbc()

    def _make_mbc(self):
        if self.cart_type == 0x00:
            from .mbc import NoMBC
            return NoMBC(self)
        if self.cart_type in (0x01, 0x02, 0x03):
            from .mbc import MBC1
            return MBC1(self)
        raise ValueError(f"Unsupported cartridge type: {self.cart_type:#04x}")

    def read(self, addr):
        return self.mbc.read(addr)

    def write(self, addr, value):
        self.mbc.write(addr, value)
