# gbemulator/core/cpu.py
class CPU:
    ZERO_FLAG = 0x80
    SUB_FLAG = 0x40
    HALF_CARRY_FLAG = 0x20
    CARRY_FLAG = 0x10

    def __init__(self, mmu):
        self.mmu = mmu
        self.a = 0x01
        self.f = 0xB0
        self.b = 0x00
        self.c = 0x13
        self.d = 0x00
        self.e = 0xD8
        self.h = 0x01
        self.l = 0x4D
        self.sp = 0xFFFE
        self.pc = 0x0100
        self.ime = False
        self.ime_pending = False
        self.halted = False

    @property
    def bc(self):
        return (self.b << 8) | self.c

    @bc.setter
    def bc(self, value):
        value &= 0xFFFF
        self.b, self.c = (value >> 8) & 0xFF, value & 0xFF

    @property
    def de(self):
        return (self.d << 8) | self.e

    @de.setter
    def de(self, value):
        value &= 0xFFFF
        self.d, self.e = (value >> 8) & 0xFF, value & 0xFF

    @property
    def hl(self):
        return (self.h << 8) | self.l

    @hl.setter
    def hl(self, value):
        value &= 0xFFFF
        self.h, self.l = (value >> 8) & 0xFF, value & 0xFF

    @property
    def af(self):
        return (self.a << 8) | (self.f & 0xF0)

    @af.setter
    def af(self, value):
        value &= 0xFFFF
        self.a, self.f = (value >> 8) & 0xFF, value & 0xF0

    def get_flag(self, mask):
        return 1 if (self.f & mask) else 0

    def set_flag(self, mask, value):
        if value:
            self.f |= mask
        else:
            self.f &= ~mask & 0xFF

    def fetch8(self):
        value = self.mmu.read(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return value

    def fetch16(self):
        lo = self.fetch8()
        hi = self.fetch8()
        return (hi << 8) | lo

    def execute(self, opcode):
        raise NotImplementedError(f"Opcode {opcode:#04x} not implemented at PC={self.pc - 1:#06x}")

    def step(self):
        opcode = self.fetch8()
        return self.execute(opcode)
