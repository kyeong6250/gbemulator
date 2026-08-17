import pytest


def test_cb_rlc_sets_zero_flag_when_result_zero(cpu, mmu):
    cpu.b = 0x00
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x00  # RLC B
    cpu.step()
    assert cpu.b == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_cb_rlc_rotates_and_sets_carry(cpu, mmu):
    cpu.b = 0x85
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x00
    cpu.step()
    assert cpu.b == 0x0B
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cb_swap(cpu, mmu):
    cpu.a = 0xAB
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x37  # SWAP A
    cpu.step()
    assert cpu.a == 0xBA
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_cb_sla(cpu, mmu):
    cpu.c = 0x80
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x21  # SLA C
    cpu.step()
    assert cpu.c == 0x00
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_cb_sra_preserves_sign_bit(cpu, mmu):
    cpu.d = 0x81
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x2A  # SRA D
    cpu.step()
    assert cpu.d == 0xC0
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cb_srl_clears_bit7(cpu, mmu):
    cpu.e = 0x81
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x3B  # SRL E
    cpu.step()
    assert cpu.e == 0x40
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


@pytest.mark.parametrize("bit,value,expected_zero", [(7, 0x80, 0), (7, 0x00, 1), (0, 0x01, 0)])
def test_cb_bit(cpu, mmu, bit, value, expected_zero):
    cpu.h = value
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x40 | (bit << 3) | 4  # BIT bit,H
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_cb_res_clears_bit(cpu, mmu):
    cpu.l = 0xFF
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x80 | (3 << 3) | 5  # RES 3,L
    cpu.step()
    assert cpu.l == 0xF7


def test_cb_set_sets_bit(cpu, mmu):
    cpu.l = 0x00
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0xC0 | (3 << 3) | 5  # SET 3,L
    cpu.step()
    assert cpu.l == 0x08


def test_cb_bit_hl_indirect_costs_12_cycles(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x80
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x46  # BIT 0,(HL)
    cycles = cpu.step()
    assert cycles == 12


# Additional parametrized tests for comprehensive coverage

@pytest.mark.parametrize("reg_idx,reg_name,initial_value,expected_carry", [
    (0, 'b', 0x80, 1),
    (1, 'c', 0x40, 0),
    (2, 'd', 0x20, 0),
    (3, 'e', 0x10, 0),
    (4, 'h', 0x08, 0),
    (5, 'l', 0x04, 0),
    (7, 'a', 0x02, 0),
])
def test_cb_rlc_multiple_registers(cpu, mmu, reg_idx, reg_name, initial_value, expected_carry):
    """Test RLC across all registers"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x00 | reg_idx  # RLC r
    cpu.step()
    assert getattr(cpu, reg_name) == ((initial_value << 1) | (initial_value >> 7)) & 0xFF
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry


@pytest.mark.parametrize("reg_idx,reg_name,initial_value,expected_carry", [
    (0, 'b', 0x01, 1),
    (1, 'c', 0x02, 0),
    (2, 'd', 0x04, 0),
    (3, 'e', 0x08, 0),
    (4, 'h', 0x10, 0),
    (5, 'l', 0x20, 0),
    (7, 'a', 0x40, 0),
])
def test_cb_rrc_multiple_registers(cpu, mmu, reg_idx, reg_name, initial_value, expected_carry):
    """Test RRC across all registers"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x08 | reg_idx  # RRC r
    cpu.step()
    assert getattr(cpu, reg_name) == ((initial_value >> 1) | ((initial_value & 1) << 7)) & 0xFF
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry


@pytest.mark.parametrize("reg_idx,reg_name,initial_value", [
    (0, 'b', 0xFF),
    (1, 'c', 0x7F),
    (2, 'd', 0x55),
    (7, 'a', 0xAA),
])
def test_cb_sla_multiple_registers(cpu, mmu, reg_idx, reg_name, initial_value):
    """Test SLA across multiple registers"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x20 | reg_idx  # SLA r
    cpu.step()
    expected_carry = (initial_value >> 7) & 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry
    expected_result = (initial_value << 1) & 0xFF
    assert getattr(cpu, reg_name) == expected_result


@pytest.mark.parametrize("reg_idx,reg_name,initial_value", [
    (0, 'b', 0x80),
    (1, 'c', 0xFF),
    (2, 'd', 0x42),
    (7, 'a', 0x01),
])
def test_cb_srl_multiple_registers(cpu, mmu, reg_idx, reg_name, initial_value):
    """Test SRL across multiple registers"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x38 | reg_idx  # SRL r
    cpu.step()
    expected_carry = initial_value & 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry
    expected_result = initial_value >> 1
    assert getattr(cpu, reg_name) == expected_result


@pytest.mark.parametrize("reg_idx,reg_name", [
    (0, 'b'),
    (1, 'c'),
    (2, 'd'),
    (3, 'e'),
    (4, 'h'),
    (5, 'l'),
    (7, 'a'),
])
def test_cb_swap_multiple_registers(cpu, mmu, reg_idx, reg_name):
    """Test SWAP across all registers"""
    setattr(cpu, reg_name, 0xF0)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x30 | reg_idx  # SWAP r
    cpu.step()
    assert getattr(cpu, reg_name) == 0x0F
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


@pytest.mark.parametrize("reg_idx,reg_name,bit_idx,initial_value,expected_zero", [
    (0, 'b', 0, 0x01, 0),  # b, bit 0, set
    (0, 'b', 0, 0xFE, 1),  # b, bit 0, clear
    (1, 'c', 7, 0x80, 0),  # c, bit 7, set
    (1, 'c', 7, 0x7F, 1),  # c, bit 7, clear
    (2, 'd', 3, 0x08, 0),  # d, bit 3, set
    (7, 'a', 4, 0x10, 0),  # a, bit 4, set
])
def test_cb_bit_multiple_registers(cpu, mmu, reg_idx, reg_name, bit_idx, initial_value, expected_zero):
    """Test BIT across multiple registers and bit indices"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x40 | (bit_idx << 3) | reg_idx  # BIT bit,r
    cycles = cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cycles == 8  # Register operand costs 8


@pytest.mark.parametrize("bit_idx,initial_value,expected_zero", [
    (0, 0x01, 0),
    (0, 0xFE, 1),
    (7, 0x80, 0),
    (7, 0x7F, 1),
    (3, 0x08, 0),
])
def test_cb_bit_hl_indirect_multiple_bits(cpu, mmu, bit_idx, initial_value, expected_zero):
    """Test BIT (HL) with multiple bit indices"""
    cpu.hl = 0xC000
    mmu.mem[0xC000] = initial_value
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x40 | (bit_idx << 3) | 6  # BIT bit,(HL)
    cycles = cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cycles == 12  # (HL) operand costs 12


@pytest.mark.parametrize("reg_idx,reg_name,bit_idx,initial_value,expected_result", [
    (0, 'b', 0, 0xFF, 0xFE),
    (1, 'c', 7, 0x80, 0x00),
    (2, 'd', 3, 0x0F, 0x07),
    (7, 'a', 4, 0xFF, 0xEF),
])
def test_cb_res_multiple_registers(cpu, mmu, reg_idx, reg_name, bit_idx, initial_value, expected_result):
    """Test RES across multiple registers and bit indices"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x80 | (bit_idx << 3) | reg_idx  # RES bit,r
    cpu.step()
    assert getattr(cpu, reg_name) == expected_result


@pytest.mark.parametrize("reg_idx,reg_name,bit_idx,initial_value,expected_result", [
    (0, 'b', 0, 0x00, 0x01),
    (1, 'c', 7, 0x00, 0x80),
    (2, 'd', 3, 0x00, 0x08),
    (7, 'a', 4, 0x00, 0x10),
])
def test_cb_set_multiple_registers(cpu, mmu, reg_idx, reg_name, bit_idx, initial_value, expected_result):
    """Test SET across multiple registers and bit indices"""
    setattr(cpu, reg_name, initial_value)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0xC0 | (bit_idx << 3) | reg_idx  # SET bit,r
    cpu.step()
    assert getattr(cpu, reg_name) == expected_result


@pytest.mark.parametrize("reg_idx,reg_name,initial_value,carry_in,expected_value,expected_carry,expected_zero", [
    # RL B tests: carry enters bit 0, bit 7 exits to carry
    (0, 'b', 0x80, 1, 0x01, 1, 0),  # bit 7 set, carry in → result 0x01, carry out
    (0, 'b', 0x40, 0, 0x80, 0, 0),  # bit 7 clear, no carry in → result 0x80, no carry
    (0, 'b', 0x00, 0, 0x00, 0, 1),  # all zeros → result 0x00, no carry, ZERO=1
    # RL C tests
    (1, 'c', 0x81, 1, 0x03, 1, 0),  # 0x81 with carry=1 → 0x03, carry=1
    (1, 'c', 0x7F, 1, 0xFF, 0, 0),  # 0x7F with carry=1 → 0xFF, carry=0
    # RL D tests
    (2, 'd', 0xAA, 0, 0x54, 1, 0),  # 0xAA (10101010) with carry=0 → 0x54 (01010100), carry=1
])
def test_cb_rl_rotate_through_carry(cpu, mmu, reg_idx, reg_name, initial_value, carry_in, expected_value, expected_carry, expected_zero):
    """Test RL (rotate left through carry) - CB opcodes 0x10-0x17"""
    setattr(cpu, reg_name, initial_value)
    cpu.set_flag(cpu.CARRY_FLAG, carry_in)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x10 | reg_idx  # RL r (0x10-0x17)
    cycles = cpu.step()
    assert getattr(cpu, reg_name) == expected_value
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cycles == 8  # Register operand costs 8


@pytest.mark.parametrize("reg_idx,reg_name,initial_value,carry_in,expected_value,expected_carry,expected_zero", [
    # RR B tests: carry enters bit 7, bit 0 exits to carry
    (0, 'b', 0x01, 1, 0x80, 1, 0),  # bit 0 set, carry in → result 0x80, carry out
    (0, 'b', 0x02, 0, 0x01, 0, 0),  # bit 0 clear, no carry in → result 0x01, no carry
    (0, 'b', 0x00, 0, 0x00, 0, 1),  # all zeros → result 0x00, no carry, ZERO=1
    # RR C tests
    (1, 'c', 0x80, 1, 0xC0, 0, 0),  # 0x80 with carry=1 → 0xC0, carry=0
    (1, 'c', 0xFF, 0, 0x7F, 1, 0),  # 0xFF with carry=0 → 0x7F, carry=1
    # RR D tests
    (2, 'd', 0x55, 1, 0xAA, 1, 0),  # 0x55 (01010101) with carry=1 → 0xAA (10101010), carry=1
])
def test_cb_rr_rotate_through_carry(cpu, mmu, reg_idx, reg_name, initial_value, carry_in, expected_value, expected_carry, expected_zero):
    """Test RR (rotate right through carry) - CB opcodes 0x18-0x1F"""
    setattr(cpu, reg_name, initial_value)
    cpu.set_flag(cpu.CARRY_FLAG, carry_in)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x18 | reg_idx  # RR r (0x18-0x1F)
    cycles = cpu.step()
    assert getattr(cpu, reg_name) == expected_value
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cycles == 8  # Register operand costs 8


@pytest.mark.parametrize("bit_idx,initial_value,carry_before,expected_carry", [
    # Test that BIT leaves CARRY_FLAG untouched in both directions
    (0, 0x01, 1, 1),   # carry=1 before, should be 1 after
    (0, 0x01, 0, 0),   # carry=0 before, should be 0 after
    (7, 0x80, 1, 1),   # carry=1 before, should be 1 after
    (7, 0x80, 0, 0),   # carry=0 before, should be 0 after
    (3, 0x08, 1, 1),   # carry=1 before, should be 1 after
    (3, 0x08, 0, 0),   # carry=0 before, should be 0 after
])
def test_cb_bit_preserves_carry_flag(cpu, mmu, bit_idx, initial_value, carry_before, expected_carry):
    """Test that BIT instruction leaves CARRY_FLAG untouched"""
    cpu.h = initial_value
    cpu.set_flag(cpu.CARRY_FLAG, carry_before)
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x40 | (bit_idx << 3) | 4  # BIT bit,H
    cpu.step()
    # CARRY_FLAG should be unchanged
    assert cpu.get_flag(cpu.CARRY_FLAG) == expected_carry


@pytest.mark.parametrize("cycle_count,op_group,is_hl", [
    (16, 0, True),   # rotate/shift on (HL) = 16 cycles
    (8, 0, False),   # rotate/shift on register = 8 cycles
    (12, 1, True),   # BIT on (HL) = 12 cycles
    (8, 1, False),   # BIT on register = 8 cycles
    (16, 2, True),   # RES on (HL) = 16 cycles
    (8, 2, False),   # RES on register = 8 cycles
    (16, 3, True),   # SET on (HL) = 16 cycles
    (8, 3, False),   # SET on register = 8 cycles
])
def test_cb_cycle_counts(cpu, mmu, cycle_count, op_group, is_hl):
    """Test CB operation cycle counts for register vs (HL) operands"""
    if is_hl:
        cpu.hl = 0xC000
        mmu.mem[0xC000] = 0xFF
        reg_idx = 6  # (HL)
    else:
        cpu.b = 0xFF
        reg_idx = 0  # B

    mmu.mem[0x0100] = 0xCB
    # Encode: op_group (bits 6-7), bit 0 (bits 3-5), register (bits 0-2)
    mmu.mem[0x0101] = ((op_group & 0x03) << 6) | (0 << 3) | reg_idx
    cycles = cpu.step()
    assert cycles == cycle_count
