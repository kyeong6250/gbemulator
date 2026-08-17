# tests/test_cpu_interrupts.py
from gbemulator.core import interrupts


def test_serviced_interrupt_pushes_pc_and_jumps(cpu, mmu):
    cpu.pc = 0x0150
    cpu.sp = 0xFFFE
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)  # IE: all enabled
    interrupts.request(mmu, interrupts.VBLANK)
    cpu.step()
    assert cpu.pc == 0x0040
    assert cpu.sp == 0xFFFC
    assert mmu.read(0xFFFC) == 0x50
    assert mmu.read(0xFFFD) == 0x01


def test_servicing_clears_ime_and_if_bit(cpu, mmu):
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.TIMER)
    cpu.step()
    assert cpu.ime is False
    assert mmu.read(0xFF0F) & interrupts.TIMER == 0


def test_no_service_when_ime_false(cpu, mmu):
    cpu.pc = 0x0150
    mmu.mem[0x0150] = 0x00  # NOP, so a normal step still occurs
    cpu.ime = False
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.VBLANK)
    cpu.step()
    assert cpu.pc == 0x0151  # executed the NOP, did not jump to vector


def test_halted_cpu_wakes_on_pending_interrupt_even_if_ime_false(cpu, mmu):
    cpu.halted = True
    cpu.ime = False
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.JOYPAD)
    mmu.mem[cpu.pc] = 0x00  # Place NOP at PC so execution is deterministic
    cpu.step()
    assert cpu.halted is False
    # PC should not jump to interrupt vector (0x0048 is JOYPAD) since IME is false
    # Instead, it should have executed the instruction at PC, advancing by 1 (NOP)
    assert cpu.pc != 0x0048
    # IF bit for JOYPAD should still be set (interrupt not serviced, just halted cleared)
    assert mmu.read(0xFF0F) & interrupts.JOYPAD == interrupts.JOYPAD


def test_interrupt_service_costs_20_cycles(cpu, mmu):
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.VBLANK)
    cycles = cpu.step()
    assert cycles == 20


def test_interrupt_priority_highest_fires_first(cpu, mmu):
    """When multiple interrupts are pending, highest priority fires."""
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)  # All interrupts enabled
    # Request both TIMER (0x04) and LCD_STAT (0x02)
    # LCD_STAT has higher priority and should fire first
    interrupts.request(mmu, interrupts.TIMER)
    interrupts.request(mmu, interrupts.LCD_STAT)
    cpu.step()
    # Should jump to LCD_STAT vector (0x0048), not TIMER (0x0050)
    assert cpu.pc == 0x0048


def test_multiple_interrupts_clears_only_serviced_bit(cpu, mmu):
    """When multiple interrupts are pending, only the serviced one is cleared."""
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)  # All interrupts enabled
    # Request both VBLANK (0x01) and TIMER (0x04)
    interrupts.request(mmu, interrupts.VBLANK)
    interrupts.request(mmu, interrupts.TIMER)
    if_before = mmu.read(0xFF0F)
    assert if_before & interrupts.VBLANK
    assert if_before & interrupts.TIMER

    cpu.step()  # Should service VBLANK (higher priority)

    if_after = mmu.read(0xFF0F)
    # VBLANK bit should be cleared
    assert if_after & interrupts.VBLANK == 0
    # TIMER bit should still be set
    assert if_after & interrupts.TIMER
