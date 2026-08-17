import os
import pytest

from gbemulator.core.gameboy import GameBoy

ROM_PATH = os.path.join(os.path.dirname(__file__), "..", "roms", "blargg", "cpu_instrs.gb")


@pytest.mark.skipif(not os.path.exists(ROM_PATH), reason="cpu_instrs.gb not present, see roms/blargg/README.md")
def test_blargg_cpu_instrs_passes():
    gb = GameBoy(ROM_PATH)
    max_cycles = 200_000_000  # generous ceiling; the real ROM finishes well under this
    cycles_run = 0
    output = ""
    while cycles_run < max_cycles:
        cycles = gb.cpu.step()
        gb.ppu.tick(cycles)
        gb.timer.tick(cycles)
        cycles_run += cycles
        if gb.mmu.serial_output:
            output = bytes(gb.mmu.serial_output).decode("ascii", errors="ignore")
            if "Passed" in output or "Failed" in output:
                break
    assert "Passed" in output, f"cpu_instrs did not pass. Serial output:\n{output}"
