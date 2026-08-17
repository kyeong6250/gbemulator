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

    def _get_r8(self, idx):
        if idx == 0: return self.b
        if idx == 1: return self.c
        if idx == 2: return self.d
        if idx == 3: return self.e
        if idx == 4: return self.h
        if idx == 5: return self.l
        if idx == 6: return self.mmu.read(self.hl)
        return self.a  # idx == 7

    def _set_r8(self, idx, value):
        value &= 0xFF
        if idx == 0: self.b = value
        elif idx == 1: self.c = value
        elif idx == 2: self.d = value
        elif idx == 3: self.e = value
        elif idx == 4: self.h = value
        elif idx == 5: self.l = value
        elif idx == 6: self.mmu.write(self.hl, value)
        else: self.a = value

    def _ld_r_r(self, opcode):
        dst = (opcode >> 3) & 0x07
        src = opcode & 0x07
        self._set_r8(dst, self._get_r8(src))
        return 8 if (dst == 6 or src == 6) else 4

    def _ld_r_d8(self, opcode):
        dst = (opcode >> 3) & 0x07
        self._set_r8(dst, self.fetch8())
        return 12 if dst == 6 else 8

    def _alu_add(self, value, carry_in=0):
        result = self.a + value + carry_in
        self.set_flag(self.HALF_CARRY_FLAG, ((self.a & 0xF) + (value & 0xF) + carry_in) > 0xF)
        self.set_flag(self.CARRY_FLAG, result > 0xFF)
        self.a = result & 0xFF
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)

    def _alu_sub(self, value, carry_in=0, store=True):
        result = self.a - value - carry_in
        self.set_flag(self.HALF_CARRY_FLAG, (self.a & 0xF) < ((value & 0xF) + carry_in))
        self.set_flag(self.CARRY_FLAG, result < 0)
        result &= 0xFF
        self.set_flag(self.ZERO_FLAG, result == 0)
        self.set_flag(self.SUB_FLAG, True)
        if store:
            self.a = result

    def _alu_and(self, value):
        self.a &= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, True)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_or(self, value):
        self.a |= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, False)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_xor(self, value):
        self.a ^= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, False)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_dispatch(self, op_idx, value):
        carry = self.get_flag(self.CARRY_FLAG)
        if op_idx == 0: self._alu_add(value)
        elif op_idx == 1: self._alu_add(value, carry)
        elif op_idx == 2: self._alu_sub(value)
        elif op_idx == 3: self._alu_sub(value, carry)
        elif op_idx == 4: self._alu_and(value)
        elif op_idx == 5: self._alu_xor(value)
        elif op_idx == 6: self._alu_or(value)
        elif op_idx == 7: self._alu_sub(value, 0, store=False)  # CP

    def execute(self, opcode):
        if 0x40 <= opcode <= 0x7F and opcode != 0x76:
            return self._ld_r_r(opcode)
        if opcode in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E):
            return self._ld_r_d8(opcode)
        if opcode == 0x0A:
            self.a = self.mmu.read(self.bc)
            return 8
        if opcode == 0x1A:
            self.a = self.mmu.read(self.de)
            return 8
        if opcode == 0x02:
            self.mmu.write(self.bc, self.a)
            return 8
        if opcode == 0x12:
            self.mmu.write(self.de, self.a)
            return 8
        if opcode == 0x2A:
            self.a = self.mmu.read(self.hl)
            self.hl = (self.hl + 1) & 0xFFFF
            return 8
        if opcode == 0x3A:
            self.a = self.mmu.read(self.hl)
            self.hl = (self.hl - 1) & 0xFFFF
            return 8
        if opcode == 0x22:
            self.mmu.write(self.hl, self.a)
            self.hl = (self.hl + 1) & 0xFFFF
            return 8
        if opcode == 0x32:
            self.mmu.write(self.hl, self.a)
            self.hl = (self.hl - 1) & 0xFFFF
            return 8
        if opcode == 0xE0:
            self.mmu.write(0xFF00 + self.fetch8(), self.a)
            return 12
        if opcode == 0xF0:
            self.a = self.mmu.read(0xFF00 + self.fetch8())
            return 12
        if opcode == 0xE2:
            self.mmu.write(0xFF00 + self.c, self.a)
            return 8
        if opcode == 0xF2:
            self.a = self.mmu.read(0xFF00 + self.c)
            return 8
        if opcode == 0xEA:
            self.mmu.write(self.fetch16(), self.a)
            return 16
        if opcode == 0xFA:
            self.a = self.mmu.read(self.fetch16())
            return 16
        if opcode in (0x01, 0x11, 0x21, 0x31):
            value = self.fetch16()
            if opcode == 0x01: self.bc = value
            elif opcode == 0x11: self.de = value
            elif opcode == 0x21: self.hl = value
            else: self.sp = value
            return 12
        if opcode == 0x08:
            addr = self.fetch16()
            self.mmu.write(addr, self.sp & 0xFF)
            self.mmu.write((addr + 1) & 0xFFFF, (self.sp >> 8) & 0xFF)
            return 20
        if opcode == 0xF9:
            self.sp = self.hl
            return 8
        if opcode == 0xF8:
            offset = self._signed8(self.fetch8())
            result = (self.sp + offset) & 0xFFFF
            self.set_flag(self.ZERO_FLAG, False)
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, ((self.sp & 0xF) + (offset & 0xF)) > 0xF)
            self.set_flag(self.CARRY_FLAG, ((self.sp & 0xFF) + (offset & 0xFF)) > 0xFF)
            self.hl = result
            return 12
        if opcode in (0xC5, 0xD5, 0xE5, 0xF5):
            value = {0xC5: self.bc, 0xD5: self.de, 0xE5: self.hl, 0xF5: self.af}[opcode]
            self._push16(value)
            return 16
        if opcode in (0xC1, 0xD1, 0xE1, 0xF1):
            value = self._pop16()
            if opcode == 0xC1: self.bc = value
            elif opcode == 0xD1: self.de = value
            elif opcode == 0xE1: self.hl = value
            else: self.af = value
            return 12
        if opcode == 0x00:
            return 4
        if opcode == 0x76:
            self.halted = True
            return 4
        if opcode == 0x10:
            self.fetch8()  # STOP's mandatory second byte, unused in our scope
            return 4
        if opcode == 0xF3:
            self.ime = False
            return 4
        if opcode == 0xFB:
            self.ime_pending = True
            return 4
        if 0x80 <= opcode <= 0xBF:
            op_idx = (opcode >> 3) & 0x07
            src = opcode & 0x07
            self._alu_dispatch(op_idx, self._get_r8(src))
            return 8 if src == 6 else 4
        if opcode in (0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE):
            op_idx = (opcode >> 3) & 0x07
            self._alu_dispatch(op_idx, self.fetch8())
            return 8
        raise NotImplementedError(f"Opcode {opcode:#04x} not implemented at PC={self.pc - 1:#06x}")

    def _push16(self, value):
        self.sp = (self.sp - 1) & 0xFFFF
        self.mmu.write(self.sp, (value >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.mmu.write(self.sp, value & 0xFF)

    def _pop16(self):
        lo = self.mmu.read(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        hi = self.mmu.read(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        return (hi << 8) | lo

    def _signed8(self, value):
        return value - 256 if value & 0x80 else value

    def step(self):
        if self.halted:
            return 4
        if self.ime_pending:
            self.ime = True
            self.ime_pending = False
        opcode = self.fetch8()
        return self.execute(opcode)
