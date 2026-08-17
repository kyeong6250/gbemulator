from .cartridge import Cartridge
from .mmu import MMU
from .cpu import CPU
from .ppu import PPU
from .timer import Timer
from .joypad import Joypad


class GameBoy:
    def __init__(self, rom_path):
        with open(rom_path, "rb") as f:
            rom_bytes = f.read()
        self.cartridge = Cartridge(rom_bytes)
        self.mmu = MMU(self.cartridge)
        self.cpu = CPU(self.mmu)
        self.ppu = PPU(self.mmu)
        self.timer = Timer(self.mmu)
        self.joypad = Joypad(self.mmu)
        self.mmu.timer = self.timer
        self.mmu.joypad = self.joypad

    def run_frame(self):
        self.ppu.frame_ready = False
        while not self.ppu.frame_ready:
            cycles = self.cpu.step()
            self.ppu.tick(cycles)
            self.timer.tick(cycles)
        self.ppu.frame_ready = False
        return self.ppu.framebuffer
