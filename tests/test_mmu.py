from gbemulator.core.mmu import MMU


class FakeCartridge:
    def __init__(self):
        self.store = {}

    def read(self, addr):
        return self.store.get(addr, 0xFF)

    def write(self, addr, value):
        self.store[addr] = value


def test_reads_writes_wram_directly():
    mmu = MMU(FakeCartridge())
    mmu.write(0xC000, 0x42)
    assert mmu.read(0xC000) == 0x42


def test_rom_range_delegates_to_cartridge():
    cart = FakeCartridge()
    mmu = MMU(cart)
    mmu.write(0x2000, 0x05)  # e.g. MBC bank-select write
    assert cart.store[0x2000] == 0x05
    cart.store[0x0100] = 0xAB
    assert mmu.read(0x0100) == 0xAB


def test_cart_ram_range_delegates_to_cartridge():
    cart = FakeCartridge()
    mmu = MMU(cart)
    mmu.write(0xA000, 0x77)
    assert cart.store[0xA000] == 0x77


def test_joypad_none_reads_mem_directly():
    mmu = MMU(FakeCartridge())
    mmu.mem[0xFF00] = 0xCF
    assert mmu.read(0xFF00) == 0xCF


def test_joypad_delegate_used_when_present():
    class FakeJoypad:
        def read(self):
            return 0x0F

        def write(self, value):
            self.written = value

    mmu = MMU(FakeCartridge())
    mmu.joypad = FakeJoypad()
    assert mmu.read(0xFF00) == 0x0F
    mmu.write(0xFF00, 0x20)
    assert mmu.joypad.written == 0x20


def test_serial_output_captured_on_0x81_write():
    mmu = MMU(FakeCartridge())
    mmu.write(0xFF01, ord("A"))
    mmu.write(0xFF02, 0x81)
    assert mmu.serial_output == [ord("A")]
