from gbemulator.core.mmu import MMU
from gbemulator.core.timer import Timer
from gbemulator.core import interrupts


class FakeCartridge:
    def read(self, addr): return 0xFF
    def write(self, addr, value): pass


def _make_mmu_with_timer():
    mmu = MMU(FakeCartridge())
    timer = Timer(mmu)
    mmu.timer = timer
    return mmu, timer


def test_div_increments_every_256_cycles():
    mmu, timer = _make_mmu_with_timer()
    timer.tick(256)
    assert mmu.mem[0xFF04] == 1


def test_writing_div_resets_it():
    mmu, timer = _make_mmu_with_timer()
    timer.tick(256)
    mmu.write(0xFF04, 0x99)  # any value resets DIV to 0
    assert mmu.mem[0xFF04] == 0


def test_tima_disabled_by_default():
    mmu, timer = _make_mmu_with_timer()
    mmu.mem[0xFF07] = 0x00  # TAC disabled
    timer.tick(1024)
    assert mmu.mem[0xFF05] == 0


def test_tima_increments_at_selected_rate():
    mmu, timer = _make_mmu_with_timer()
    mmu.mem[0xFF07] = 0x05  # enabled, select 01 = every 16 cycles
    timer.tick(16)
    assert mmu.mem[0xFF05] == 1


def test_tima_overflow_reloads_tma_and_requests_interrupt():
    mmu, timer = _make_mmu_with_timer()
    mmu.write(0xFFFF, 0xFF)
    mmu.mem[0xFF06] = 0x50  # TMA
    mmu.mem[0xFF05] = 0xFF  # TIMA about to overflow
    mmu.mem[0xFF07] = 0x05  # enabled, every 16 cycles
    timer.tick(16)
    assert mmu.mem[0xFF05] == 0x50
    assert mmu.read(0xFF0F) & interrupts.TIMER == interrupts.TIMER
