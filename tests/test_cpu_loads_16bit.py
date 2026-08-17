import pytest


@pytest.mark.parametrize("opcode,attr", [(0x01, "bc"), (0x11, "de"), (0x21, "hl")])
def test_ld_rr_d16(cpu, mmu, opcode, attr):
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x34
    mmu.mem[0x0102] = 0x12
    cpu.step()
    assert getattr(cpu, attr) == 0x1234


def test_ld_sp_d16(cpu, mmu):
    mmu.mem[0x0100] = 0x31
    mmu.mem[0x0101] = 0xFE
    mmu.mem[0x0102] = 0xFF
    cpu.step()
    assert cpu.sp == 0xFFFE


def test_ld_a16_sp(cpu, mmu):
    cpu.sp = 0xABCD
    mmu.mem[0x0100] = 0x08
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC1
    cpu.step()
    assert mmu.mem[0xC100] == 0xCD
    assert mmu.mem[0xC101] == 0xAB


def test_ld_sp_hl(cpu, mmu):
    cpu.hl = 0x9988
    mmu.mem[0x0100] = 0xF9
    cpu.step()
    assert cpu.sp == 0x9988


def test_ld_hl_sp_plus_positive_offset(cpu, mmu):
    cpu.sp = 0xC000
    mmu.mem[0x0100] = 0xF8
    mmu.mem[0x0101] = 0x02
    cpu.step()
    assert cpu.hl == 0xC002
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_ld_hl_sp_plus_negative_offset(cpu, mmu):
    cpu.sp = 0xC005
    mmu.mem[0x0100] = 0xF8
    mmu.mem[0x0101] = 0xFE  # -2
    cpu.step()
    assert cpu.hl == 0xC003


@pytest.mark.parametrize("push_op,pop_op,attr", [
    (0xC5, 0xC1, "bc"), (0xD5, 0xD1, "de"), (0xE5, 0xE1, "hl"),
])
def test_push_pop_roundtrip(cpu, mmu, push_op, pop_op, attr):
    setattr(cpu, attr, 0x1357)
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = push_op
    cpu.step()
    assert cpu.sp == 0xFFFC
    setattr(cpu, attr, 0x0000)
    mmu.mem[0x0101] = pop_op
    cpu.step()
    assert getattr(cpu, attr) == 0x1357
    assert cpu.sp == 0xFFFE


def test_push_pop_af_masks_low_nibble(cpu, mmu):
    cpu.af = 0x12FF
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xF5  # PUSH AF
    mmu.mem[0x0101] = 0xF1  # POP AF
    cpu.step()
    cpu.step()
    assert cpu.af == 0x12F0
