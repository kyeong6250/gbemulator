import pytest


@pytest.mark.parametrize("opcode,attr", [(0x04, "b"), (0x0C, "c"), (0x14, "d"), (0x3C, "a")])
def test_inc_r8(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x0F)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x10
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_inc_r8_wraps_and_sets_zero(cpu, mmu):
    cpu.a = 0xFF
    mmu.mem[0x0100] = 0x3C
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_inc_r8_does_not_touch_carry(cpu, mmu):
    cpu.set_flag(cpu.CARRY_FLAG, True)
    cpu.a = 0x01
    mmu.mem[0x0100] = 0x3C
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


@pytest.mark.parametrize("opcode,attr", [(0x05, "b"), (0x0D, "c"), (0x3D, "a")])
def test_dec_r8(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x10)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x0F
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 1


def test_inc_hl_indirect(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x05
    mmu.mem[0x0100] = 0x34  # INC (HL)
    cycles = cpu.step()
    assert mmu.mem[0xC000] == 0x06
    assert cycles == 12


@pytest.mark.parametrize("opcode,attr", [(0x03, "bc"), (0x13, "de"), (0x23, "hl"), (0x33, "sp")])
def test_inc_rr(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0xFFFF)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x0000


@pytest.mark.parametrize("opcode,attr", [(0x0B, "bc"), (0x1B, "de"), (0x2B, "hl"), (0x3B, "sp")])
def test_dec_rr(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x0000)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0xFFFF


def test_inc_dec_rr_does_not_touch_flags(cpu, mmu):
    cpu.f = 0xF0
    cpu.bc = 0x1000
    mmu.mem[0x0100] = 0x03
    cpu.step()
    assert cpu.f == 0xF0


@pytest.mark.parametrize("opcode,attr", [(0x09, "bc"), (0x19, "de"), (0x39, "sp")])
def test_add_hl_rr(cpu, mmu, opcode, attr):
    cpu.hl = 0x0FFF
    setattr(cpu, attr, 0x0001)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert cpu.hl == 0x1000
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_add_hl_hl(cpu, mmu):
    cpu.hl = 0x8000
    mmu.mem[0x0100] = 0x29
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_add_hl_rr_preserves_zero_flag(cpu, mmu):
    cpu.set_flag(cpu.ZERO_FLAG, True)
    cpu.hl = 0x0001
    cpu.bc = 0x0001
    mmu.mem[0x0100] = 0x09
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
