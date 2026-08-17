# tests/test_cpu_skeleton.py
import pytest


def test_initial_register_state(cpu):
    assert cpu.pc == 0x0100
    assert cpu.sp == 0xFFFE


def test_bc_de_hl_af_composite_registers(cpu):
    cpu.b, cpu.c = 0x12, 0x34
    assert cpu.bc == 0x1234
    cpu.hl = 0xBEEF
    assert cpu.h == 0xBE and cpu.l == 0xEF
    cpu.a, cpu.f = 0xAB, 0xF0
    assert cpu.af == 0xABF0


def test_fetch8_advances_pc(cpu, mmu):
    mmu.mem[0x0100] = 0x99
    value = cpu.fetch8()
    assert value == 0x99
    assert cpu.pc == 0x0101


def test_fetch16_little_endian(cpu, mmu):
    mmu.mem[0x0100] = 0x34
    mmu.mem[0x0101] = 0x12
    assert cpu.fetch16() == 0x1234
    assert cpu.pc == 0x0102


def test_set_and_get_flag(cpu):
    cpu.set_flag(cpu.ZERO_FLAG, True)
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    cpu.set_flag(cpu.ZERO_FLAG, False)
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0


def test_step_dispatches_to_execute(cpu, mmu):
    mmu.mem[0x0100] = 0x07  # RLCA - not yet implemented
    with pytest.raises(NotImplementedError):
        cpu.step()


def test_unknown_opcode_raises(cpu, mmu):
    mmu.mem[0x0100] = 0xFC  # never a valid unprefixed opcode
    with pytest.raises(NotImplementedError):
        cpu.step()
