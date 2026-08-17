import pytest


def test_add_sets_carry_and_half_carry(cpu, mmu):
    cpu.a = 0xFF
    cpu.b = 0x01
    mmu.mem[0x0100] = 0x80  # ADD A,B
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_adc_includes_carry_in(cpu, mmu):
    cpu.a = 0x01
    cpu.b = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x88  # ADC A,B
    cpu.step()
    assert cpu.a == 0x03


def test_sub_sets_carry_when_borrow(cpu, mmu):
    cpu.a = 0x02
    cpu.b = 0x03
    mmu.mem[0x0100] = 0x90  # SUB B
    cpu.step()
    assert cpu.a == 0xFF
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 1


def test_sbc_includes_carry_in(cpu, mmu):
    cpu.a = 0x05
    cpu.b = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x98  # SBC A,B
    cpu.step()
    assert cpu.a == 0x03


def test_and_sets_half_carry_clears_carry(cpu, mmu):
    cpu.a = 0xF0
    cpu.b = 0xFF
    mmu.mem[0x0100] = 0xA0  # AND B
    cpu.step()
    assert cpu.a == 0xF0
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_xor_a_a_zeroes_and_sets_zero_flag(cpu, mmu):
    cpu.a = 0x5A
    mmu.mem[0x0100] = 0xAF  # XOR A
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_or_clears_flags_except_zero(cpu, mmu):
    cpu.a = 0x00
    cpu.b = 0x00
    mmu.mem[0x0100] = 0xB0  # OR B
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 0


def test_cp_does_not_modify_a(cpu, mmu):
    cpu.a = 0x10
    cpu.b = 0x10
    mmu.mem[0x0100] = 0xB8  # CP B
    cpu.step()
    assert cpu.a == 0x10
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_add_a_hl_indirect_costs_8_cycles(cpu, mmu):
    cpu.a = 0x01
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x01
    mmu.mem[0x0100] = 0x86  # ADD A,(HL)
    cycles = cpu.step()
    assert cpu.a == 0x02
    assert cycles == 8


@pytest.mark.parametrize("opcode,a,operand,expected", [
    (0xC6, 0x01, 0x01, 0x02),  # ADD A,d8
    (0xD6, 0x05, 0x03, 0x02),  # SUB d8
    (0xE6, 0xFF, 0x0F, 0x0F),  # AND d8
    (0xF6, 0x00, 0x0F, 0x0F),  # OR d8
])
def test_immediate_arithmetic(cpu, mmu, opcode, a, operand, expected):
    cpu.a = a
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = operand
    cpu.step()
    assert cpu.a == expected
