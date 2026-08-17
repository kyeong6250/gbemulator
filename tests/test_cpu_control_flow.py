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


@pytest.mark.parametrize("opcode,flag,value,should_jump", [
    (0xC2, "ZERO_FLAG", 0, True),   # JP NZ - jumps when Z clear
    (0xC2, "ZERO_FLAG", 1, False),
    (0xCA, "ZERO_FLAG", 1, True),   # JP Z - jumps when Z set
    (0xD2, "CARRY_FLAG", 0, True),  # JP NC
    (0xDA, "CARRY_FLAG", 1, True),  # JP C
])
def test_jp_conditional(cpu, mmu, opcode, flag, value, should_jump):
    cpu.set_flag(getattr(cpu, flag), value)
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == (0xC000 if should_jump else 0x0103)


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


def test_call_pushes_return_address(cpu, mmu):
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xCD
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == 0xC000
    assert cpu.sp == 0xFFFC
    assert mmu.mem[0xFFFC] == 0x03
    assert mmu.mem[0xFFFD] == 0x01


def test_ret_pops_return_address(cpu, mmu):
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x03
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = 0xC9
    cpu.step()
    assert cpu.pc == 0x0103
    assert cpu.sp == 0xFFFE


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
