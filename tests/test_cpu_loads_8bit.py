# tests/test_cpu_loads_8bit.py
import itertools
import pytest


R8_ATTR = {0: "b", 1: "c", 2: "d", 3: "e", 4: "h", 5: "l", 7: "a"}


@pytest.mark.parametrize("dst,src", [
    (d, s) for d, s in itertools.product(range(8), repeat=2) if (d, s) != (6, 6)
])
def test_ld_r_r(cpu, mmu, dst, src):
    opcode = 0x40 | (dst << 3) | src
    mmu.mem[0x0100] = opcode
    if src == 6:
        cpu.hl = 0xC000
        mmu.mem[0xC000] = 0x77
    elif src != dst:
        setattr(cpu, R8_ATTR[src], 0x77)
    else:
        setattr(cpu, R8_ATTR[src], 0x77)

    cpu.step()

    if dst == 6:
        assert mmu.mem[cpu.hl] == 0x77 if src != 6 else True
    else:
        assert getattr(cpu, R8_ATTR[dst]) == 0x77


@pytest.mark.parametrize("opcode,attr", [
    (0x06, "b"), (0x0E, "c"), (0x16, "d"), (0x1E, "e"),
    (0x26, "h"), (0x2E, "l"), (0x3E, "a"),
])
def test_ld_r_d8(cpu, mmu, opcode, attr):
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x99
    cpu.step()
    assert getattr(cpu, attr) == 0x99
    assert cpu.pc == 0x0102


def test_ld_hl_d8(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0x0100] = 0x36
    mmu.mem[0x0101] = 0x55
    cpu.step()
    assert mmu.mem[0xC000] == 0x55


def test_ld_a_bc_indirect(cpu, mmu):
    cpu.bc = 0xC001
    mmu.mem[0xC001] = 0x42
    mmu.mem[0x0100] = 0x0A
    cpu.step()
    assert cpu.a == 0x42


def test_ld_bc_indirect_a(cpu, mmu):
    cpu.bc = 0xC002
    cpu.a = 0x33
    mmu.mem[0x0100] = 0x02
    cpu.step()
    assert mmu.mem[0xC002] == 0x33


def test_ld_a_hl_plus_increments_hl(cpu, mmu):
    cpu.hl = 0xC003
    mmu.mem[0xC003] = 0x11
    mmu.mem[0x0100] = 0x2A
    cpu.step()
    assert cpu.a == 0x11
    assert cpu.hl == 0xC004


def test_ld_hl_minus_a_decrements_hl(cpu, mmu):
    cpu.hl = 0xC004
    cpu.a = 0x22
    mmu.mem[0x0100] = 0x32
    cpu.step()
    assert mmu.mem[0xC004] == 0x22
    assert cpu.hl == 0xC003


def test_ldh_a8_a(cpu, mmu):
    cpu.a = 0x5A
    mmu.mem[0x0100] = 0xE0
    mmu.mem[0x0101] = 0x80
    cpu.step()
    assert mmu.mem[0xFF80] == 0x5A


def test_ldh_a_a8(cpu, mmu):
    mmu.mem[0xFF81] = 0x66
    mmu.mem[0x0100] = 0xF0
    mmu.mem[0x0101] = 0x81
    cpu.step()
    assert cpu.a == 0x66


def test_ld_c_indirect_a(cpu, mmu):
    cpu.c = 0x82
    cpu.a = 0x11
    mmu.mem[0x0100] = 0xE2
    cpu.step()
    assert mmu.mem[0xFF82] == 0x11


def test_ld_a16_a(cpu, mmu):
    cpu.a = 0x9A
    mmu.mem[0x0100] = 0xEA
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC1
    cpu.step()
    assert mmu.mem[0xC100] == 0x9A
