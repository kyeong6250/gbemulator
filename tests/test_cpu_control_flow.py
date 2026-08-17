import pytest


def test_jp_a16(cpu, mmu):
    mmu.mem[0x0100] = 0xC3
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == 0xC000


def test_jp_hl(cpu, mmu):
    cpu.hl = 0xD000
    mmu.mem[0x0100] = 0xE9
    cpu.step()
    assert cpu.pc == 0xD000


@pytest.mark.parametrize("opcode,flag,value,should_jump,expected_cycles", [
    (0xC2, "ZERO_FLAG", 0, True, 16),   # JP NZ - jumps when Z clear
    (0xC2, "ZERO_FLAG", 1, False, 12),
    (0xCA, "ZERO_FLAG", 1, True, 16),   # JP Z - jumps when Z set
    (0xD2, "CARRY_FLAG", 0, True, 16),  # JP NC
    (0xDA, "CARRY_FLAG", 1, True, 16),  # JP C
])
def test_jp_conditional(cpu, mmu, opcode, flag, value, should_jump, expected_cycles):
    cpu.set_flag(getattr(cpu, flag), value)
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cycles = cpu.step()
    assert cpu.pc == (0xC000 if should_jump else 0x0103)
    assert cycles == expected_cycles


def test_jr_forward(cpu, mmu):
    mmu.mem[0x0100] = 0x18
    mmu.mem[0x0101] = 0x05
    cpu.step()
    assert cpu.pc == 0x0107


def test_jr_backward(cpu, mmu):
    cpu.pc = 0x0110
    mmu.mem[0x0110] = 0x18
    mmu.mem[0x0111] = 0xFB  # -5
    cpu.step()
    assert cpu.pc == 0x010D


@pytest.mark.parametrize("opcode,flag,value,should_jump,expected_cycles", [
    (0x20, "ZERO_FLAG", 0, True, 12),   # JR NZ - jumps when Z clear
    (0x20, "ZERO_FLAG", 1, False, 8),   # JR NZ - not taken when Z set
    (0x28, "ZERO_FLAG", 1, True, 12),   # JR Z - jumps when Z set
    (0x28, "ZERO_FLAG", 0, False, 8),   # JR Z - not taken when Z clear
    (0x30, "CARRY_FLAG", 0, True, 12),  # JR NC - jumps when C clear
    (0x30, "CARRY_FLAG", 1, False, 8),  # JR NC - not taken when C set
    (0x38, "CARRY_FLAG", 1, True, 12),  # JR C - jumps when C set
    (0x38, "CARRY_FLAG", 0, False, 8),  # JR C - not taken when C clear
])
def test_jr_conditional(cpu, mmu, opcode, flag, value, should_jump, expected_cycles):
    cpu.set_flag(getattr(cpu, flag), value)
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x05
    cycles = cpu.step()
    assert cpu.pc == (0x0107 if should_jump else 0x0102)
    assert cycles == expected_cycles


def test_call_pushes_return_address(cpu, mmu):
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xCD
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cycles = cpu.step()
    assert cpu.pc == 0xC000
    assert cpu.sp == 0xFFFC
    assert mmu.mem[0xFFFC] == 0x03
    assert mmu.mem[0xFFFD] == 0x01
    assert cycles == 24


@pytest.mark.parametrize("opcode,flag,value,should_call,expected_cycles", [
    (0xC4, "ZERO_FLAG", 0, True, 24),   # CALL NZ - calls when Z clear
    (0xC4, "ZERO_FLAG", 1, False, 12),  # CALL NZ - not called when Z set
    (0xCC, "ZERO_FLAG", 1, True, 24),   # CALL Z - calls when Z set
    (0xCC, "ZERO_FLAG", 0, False, 12),  # CALL Z - not called when Z clear
    (0xD4, "CARRY_FLAG", 0, True, 24),  # CALL NC - calls when C clear
    (0xD4, "CARRY_FLAG", 1, False, 12), # CALL NC - not called when C set
    (0xDC, "CARRY_FLAG", 1, True, 24),  # CALL C - calls when C set
    (0xDC, "CARRY_FLAG", 0, False, 12), # CALL C - not called when C clear
])
def test_call_conditional(cpu, mmu, opcode, flag, value, should_call, expected_cycles):
    cpu.set_flag(getattr(cpu, flag), value)
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cycles = cpu.step()
    assert cpu.pc == (0xC000 if should_call else 0x0103)
    if should_call:
        assert cpu.sp == 0xFFFC
        assert mmu.mem[0xFFFC] == 0x03
        assert mmu.mem[0xFFFD] == 0x01
    else:
        assert cpu.sp == 0xFFFE
    assert cycles == expected_cycles


def test_ret_pops_return_address(cpu, mmu):
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x03
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = 0xC9
    cycles = cpu.step()
    assert cpu.pc == 0x0103
    assert cpu.sp == 0xFFFE
    assert cycles == 16


@pytest.mark.parametrize("opcode,flag,value,should_return,expected_cycles", [
    (0xC0, "ZERO_FLAG", 0, True, 20),   # RET NZ - returns when Z clear
    (0xC0, "ZERO_FLAG", 1, False, 8),   # RET NZ - not returned when Z set
    (0xC8, "ZERO_FLAG", 1, True, 20),   # RET Z - returns when Z set
    (0xC8, "ZERO_FLAG", 0, False, 8),   # RET Z - not returned when Z clear
    (0xD0, "CARRY_FLAG", 0, True, 20),  # RET NC - returns when C clear
    (0xD0, "CARRY_FLAG", 1, False, 8),  # RET NC - not returned when C set
    (0xD8, "CARRY_FLAG", 1, True, 20),  # RET C - returns when C set
    (0xD8, "CARRY_FLAG", 0, False, 8),  # RET C - not returned when C clear
])
def test_ret_conditional(cpu, mmu, opcode, flag, value, should_return, expected_cycles):
    cpu.set_flag(getattr(cpu, flag), value)
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x03
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = opcode
    cycles = cpu.step()
    assert cpu.pc == (0x0103 if should_return else 0x0101)
    if should_return:
        assert cpu.sp == 0xFFFE
    else:
        assert cpu.sp == 0xFFFC
    assert cycles == expected_cycles


def test_reti_sets_ime(cpu, mmu):
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x00
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = 0xD9
    cpu.step()
    assert cpu.ime is True


def test_rst(cpu, mmu):
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xEF  # RST 0x28
    cpu.step()
    assert cpu.pc == 0x0028
    assert mmu.mem[0xFFFC] == 0x01
    assert mmu.mem[0xFFFD] == 0x01
