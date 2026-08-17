def test_nop_advances_pc_and_costs_4_cycles(cpu, mmu):
    mmu.mem[0x0100] = 0x00
    cycles = cpu.step()
    assert cpu.pc == 0x0101
    assert cycles == 4


def test_halt_sets_halted_flag(cpu, mmu):
    mmu.mem[0x0100] = 0x76
    cpu.step()
    assert cpu.halted is True


def test_halted_cpu_returns_4_cycles_without_fetching(cpu, mmu):
    cpu.halted = True
    mmu.mem[0x0100] = 0xFF  # would be an invalid opcode if fetched
    cycles = cpu.step()
    assert cycles == 4
    assert cpu.pc == 0x0100  # did not advance


def test_di_clears_ime_immediately(cpu, mmu):
    cpu.ime = True
    mmu.mem[0x0100] = 0xF3
    cpu.step()
    assert cpu.ime is False


def test_ei_sets_ime_after_next_instruction(cpu, mmu):
    mmu.mem[0x0100] = 0xFB  # EI
    mmu.mem[0x0101] = 0x00  # NOP
    cpu.step()
    assert cpu.ime is False  # not yet - takes effect after next instruction
    cpu.step()
    assert cpu.ime is True


def test_stop_advances_pc_by_2(cpu, mmu):
    mmu.mem[0x0100] = 0x10
    mmu.mem[0x0101] = 0x00
    cpu.step()
    assert cpu.pc == 0x0102
