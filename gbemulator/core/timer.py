from . import interrupts

DIV_ADDR = 0xFF04
TIMA_ADDR = 0xFF05
TMA_ADDR = 0xFF06
TAC_ADDR = 0xFF07

_TAC_THRESHOLDS = {0: 1024, 1: 16, 2: 64, 3: 256}


class Timer:
    def __init__(self, mmu):
        self.mmu = mmu
        self.div_counter = 0
        self.tima_counter = 0

    def reset_div(self):
        self.div_counter = 0
        self.mmu.mem[DIV_ADDR] = 0

    def tick(self, cycles):
        self.div_counter += cycles
        while self.div_counter >= 256:
            self.div_counter -= 256
            self.mmu.mem[DIV_ADDR] = (self.mmu.mem[DIV_ADDR] + 1) & 0xFF

        tac = self.mmu.mem[TAC_ADDR]
        if not (tac & 0x04):
            return
        threshold = _TAC_THRESHOLDS[tac & 0x03]
        self.tima_counter += cycles
        while self.tima_counter >= threshold:
            self.tima_counter -= threshold
            tima = self.mmu.mem[TIMA_ADDR] + 1
            if tima > 0xFF:
                self.mmu.mem[TIMA_ADDR] = self.mmu.mem[TMA_ADDR]
                interrupts.request(self.mmu, interrupts.TIMER)
            else:
                self.mmu.mem[TIMA_ADDR] = tima
