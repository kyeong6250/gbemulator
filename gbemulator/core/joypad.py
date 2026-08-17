from . import interrupts

_DPAD_BITS = {"right": 0x01, "left": 0x02, "up": 0x04, "down": 0x08}
_ACTION_BITS = {"a": 0x01, "b": 0x02, "select": 0x04, "start": 0x08}


class Joypad:
    def __init__(self, mmu):
        self.mmu = mmu
        self.select_bits = 0x30  # neither group selected
        self.dpad_state = 0x0F   # all released (active-low)
        self.action_state = 0x0F

    def set_button(self, name, pressed):
        if name in _DPAD_BITS:
            bit = _DPAD_BITS[name]
            was_pressed = (self.dpad_state & bit) == 0
            if pressed:
                self.dpad_state &= ~bit & 0xFF
            else:
                self.dpad_state |= bit
        else:
            bit = _ACTION_BITS[name]
            was_pressed = (self.action_state & bit) == 0
            if pressed:
                self.action_state &= ~bit & 0xFF
            else:
                self.action_state |= bit
        if pressed and not was_pressed:
            interrupts.request(self.mmu, interrupts.JOYPAD)

    def write(self, value):
        self.select_bits = value & 0x30

    def read(self):
        result = self.select_bits | 0xC0
        if not (self.select_bits & 0x10):
            result |= self.dpad_state
        elif not (self.select_bits & 0x20):
            result |= self.action_state
        else:
            result |= 0x0F
        return result
