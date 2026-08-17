def test_rlca_rotates_left_through_bit7_to_carry(cpu, mmu):
    cpu.a = 0x85  # 1000_0101
    mmu.mem[0x0100] = 0x07
    cpu.step()
    assert cpu.a == 0x0B  # 0000_1011
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0  # RLCA always clears Z


def test_rrca_rotates_right_through_bit0_to_carry(cpu, mmu):
    cpu.a = 0x01
    mmu.mem[0x0100] = 0x0F
    cpu.step()
    assert cpu.a == 0x80
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_rla_rotates_through_existing_carry(cpu, mmu):
    cpu.a = 0x80
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x17
    cpu.step()
    assert cpu.a == 0x01
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_rra_rotates_through_existing_carry(cpu, mmu):
    cpu.a = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x1F
    cpu.step()
    assert cpu.a == 0x80
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cpl_inverts_a_and_sets_flags(cpu, mmu):
    cpu.a = 0x0F
    mmu.mem[0x0100] = 0x2F
    cpu.step()
    assert cpu.a == 0xF0
    assert cpu.get_flag(cpu.SUB_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_scf_sets_carry_clears_n_h(cpu, mmu):
    mmu.mem[0x0100] = 0x37
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 0


def test_ccf_flips_carry(cpu, mmu):
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x3F
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_daa_after_addition_adjusts_to_valid_bcd(cpu, mmu):
    # 0x45 + 0x38 = 0x7D in binary, should become 0x83 in BCD
    cpu.a = 0x45
    cpu.b = 0x38
    mmu.mem[0x0100] = 0x80  # ADD A,B
    mmu.mem[0x0101] = 0x27  # DAA
    cpu.step()
    cpu.step()
    assert cpu.a == 0x83


def test_daa_after_subtraction_adjusts_result(cpu, mmu):
    # Simulates 0x00 - 0x01 = 0xFF (borrow occurred)
    # After SUB instruction: A=0xFF, N=1, H=1, C=1
    # DAA should subtract 0x66: 0xFF - 0x66 = 0x99
    cpu.a = 0xFF
    cpu.set_flag(cpu.SUB_FLAG, True)
    cpu.set_flag(cpu.HALF_CARRY_FLAG, True)
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x27  # DAA
    cpu.step()
    assert cpu.a == 0x99
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1  # Carry preserved from SUB
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 0  # DAA always clears H


def test_daa_a_alone_exceeds_0x99_addition_path(cpu, mmu):
    # When A = 0xA5 and no half-carry/carry set, DAA should add 0x60
    # because upper nibble (A) > 9. 0xA5 + 0x60 = 0x165, masked = 0x05
    # Carry flag is set because result exceeded 0xFF
    cpu.a = 0xA5
    # Ensure all flags are clear (should be default)
    cpu.set_flag(cpu.SUB_FLAG, False)
    cpu.set_flag(cpu.HALF_CARRY_FLAG, False)
    cpu.set_flag(cpu.CARRY_FLAG, False)
    mmu.mem[0x0100] = 0x27  # DAA
    cpu.step()
    assert cpu.a == 0x05
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1  # Set because A alone exceeded 0x99
