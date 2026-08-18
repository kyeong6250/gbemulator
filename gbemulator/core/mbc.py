class NoMBC:
    def __init__(self, cartridge):
        self.rom = cartridge.rom
        self.ram = bytearray(cartridge.ram_size)

    def read(self, addr):
        if addr <= 0x7FFF:
            return self.rom[addr] if addr < len(self.rom) else 0xFF
        if 0xA000 <= addr <= 0xBFFF:
            offset = addr - 0xA000
            return self.ram[offset] if offset < len(self.ram) else 0xFF
        return 0xFF

    def write(self, addr, value):
        if 0xA000 <= addr <= 0xBFFF:
            offset = addr - 0xA000
            if offset < len(self.ram):
                self.ram[offset] = value & 0xFF


class MBC1:
    def __init__(self, cartridge):
        self.rom = cartridge.rom
        self.ram = bytearray(cartridge.ram_size)
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_enabled = False
        self.banking_mode = 0
        self.num_rom_banks = max(1, len(self.rom) // 0x4000)

    def read(self, addr):
        if addr <= 0x3FFF:
            return self.rom[addr] if addr < len(self.rom) else 0xFF
        if 0x4000 <= addr <= 0x7FFF:
            offset = (self.rom_bank * 0x4000) + (addr - 0x4000)
            return self.rom[offset] if offset < len(self.rom) else 0xFF
        if 0xA000 <= addr <= 0xBFFF:
            if not self.ram_enabled or len(self.ram) == 0:
                return 0xFF
            offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
            return self.ram[offset] if offset < len(self.ram) else 0xFF
        return 0xFF

    def write(self, addr, value):
        value &= 0xFF
        if addr <= 0x1FFF:
            self.ram_enabled = (value & 0x0F) == 0x0A
        elif 0x2000 <= addr <= 0x3FFF:
            bank = value & 0x1F
            if bank == 0:
                bank = 1
            self.rom_bank = (self.rom_bank & 0x60) | bank
            self.rom_bank %= self.num_rom_banks or 1
            if self.rom_bank == 0:
                self.rom_bank = 1
        elif 0x4000 <= addr <= 0x5FFF:
            bits = value & 0x03
            if self.banking_mode == 0:
                self.rom_bank = (self.rom_bank & 0x1F) | (bits << 5)
            else:
                self.ram_bank = bits
        elif 0x6000 <= addr <= 0x7FFF:
            self.banking_mode = value & 0x01
        elif 0xA000 <= addr <= 0xBFFF:
            if self.ram_enabled and len(self.ram) > 0:
                offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
                if offset < len(self.ram):
                    self.ram[offset] = value


class MBC3:
    """ROM/RAM banking half of MBC3 -- covers cart types 0x0F-0x13, which is
    enough for RAM+battery titles like Pokemon Red/Blue/Yellow (0x13). The
    real-time-clock registers (selected via ram_bank 0x08-0x0C, present on
    cart types 0x0F/0x10) are deliberately not emulated: reads return 0 and
    the latch write (0x6000-0x7FFF) is a no-op, rather than raising, so a
    game that merely probes for RTC hardware doesn't crash."""

    def __init__(self, cartridge):
        self.rom = cartridge.rom
        self.ram = bytearray(cartridge.ram_size)
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_and_timer_enabled = False
        self.num_rom_banks = max(1, len(self.rom) // 0x4000)

    def read(self, addr):
        if addr <= 0x3FFF:
            return self.rom[addr] if addr < len(self.rom) else 0xFF
        if 0x4000 <= addr <= 0x7FFF:
            offset = (self.rom_bank * 0x4000) + (addr - 0x4000)
            return self.rom[offset] if offset < len(self.rom) else 0xFF
        if 0xA000 <= addr <= 0xBFFF:
            if not self.ram_and_timer_enabled:
                return 0xFF
            if self.ram_bank > 0x03:
                return 0x00  # unemulated RTC register
            if len(self.ram) == 0:
                return 0xFF
            offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
            return self.ram[offset] if offset < len(self.ram) else 0xFF
        return 0xFF

    def write(self, addr, value):
        value &= 0xFF
        if addr <= 0x1FFF:
            self.ram_and_timer_enabled = (value & 0x0F) == 0x0A
        elif 0x2000 <= addr <= 0x3FFF:
            bank = value & 0x7F
            self.rom_bank = bank if bank != 0 else 1
        elif 0x4000 <= addr <= 0x5FFF:
            self.ram_bank = value  # 0x00-0x03: RAM bank. 0x08-0x0C: RTC register (unemulated).
        elif 0x6000 <= addr <= 0x7FFF:
            pass  # RTC latch -- no-op, RTC isn't emulated
        elif 0xA000 <= addr <= 0xBFFF:
            if self.ram_and_timer_enabled and self.ram_bank <= 0x03 and len(self.ram) > 0:
                offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
                if offset < len(self.ram):
                    self.ram[offset] = value
