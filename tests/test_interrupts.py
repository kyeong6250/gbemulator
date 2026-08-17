from gbemulator.core import interrupts


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def test_request_sets_if_bit():
    mmu = FakeMMU()
    interrupts.request(mmu, interrupts.TIMER)
    assert mmu.read(0xFF0F) == interrupts.TIMER


def test_pending_vector_none_when_nothing_enabled():
    mmu = FakeMMU()
    interrupts.request(mmu, interrupts.VBLANK)
    mmu.write(0xFFFF, 0x00)  # IE all disabled
    assert interrupts.pending_vector(mmu) is None


def test_pending_vector_priority_order():
    mmu = FakeMMU()
    mmu.write(0xFFFF, 0xFF)  # all enabled
    interrupts.request(mmu, interrupts.TIMER)
    interrupts.request(mmu, interrupts.VBLANK)
    assert interrupts.pending_vector(mmu) == (interrupts.VBLANK, 0x0040)


def test_clear_removes_bit():
    mmu = FakeMMU()
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.VBLANK)
    interrupts.clear(mmu, interrupts.VBLANK)
    assert interrupts.pending_vector(mmu) is None
