class MMU:
    def __init__(self, cartridge):
        self.cartridge = cartridge
        self.mem = bytearray(0x10000)
        self.joypad = None
        self.timer = None

    def read(self, addr):
        addr &= 0xFFFF
        if addr <= 0x7FFF or 0xA000 <= addr <= 0xBFFF:
            return self.cartridge.read(addr)
        if addr == 0xFF00 and self.joypad is not None:
            return self.joypad.read()
        return self.mem[addr]

    def write(self, addr, value):
        addr &= 0xFFFF
        value &= 0xFF
        if addr <= 0x7FFF or 0xA000 <= addr <= 0xBFFF:
            self.cartridge.write(addr, value)
            return
        if addr == 0xFF00 and self.joypad is not None:
            self.joypad.write(value)
            return
        if addr == 0xFF04 and self.timer is not None:
            self.timer.reset_div()
            return
        self.mem[addr] = value
