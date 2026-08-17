from gbemulator.core.joypad import Joypad
from gbemulator.core import interrupts


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def test_default_read_no_buttons_pressed_returns_all_high():
    mmu = FakeMMU()
    joypad = Joypad(mmu)
    joypad.write(0x10)  # select action buttons (bit 5 low = select group 1; here we select group via write)
    assert joypad.read() & 0x0F == 0x0F


def test_select_dpad_reports_pressed_direction_as_low_bit():
    mmu = FakeMMU()
    joypad = Joypad(mmu)
    joypad.set_button("right", True)
    joypad.write(0x20)  # bit4=0 selects d-pad (P14), bit5=1 deselects buttons
    result = joypad.read()
    assert result & 0x01 == 0  # right pressed -> bit 0 low


def test_select_buttons_reports_pressed_action_as_low_bit():
    mmu = FakeMMU()
    joypad = Joypad(mmu)
    joypad.set_button("a", True)
    joypad.write(0x10)  # bit5=0 selects action buttons (P15), bit4=1 deselects d-pad
    result = joypad.read()
    assert result & 0x01 == 0  # A pressed -> bit 0 low


def test_button_press_requests_joypad_interrupt():
    mmu = FakeMMU()
    joypad = Joypad(mmu)
    joypad.write(0x10)
    joypad.set_button("a", True)
    assert mmu.read(0xFF0F) & interrupts.JOYPAD == interrupts.JOYPAD


def test_button_release_does_not_request_interrupt():
    mmu = FakeMMU()
    joypad = Joypad(mmu)
    joypad.write(0x10)
    joypad.set_button("a", True)
    mmu.mem[0xFF0F] = 0  # clear
    joypad.set_button("a", False)
    assert mmu.read(0xFF0F) & interrupts.JOYPAD == 0
