VBLANK = 0x01
LCD_STAT = 0x02
TIMER = 0x04
SERIAL = 0x08
JOYPAD = 0x10

IF_ADDR = 0xFF0F
IE_ADDR = 0xFFFF

_ORDER = (VBLANK, LCD_STAT, TIMER, SERIAL, JOYPAD)
_VECTORS = {VBLANK: 0x0040, LCD_STAT: 0x0048, TIMER: 0x0050, SERIAL: 0x0058, JOYPAD: 0x0060}


def request(mmu, bit):
    mmu.write(IF_ADDR, mmu.read(IF_ADDR) | bit)


def pending_vector(mmu):
    pending = mmu.read(IF_ADDR) & mmu.read(IE_ADDR) & 0x1F
    if pending == 0:
        return None
    for bit in _ORDER:
        if pending & bit:
            return bit, _VECTORS[bit]
    return None


def clear(mmu, bit):
    mmu.write(IF_ADDR, mmu.read(IF_ADDR) & ~bit & 0xFF)
