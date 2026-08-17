# Game Boy Emulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python Game Boy (DMG) emulator that boots ROM-only and MBC1 cartridges, renders background/window/sprites via pygame, and passes Blargg's `cpu_instrs` test ROM.

**Architecture:** A pure emulation `core/` package (CPU, MMU, PPU, Timer, Joypad, Cartridge/MBC — zero I/O dependencies, fully unit-testable) driven by a `GameBoy` orchestrator whose `run_frame()` steps the CPU and advances PPU/Timer by elapsed cycles until a frame completes. A thin pygame `frontend/` displays frames and forwards key events. Instruction-stepped timing (not full T-state cycle accuracy).

**Tech Stack:** Python 3.11+, pygame-ce (window/input — drop-in `import pygame` compatible fork, used because it ships prebuilt wheels for newer CPython faster than upstream pygame), numpy (framebuffer), pytest (testing).

**Spec:** `docs/superpowers/specs/2026-08-17-gameboy-emulator-design.md`

## Global Constraints

- Python 3.11+; dependencies limited to pygame-ce (imported as `pygame`), numpy, pytest (see spec Testing/Architecture sections).
- Timing model is instruction-stepped: CPU `step()` returns T-cycles consumed; PPU/Timer advance by that count. No per-T-state interleaving.
- Cartridge support limited to ROM-only (NoMBC) and MBC1 for v1 — other mappers raise a clear error at load time.
- No sound/APU, no CGB features, no save states/debugger in v1 (spec "Out of scope").
- No copyrighted commercial ROMs committed to the repository; only Blargg test ROMs and public-domain/homebrew ROMs.
- `core/` must have zero pygame dependency so unit/integration tests run headless.
- Unknown/unimplemented opcode or unsupported cartridge type raises immediately (fail loud), per spec's Error Handling section.

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `gbemulator/__init__.py`
- Create: `gbemulator/core/__init__.py`
- Create: `gbemulator/frontend/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Modify: `README.md`

**Interfaces:**
- Produces: installable package layout `gbemulator/core/*`, `gbemulator/frontend/*`; `pytest` runnable from repo root.

- [ ] **Step 1: Create directory structure and empty package files**

```bash
mkdir -p gbemulator/core gbemulator/frontend tests roms/blargg
touch gbemulator/__init__.py gbemulator/core/__init__.py gbemulator/frontend/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
pygame-ce>=2.5
numpy>=1.26
pytest>=8.0
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
roms/*.gb
roms/*.gbc
!roms/blargg/
```

- [ ] **Step 5: Write a smoke test**

```python
# tests/test_smoke.py
def test_smoke():
    assert True
```

- [ ] **Step 6: Install dependencies and run the smoke test**

```bash
pip install -r requirements.txt
pytest tests/test_smoke.py -v
```

Expected: `1 passed`.

- [ ] **Step 7: Update README.md**

Replace the placeholder README content with:

```markdown
# gbemulator

A Game Boy (DMG) emulator written in Python, inspired by [geaz/emu-gameboy](https://github.com/geaz/emu-gameboy).

## Setup

    pip install -r requirements.txt

## Run

    python -m gbemulator.frontend.pygame_app path/to/rom.gb

## Test

    pytest
```

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pytest.ini .gitignore gbemulator tests README.md roms
git commit -m "chore: project scaffolding"
```

---

### Task 2: Cartridge header parsing

**Files:**
- Create: `gbemulator/core/cartridge.py`
- Test: `tests/test_cartridge.py`

**Interfaces:**
- Consumes: nothing (first core module).
- Produces: `Cartridge(rom_bytes)` with attributes `.title` (str), `.cart_type` (int), `.rom_size` (int), `.ram_size` (int), `.rom` (bytes), and `.read(addr)`/`.write(addr, value)` that delegate to `.mbc`. `Cartridge._make_mbc()` raises `ValueError` for unsupported cart types. Depended on by Task 3 (MBC classes) and Task 5 (MMU).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cartridge.py
import pytest
from gbemulator.core.cartridge import Cartridge


def _make_rom(cart_type=0x00, rom_size_code=0x00, ram_size_code=0x00, title=b"TESTROM"):
    rom = bytearray(32 * 1024)
    rom[0x134:0x134 + len(title)] = title
    rom[0x147] = cart_type
    rom[0x148] = rom_size_code
    rom[0x149] = ram_size_code
    return bytes(rom)


def test_parses_title():
    cart = Cartridge(_make_rom(title=b"ZELDA"))
    assert cart.title == "ZELDA"


def test_parses_rom_and_ram_size():
    cart = Cartridge(_make_rom(rom_size_code=0x01, ram_size_code=0x02))
    assert cart.rom_size == 64 * 1024
    assert cart.ram_size == 8 * 1024


def test_unsupported_cart_type_raises():
    with pytest.raises(ValueError):
        Cartridge(_make_rom(cart_type=0x1B))  # MBC5, unsupported in v1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cartridge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.cartridge'`

- [ ] **Step 3: Write minimal implementation**

```python
# gbemulator/core/cartridge.py
_RAM_SIZES = {0: 0, 1: 2 * 1024, 2: 8 * 1024, 3: 32 * 1024, 4: 128 * 1024, 5: 64 * 1024}


class Cartridge:
    def __init__(self, rom_bytes):
        self.rom = rom_bytes
        self.title = rom_bytes[0x134:0x144].split(b"\x00")[0].decode("ascii", errors="ignore")
        self.cart_type = rom_bytes[0x147]
        self.rom_size = 32 * 1024 * (1 << rom_bytes[0x148])
        self.ram_size = _RAM_SIZES.get(rom_bytes[0x149], 0)
        self.mbc = self._make_mbc()

    def _make_mbc(self):
        from .mbc import NoMBC, MBC1
        if self.cart_type == 0x00:
            return NoMBC(self)
        if self.cart_type in (0x01, 0x02, 0x03):
            return MBC1(self)
        raise ValueError(f"Unsupported cartridge type: {self.cart_type:#04x}")

    def read(self, addr):
        return self.mbc.read(addr)

    def write(self, addr, value):
        self.mbc.write(addr, value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cartridge.py -v`
Expected: FAIL still — `mbc.py` doesn't exist yet (import inside `_make_mbc` fails on the passing-case tests). This is expected; Task 3 creates it. For now, verify only the error-raising test passes in isolation:

Run: `pytest tests/test_cartridge.py::test_unsupported_cart_type_raises -v`
Expected: PASS (it raises before reaching the `NoMBC`/`MBC1` import path... actually the import happens unconditionally at the top of `_make_mbc`, so this will also fail). Adjust: move the `from .mbc import ...` inside each branch so the unsupported-type test doesn't require `mbc.py` to exist:

```python
    def _make_mbc(self):
        if self.cart_type == 0x00:
            from .mbc import NoMBC
            return NoMBC(self)
        if self.cart_type in (0x01, 0x02, 0x03):
            from .mbc import MBC1
            return MBC1(self)
        raise ValueError(f"Unsupported cartridge type: {self.cart_type:#04x}")
```

Run: `pytest tests/test_cartridge.py::test_unsupported_cart_type_raises -v`
Expected: PASS. The other two tests (`test_parses_title`, `test_parses_rom_and_ram_size`) still fail on the `mbc` import — that's expected and resolved by Task 3.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cartridge.py tests/test_cartridge.py
git commit -m "feat: parse cartridge header"
```

---

### Task 3: NoMBC and MBC1 mappers

**Files:**
- Create: `gbemulator/core/mbc.py`
- Test: `tests/test_mbc.py`

**Interfaces:**
- Consumes: `Cartridge` instance (for `.rom`, `.ram_size`) from Task 2.
- Produces: `NoMBC(cartridge)` and `MBC1(cartridge)`, both with `.read(addr)` / `.write(addr, value)`. Depended on by Task 2 (already wired) and Task 5 (MMU delegates to `cartridge.read/write`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mbc.py
from gbemulator.core.cartridge import Cartridge


def _make_mbc1_rom(num_banks=4, ram_size_code=0x02):
    rom = bytearray(0x4000 * num_banks)
    rom[0x147] = 0x01  # MBC1
    rom[0x148] = {2: 0x00, 4: 0x01, 8: 0x02}[num_banks]
    rom[0x149] = ram_size_code
    for bank in range(num_banks):
        rom[bank * 0x4000] = bank  # marker byte at start of each bank
    return bytes(rom)


def test_nomb_reads_rom_directly():
    rom = bytearray(32 * 1024)
    rom[0x150] = 0xAB
    cart = Cartridge(bytes(rom))
    assert cart.read(0x150) == 0xAB


def test_nomb_ram_read_write():
    cart = Cartridge(bytes(bytearray(32 * 1024)))
    cart.ram_size = 0  # ROM-only carts typically have no RAM; write should be ignored safely
    assert cart.mbc.read(0xA000) == 0xFF


def test_mbc1_bank0_fixed():
    cart = Cartridge(_make_mbc1_rom())
    assert cart.read(0x0000) == 0  # bank 0 marker


def test_mbc1_default_bank1_switchable_area():
    cart = Cartridge(_make_mbc1_rom())
    assert cart.read(0x4000) == 1  # defaults to bank 1


def test_mbc1_bank_switch():
    cart = Cartridge(_make_mbc1_rom(num_banks=4))
    cart.write(0x2000, 0x03)  # select bank 3
    assert cart.read(0x4000) == 3


def test_mbc1_bank_switch_zero_maps_to_one():
    cart = Cartridge(_make_mbc1_rom(num_banks=4))
    cart.write(0x2000, 0x00)  # writing 0 selects bank 1 per SM83 quirk
    assert cart.read(0x4000) == 1


def test_mbc1_ram_requires_enable():
    cart = Cartridge(_make_mbc1_rom(ram_size_code=0x02))
    cart.write(0xA000, 0x42)  # RAM disabled by default, write ignored
    assert cart.read(0xA000) == 0xFF
    cart.write(0x0000, 0x0A)  # enable RAM
    cart.write(0xA000, 0x42)
    assert cart.read(0xA000) == 0x42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mbc.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.mbc'`

- [ ] **Step 3: Write minimal implementation**

```python
# gbemulator/core/mbc.py
class NoMBC:
    def __init__(self, cartridge):
        self.rom = cartridge.rom
        self.ram = bytearray(cartridge.ram_size)

    def read(self, addr):
        if addr <= 0x7FFF:
            return self.rom[addr] if addr < len(self.rom) else 0xFF
        if 0xA000 <= addr <= 0xBFFF:
            offset = addr - 0xA000
            return self.ram[offset] if offset < len(self.ram) else 0xFF
        return 0xFF

    def write(self, addr, value):
        if 0xA000 <= addr <= 0xBFFF:
            offset = addr - 0xA000
            if offset < len(self.ram):
                self.ram[offset] = value & 0xFF


class MBC1:
    def __init__(self, cartridge):
        self.rom = cartridge.rom
        self.ram = bytearray(cartridge.ram_size)
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_enabled = False
        self.banking_mode = 0
        self.num_rom_banks = max(1, len(self.rom) // 0x4000)

    def read(self, addr):
        if addr <= 0x3FFF:
            return self.rom[addr] if addr < len(self.rom) else 0xFF
        if 0x4000 <= addr <= 0x7FFF:
            offset = (self.rom_bank * 0x4000) + (addr - 0x4000)
            return self.rom[offset] if offset < len(self.rom) else 0xFF
        if 0xA000 <= addr <= 0xBFFF:
            if not self.ram_enabled or len(self.ram) == 0:
                return 0xFF
            offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
            return self.ram[offset] if offset < len(self.ram) else 0xFF
        return 0xFF

    def write(self, addr, value):
        value &= 0xFF
        if addr <= 0x1FFF:
            self.ram_enabled = (value & 0x0F) == 0x0A
        elif 0x2000 <= addr <= 0x3FFF:
            bank = value & 0x1F
            if bank == 0:
                bank = 1
            self.rom_bank = (self.rom_bank & 0x60) | bank
            self.rom_bank %= self.num_rom_banks or 1
            if self.rom_bank == 0:
                self.rom_bank = 1
        elif 0x4000 <= addr <= 0x5FFF:
            bits = value & 0x03
            if self.banking_mode == 0:
                self.rom_bank = (self.rom_bank & 0x1F) | (bits << 5)
            else:
                self.ram_bank = bits
        elif 0x6000 <= addr <= 0x7FFF:
            self.banking_mode = value & 0x01
        elif 0xA000 <= addr <= 0xBFFF:
            if self.ram_enabled and len(self.ram) > 0:
                offset = (self.ram_bank * 0x2000) + (addr - 0xA000)
                if offset < len(self.ram):
                    self.ram[offset] = value
```

- [ ] **Step 4: Run tests to verify everything passes**

Run: `pytest tests/test_cartridge.py tests/test_mbc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/mbc.py tests/test_mbc.py
git commit -m "feat: NoMBC and MBC1 cartridge mappers"
```

---

### Task 4: Interrupt bit constants and helpers

**Files:**
- Create: `gbemulator/core/interrupts.py`
- Test: `tests/test_interrupts.py`

**Interfaces:**
- Consumes: an object with `.read(addr)`/`.write(addr, value)` (an MMU, or a fake in tests).
- Produces: constants `VBLANK=0x01`, `LCD_STAT=0x02`, `TIMER=0x04`, `SERIAL=0x08`, `JOYPAD=0x10`; functions `request(mmu, bit)`, `pending_vector(mmu)` returning `(bit, vector_addr)` or `None`, and `clear(mmu, bit)`. Depended on by Task 14 (CPU interrupt servicing), Task 15 (Timer), Task 16 (Joypad), Task 17 (PPU VBlank).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_interrupts.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_interrupts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.interrupts'`

- [ ] **Step 3: Write minimal implementation**

```python
# gbemulator/core/interrupts.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_interrupts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/interrupts.py tests/test_interrupts.py
git commit -m "feat: interrupt request/pending/clear helpers"
```

---

### Task 5: MMU core

**Files:**
- Create: `gbemulator/core/mmu.py`
- Test: `tests/test_mmu.py`

**Interfaces:**
- Consumes: a `Cartridge`-like object with `.read(addr)`/`.write(addr, value)` (Task 2).
- Produces: `MMU(cartridge)` with `.read(addr)`, `.write(addr, value)`, public `.mem` bytearray(0x10000), and optional `.joypad`/`.timer` attributes (`None` until Task 15/16 wire them in) that `read`/`write` delegate to for addresses `0xFF00` and `0xFF04`. Depended on by Task 6 (CPU), Task 15 (Timer), Task 16 (Joypad), Task 17 (PPU).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mmu.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mmu.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.mmu'`

- [ ] **Step 3: Write minimal implementation**

```python
# gbemulator/core/mmu.py
class MMU:
    def __init__(self, cartridge):
        self.cartridge = cartridge
        self.mem = bytearray(0x10000)
        self.joypad = None
        self.timer = None

    def read(self, addr):
        addr &= 0xFFFF
        if addr <= 0x7FFF or 0xA000 <= addr <= 0xBFFF:
            return self.cartridge.read(addr)
        if addr == 0xFF00 and self.joypad is not None:
            return self.joypad.read()
        return self.mem[addr]

    def write(self, addr, value):
        addr &= 0xFFFF
        value &= 0xFF
        if addr <= 0x7FFF or 0xA000 <= addr <= 0xBFFF:
            self.cartridge.write(addr, value)
            return
        if addr == 0xFF00 and self.joypad is not None:
            self.joypad.write(value)
            return
        if addr == 0xFF04 and self.timer is not None:
            self.timer.reset_div()
            return
        self.mem[addr] = value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mmu.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/mmu.py tests/test_mmu.py
git commit -m "feat: MMU core with cartridge/joypad/timer delegation"
```

---

### Task 6: CPU skeleton (registers, flags, fetch, step loop)

**Files:**
- Create: `gbemulator/core/cpu.py`
- Create: `tests/conftest.py`
- Test: `tests/test_cpu_skeleton.py`

**Interfaces:**
- Consumes: an object with `.read(addr)`/`.write(addr, value)` (MMU or fake), plus `interrupts.pending_vector`/`.clear` (Task 4).
- Produces: `CPU(mmu)` with 8-bit regs `a,f,b,c,d,e,h,l`; 16-bit properties `bc,de,hl,af`; `sp,pc,ime,ime_pending,halted`; `fetch8()`, `fetch16()`; flag helpers `get_flag(mask)`/`set_flag(mask, value)` and constants `ZERO_FLAG=0x80, SUB_FLAG=0x40, HALF_CARRY_FLAG=0x20, CARRY_FLAG=0x10`; `execute(opcode)` raising `NotImplementedError` for anything not yet wired; `step()` that fetches one opcode, calls `execute`, and returns cycles. Also produces the `tests/conftest.py` `FakeMMU`, `mmu` and `cpu` pytest fixtures reused by every later CPU task.

- [ ] **Step 1: Write `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from gbemulator.core.cpu import CPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr & 0xFFFF]

    def write(self, addr, value):
        self.mem[addr & 0xFFFF] = value & 0xFF


@pytest.fixture
def mmu():
    return FakeMMU()


@pytest.fixture
def cpu(mmu):
    return CPU(mmu)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_cpu_skeleton.py
import pytest


def test_initial_register_state(cpu):
    assert cpu.pc == 0x0100
    assert cpu.sp == 0xFFFE


def test_bc_de_hl_af_composite_registers(cpu):
    cpu.b, cpu.c = 0x12, 0x34
    assert cpu.bc == 0x1234
    cpu.hl = 0xBEEF
    assert cpu.h == 0xBE and cpu.l == 0xEF
    cpu.a, cpu.f = 0xAB, 0xF0
    assert cpu.af == 0xABF0


def test_fetch8_advances_pc(cpu, mmu):
    mmu.mem[0x0100] = 0x99
    value = cpu.fetch8()
    assert value == 0x99
    assert cpu.pc == 0x0101


def test_fetch16_little_endian(cpu, mmu):
    mmu.mem[0x0100] = 0x34
    mmu.mem[0x0101] = 0x12
    assert cpu.fetch16() == 0x1234
    assert cpu.pc == 0x0102


def test_set_and_get_flag(cpu):
    cpu.set_flag(cpu.ZERO_FLAG, True)
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    cpu.set_flag(cpu.ZERO_FLAG, False)
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0


def test_step_dispatches_to_execute(cpu, mmu):
    mmu.mem[0x0100] = 0x00  # NOP, wired in Task 8 (misc control)
    with pytest.raises(NotImplementedError):
        cpu.step()


def test_unknown_opcode_raises(cpu, mmu):
    mmu.mem[0x0100] = 0xFC  # never a valid unprefixed opcode
    with pytest.raises(NotImplementedError):
        cpu.step()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_cpu_skeleton.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.cpu'`

- [ ] **Step 4: Write minimal implementation**

```python
# gbemulator/core/cpu.py
class CPU:
    ZERO_FLAG = 0x80
    SUB_FLAG = 0x40
    HALF_CARRY_FLAG = 0x20
    CARRY_FLAG = 0x10

    def __init__(self, mmu):
        self.mmu = mmu
        self.a = 0x01
        self.f = 0xB0
        self.b = 0x00
        self.c = 0x13
        self.d = 0x00
        self.e = 0xD8
        self.h = 0x01
        self.l = 0x4D
        self.sp = 0xFFFE
        self.pc = 0x0100
        self.ime = False
        self.ime_pending = False
        self.halted = False

    @property
    def bc(self):
        return (self.b << 8) | self.c

    @bc.setter
    def bc(self, value):
        value &= 0xFFFF
        self.b, self.c = (value >> 8) & 0xFF, value & 0xFF

    @property
    def de(self):
        return (self.d << 8) | self.e

    @de.setter
    def de(self, value):
        value &= 0xFFFF
        self.d, self.e = (value >> 8) & 0xFF, value & 0xFF

    @property
    def hl(self):
        return (self.h << 8) | self.l

    @hl.setter
    def hl(self, value):
        value &= 0xFFFF
        self.h, self.l = (value >> 8) & 0xFF, value & 0xFF

    @property
    def af(self):
        return (self.a << 8) | (self.f & 0xF0)

    @af.setter
    def af(self, value):
        value &= 0xFFFF
        self.a, self.f = (value >> 8) & 0xFF, value & 0xF0

    def get_flag(self, mask):
        return 1 if (self.f & mask) else 0

    def set_flag(self, mask, value):
        if value:
            self.f |= mask
        else:
            self.f &= ~mask & 0xFF

    def fetch8(self):
        value = self.mmu.read(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return value

    def fetch16(self):
        lo = self.fetch8()
        hi = self.fetch8()
        return (hi << 8) | lo

    def execute(self, opcode):
        raise NotImplementedError(f"Opcode {opcode:#04x} not implemented at PC={self.pc - 1:#06x}")

    def step(self):
        opcode = self.fetch8()
        return self.execute(opcode)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cpu_skeleton.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add gbemulator/core/cpu.py tests/conftest.py tests/test_cpu_skeleton.py
git commit -m "feat: CPU skeleton with registers, flags, fetch, step"
```

---

### Task 7: 8-bit register helpers (`_get_r8`/`_set_r8`) and 8-bit load instructions

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_loads_8bit.py`

**Interfaces:**
- Consumes: `CPU` skeleton (Task 6): `fetch8`, `execute`, `hl` property, `mmu.read/write`.
- Produces: `CPU._get_r8(idx)` / `CPU._set_r8(idx, value)` using index order `0=B,1=C,2=D,3=E,4=H,5=L,6=(HL),7=A`; `execute()` handles opcodes `0x40-0x7F` (except `0x76`=HALT, left unimplemented until Task 12) and the 8 `LD r,d8` opcodes (`0x06,0x0E,0x16,0x1E,0x26,0x2E,0x36,0x3E`) plus `LD A,(BC)/(DE)/(HL+)/(HL-)`, `LD (BC),A/(DE),A/(HL+),A/(HL-),A`, `LDH (a8),A`/`LDH A,(a8)`, `LD (C),A`/`LD A,(C)`, `LD (a16),A`/`LD A,(a16)`. Depended on by all later CPU tasks for register access.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_loads_8bit.py
import itertools
import pytest


R8_ATTR = {0: "b", 1: "c", 2: "d", 3: "e", 4: "h", 5: "l", 7: "a"}


@pytest.mark.parametrize("dst,src", [
    (d, s) for d, s in itertools.product(range(8), repeat=2) if (d, s) != (6, 6)
])
def test_ld_r_r(cpu, mmu, dst, src):
    opcode = 0x40 | (dst << 3) | src
    mmu.mem[0x0100] = opcode
    if src == 6:
        cpu.hl = 0xC000
        mmu.mem[0xC000] = 0x77
    elif src != dst:
        setattr(cpu, R8_ATTR[src], 0x77)
    else:
        setattr(cpu, R8_ATTR[src], 0x77)

    cpu.step()

    if dst == 6:
        cpu.hl = cpu.hl  # no-op, just documents (HL) was the target
        assert mmu.mem[cpu.hl] == 0x77 if src != 6 else True
    else:
        assert getattr(cpu, R8_ATTR[dst]) == 0x77


@pytest.mark.parametrize("opcode,attr", [
    (0x06, "b"), (0x0E, "c"), (0x16, "d"), (0x1E, "e"),
    (0x26, "h"), (0x2E, "l"), (0x3E, "a"),
])
def test_ld_r_d8(cpu, mmu, opcode, attr):
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x99
    cpu.step()
    assert getattr(cpu, attr) == 0x99
    assert cpu.pc == 0x0102


def test_ld_hl_d8(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0x0100] = 0x36
    mmu.mem[0x0101] = 0x55
    cpu.step()
    assert mmu.mem[0xC000] == 0x55


def test_ld_a_bc_indirect(cpu, mmu):
    cpu.bc = 0xC001
    mmu.mem[0xC001] = 0x42
    mmu.mem[0x0100] = 0x0A
    cpu.step()
    assert cpu.a == 0x42


def test_ld_bc_indirect_a(cpu, mmu):
    cpu.bc = 0xC002
    cpu.a = 0x33
    mmu.mem[0x0100] = 0x02
    cpu.step()
    assert mmu.mem[0xC002] == 0x33


def test_ld_a_hl_plus_increments_hl(cpu, mmu):
    cpu.hl = 0xC003
    mmu.mem[0xC003] = 0x11
    mmu.mem[0x0100] = 0x2A
    cpu.step()
    assert cpu.a == 0x11
    assert cpu.hl == 0xC004


def test_ld_hl_minus_a_decrements_hl(cpu, mmu):
    cpu.hl = 0xC004
    cpu.a = 0x22
    mmu.mem[0x0100] = 0x32
    cpu.step()
    assert mmu.mem[0xC004] == 0x22
    assert cpu.hl == 0xC003


def test_ldh_a8_a(cpu, mmu):
    cpu.a = 0x5A
    mmu.mem[0x0100] = 0xE0
    mmu.mem[0x0101] = 0x80
    cpu.step()
    assert mmu.mem[0xFF80] == 0x5A


def test_ldh_a_a8(cpu, mmu):
    mmu.mem[0xFF81] = 0x66
    mmu.mem[0x0100] = 0xF0
    mmu.mem[0x0101] = 0x81
    cpu.step()
    assert cpu.a == 0x66


def test_ld_c_indirect_a(cpu, mmu):
    cpu.c = 0x82
    cpu.a = 0x11
    mmu.mem[0x0100] = 0xE2
    cpu.step()
    assert mmu.mem[0xFF82] == 0x11


def test_ld_a16_a(cpu, mmu):
    cpu.a = 0x9A
    mmu.mem[0x0100] = 0xEA
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC1
    cpu.step()
    assert mmu.mem[0xC100] == 0x9A
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_loads_8bit.py -v`
Expected: FAIL — all raise `NotImplementedError`.

- [ ] **Step 3: Add register helpers and load handling to `cpu.py`**

Add these methods to the `CPU` class and update `execute`:

```python
    def _get_r8(self, idx):
        if idx == 0: return self.b
        if idx == 1: return self.c
        if idx == 2: return self.d
        if idx == 3: return self.e
        if idx == 4: return self.h
        if idx == 5: return self.l
        if idx == 6: return self.mmu.read(self.hl)
        return self.a  # idx == 7

    def _set_r8(self, idx, value):
        value &= 0xFF
        if idx == 0: self.b = value
        elif idx == 1: self.c = value
        elif idx == 2: self.d = value
        elif idx == 3: self.e = value
        elif idx == 4: self.h = value
        elif idx == 5: self.l = value
        elif idx == 6: self.mmu.write(self.hl, value)
        else: self.a = value

    def _ld_r_r(self, opcode):
        dst = (opcode >> 3) & 0x07
        src = opcode & 0x07
        self._set_r8(dst, self._get_r8(src))
        return 8 if (dst == 6 or src == 6) else 4

    def _ld_r_d8(self, opcode):
        dst = (opcode >> 3) & 0x07
        self._set_r8(dst, self.fetch8())
        return 12 if dst == 6 else 8

    def execute(self, opcode):
        if 0x40 <= opcode <= 0x7F and opcode != 0x76:
            return self._ld_r_r(opcode)
        if opcode in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E):
            return self._ld_r_d8(opcode)
        if opcode == 0x0A:
            self.a = self.mmu.read(self.bc)
            return 8
        if opcode == 0x1A:
            self.a = self.mmu.read(self.de)
            return 8
        if opcode == 0x02:
            self.mmu.write(self.bc, self.a)
            return 8
        if opcode == 0x12:
            self.mmu.write(self.de, self.a)
            return 8
        if opcode == 0x2A:
            self.a = self.mmu.read(self.hl)
            self.hl = (self.hl + 1) & 0xFFFF
            return 8
        if opcode == 0x3A:
            self.a = self.mmu.read(self.hl)
            self.hl = (self.hl - 1) & 0xFFFF
            return 8
        if opcode == 0x22:
            self.mmu.write(self.hl, self.a)
            self.hl = (self.hl + 1) & 0xFFFF
            return 8
        if opcode == 0x32:
            self.mmu.write(self.hl, self.a)
            self.hl = (self.hl - 1) & 0xFFFF
            return 8
        if opcode == 0xE0:
            self.mmu.write(0xFF00 + self.fetch8(), self.a)
            return 12
        if opcode == 0xF0:
            self.a = self.mmu.read(0xFF00 + self.fetch8())
            return 12
        if opcode == 0xE2:
            self.mmu.write(0xFF00 + self.c, self.a)
            return 8
        if opcode == 0xF2:
            self.a = self.mmu.read(0xFF00 + self.c)
            return 8
        if opcode == 0xEA:
            self.mmu.write(self.fetch16(), self.a)
            return 16
        if opcode == 0xFA:
            self.a = self.mmu.read(self.fetch16())
            return 16
        raise NotImplementedError(f"Opcode {opcode:#04x} not implemented at PC={self.pc - 1:#06x}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_loads_8bit.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_loads_8bit.py
git commit -m "feat: 8-bit register helpers and LD instructions"
```

---

### Task 8: 16-bit loads, PUSH/POP, and misc control (NOP/HALT/STOP/DI/EI)

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_loads_16bit.py`
- Test: `tests/test_cpu_misc.py`

**Interfaces:**
- Consumes: `_get_r8`/`_set_r8`, `bc/de/hl/af/sp` properties (Task 6-7).
- Produces: `execute()` handles `LD rr,d16` (`0x01,0x11,0x21,0x31`), `LD (a16),SP` (`0x08`), `LD SP,HL` (`0xF9`), `LD HL,SP+r8` (`0xF8`), `PUSH rr`/`POP rr` (`0xC5,0xD5,0xE5,0xF5` / `0xC1,0xD1,0xE1,0xF1`), `NOP` (`0x00`), `HALT` (`0x76`), `STOP` (`0x10`), `DI` (`0xF3`), `EI` (`0xFB`). Also updates `step()` to honor `halted`/`ime_pending`. Depended on by Task 15 (interrupt wake-from-halt) and Task 21 (GameBoy orchestrator relies on `step()` cycle accounting).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cpu_loads_16bit.py
import pytest


@pytest.mark.parametrize("opcode,attr", [(0x01, "bc"), (0x11, "de"), (0x21, "hl")])
def test_ld_rr_d16(cpu, mmu, opcode, attr):
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x34
    mmu.mem[0x0102] = 0x12
    cpu.step()
    assert getattr(cpu, attr) == 0x1234


def test_ld_sp_d16(cpu, mmu):
    mmu.mem[0x0100] = 0x31
    mmu.mem[0x0101] = 0xFE
    mmu.mem[0x0102] = 0xFF
    cpu.step()
    assert cpu.sp == 0xFFFE


def test_ld_a16_sp(cpu, mmu):
    cpu.sp = 0xABCD
    mmu.mem[0x0100] = 0x08
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC1
    cpu.step()
    assert mmu.mem[0xC100] == 0xCD
    assert mmu.mem[0xC101] == 0xAB


def test_ld_sp_hl(cpu, mmu):
    cpu.hl = 0x9988
    mmu.mem[0x0100] = 0xF9
    cpu.step()
    assert cpu.sp == 0x9988


def test_ld_hl_sp_plus_positive_offset(cpu, mmu):
    cpu.sp = 0xC000
    mmu.mem[0x0100] = 0xF8
    mmu.mem[0x0101] = 0x02
    cpu.step()
    assert cpu.hl == 0xC002
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_ld_hl_sp_plus_negative_offset(cpu, mmu):
    cpu.sp = 0xC005
    mmu.mem[0x0100] = 0xF8
    mmu.mem[0x0101] = 0xFE  # -2
    cpu.step()
    assert cpu.hl == 0xC003


@pytest.mark.parametrize("push_op,pop_op,attr", [
    (0xC5, 0xC1, "bc"), (0xD5, 0xD1, "de"), (0xE5, 0xE1, "hl"),
])
def test_push_pop_roundtrip(cpu, mmu, push_op, pop_op, attr):
    setattr(cpu, attr, 0x1357)
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = push_op
    cpu.step()
    assert cpu.sp == 0xFFFC
    setattr(cpu, attr, 0x0000)
    mmu.mem[0x0101] = pop_op
    cpu.step()
    assert getattr(cpu, attr) == 0x1357
    assert cpu.sp == 0xFFFE


def test_push_pop_af_masks_low_nibble(cpu, mmu):
    cpu.af = 0x12FF
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xF5  # PUSH AF
    mmu.mem[0x0101] = 0xF1  # POP AF
    cpu.step()
    cpu.step()
    assert cpu.af == 0x12F0
```

```python
# tests/test_cpu_misc.py
def test_nop_advances_pc_and_costs_4_cycles(cpu, mmu):
    mmu.mem[0x0100] = 0x00
    cycles = cpu.step()
    assert cpu.pc == 0x0101
    assert cycles == 4


def test_halt_sets_halted_flag(cpu, mmu):
    mmu.mem[0x0100] = 0x76
    cpu.step()
    assert cpu.halted is True


def test_halted_cpu_returns_4_cycles_without_fetching(cpu, mmu):
    cpu.halted = True
    mmu.mem[0x0100] = 0xFF  # would be an invalid opcode if fetched
    cycles = cpu.step()
    assert cycles == 4
    assert cpu.pc == 0x0100  # did not advance


def test_di_clears_ime_immediately(cpu, mmu):
    cpu.ime = True
    mmu.mem[0x0100] = 0xF3
    cpu.step()
    assert cpu.ime is False


def test_ei_sets_ime_after_next_instruction(cpu, mmu):
    mmu.mem[0x0100] = 0xFB  # EI
    mmu.mem[0x0101] = 0x00  # NOP
    cpu.step()
    assert cpu.ime is False  # not yet - takes effect after next instruction
    cpu.step()
    assert cpu.ime is True


def test_stop_advances_pc_by_2(cpu, mmu):
    mmu.mem[0x0100] = 0x10
    mmu.mem[0x0101] = 0x00
    cpu.step()
    assert cpu.pc == 0x0102
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cpu_loads_16bit.py tests/test_cpu_misc.py -v`
Expected: FAIL — all raise `NotImplementedError` (or `AttributeError` for `halted` checks not yet wired to `step`).

- [ ] **Step 3: Add 16-bit loads, stack ops, and misc control to `cpu.py`**

Add helper methods and extend `execute`/`step`:

```python
    def _push16(self, value):
        self.sp = (self.sp - 1) & 0xFFFF
        self.mmu.write(self.sp, (value >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self.mmu.write(self.sp, value & 0xFF)

    def _pop16(self):
        lo = self.mmu.read(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        hi = self.mmu.read(self.sp)
        self.sp = (self.sp + 1) & 0xFFFF
        return (hi << 8) | lo

    def _signed8(self, value):
        return value - 256 if value & 0x80 else value
```

Extend `execute` with (insert before the final `raise`):

```python
        if opcode in (0x01, 0x11, 0x21, 0x31):
            value = self.fetch16()
            {0x01: "bc", 0x11: "de", 0x21: "hl", 0x31: "sp"}
            if opcode == 0x01: self.bc = value
            elif opcode == 0x11: self.de = value
            elif opcode == 0x21: self.hl = value
            else: self.sp = value
            return 12
        if opcode == 0x08:
            addr = self.fetch16()
            self.mmu.write(addr, self.sp & 0xFF)
            self.mmu.write((addr + 1) & 0xFFFF, (self.sp >> 8) & 0xFF)
            return 20
        if opcode == 0xF9:
            self.sp = self.hl
            return 8
        if opcode == 0xF8:
            offset = self._signed8(self.fetch8())
            result = (self.sp + offset) & 0xFFFF
            self.set_flag(self.ZERO_FLAG, False)
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, ((self.sp & 0xF) + (offset & 0xF)) > 0xF)
            self.set_flag(self.CARRY_FLAG, ((self.sp & 0xFF) + (offset & 0xFF)) > 0xFF)
            self.hl = result
            return 12
        if opcode in (0xC5, 0xD5, 0xE5, 0xF5):
            value = {0xC5: self.bc, 0xD5: self.de, 0xE5: self.hl, 0xF5: self.af}[opcode]
            self._push16(value)
            return 16
        if opcode in (0xC1, 0xD1, 0xE1, 0xF1):
            value = self._pop16()
            if opcode == 0xC1: self.bc = value
            elif opcode == 0xD1: self.de = value
            elif opcode == 0xE1: self.hl = value
            else: self.af = value
            return 12
        if opcode == 0x00:
            return 4
        if opcode == 0x76:
            self.halted = True
            return 4
        if opcode == 0x10:
            self.fetch8()  # STOP's mandatory second byte, unused in our scope
            return 4
        if opcode == 0xF3:
            self.ime = False
            return 4
        if opcode == 0xFB:
            self.ime_pending = True
            return 4
```

Update `step()`:

```python
    def step(self):
        if self.halted:
            return 4
        if self.ime_pending:
            self.ime = True
            self.ime_pending = False
        opcode = self.fetch8()
        return self.execute(opcode)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cpu_loads_16bit.py tests/test_cpu_misc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_loads_16bit.py tests/test_cpu_misc.py
git commit -m "feat: 16-bit loads, stack ops, NOP/HALT/STOP/DI/EI"
```

---

### Task 9: 8-bit arithmetic/logic (ADD/ADC/SUB/SBC/AND/XOR/OR/CP)

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_arithmetic_8bit.py`

**Interfaces:**
- Consumes: `_get_r8` (Task 7), flag helpers (Task 6).
- Produces: `execute()` handles the algebraically-decoded block `0x80-0xBF` (ADD/ADC/SUB/SBC/AND/XOR/OR/CP against `r8`) and their immediate forms `0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE`. Depended on by Task 14 (Blargg `cpu_instrs` exercises all of these).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_arithmetic_8bit.py
import pytest


def test_add_sets_carry_and_half_carry(cpu, mmu):
    cpu.a = 0xFF
    cpu.b = 0x01
    mmu.mem[0x0100] = 0x80  # ADD A,B
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_adc_includes_carry_in(cpu, mmu):
    cpu.a = 0x01
    cpu.b = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x88  # ADC A,B
    cpu.step()
    assert cpu.a == 0x03


def test_sub_sets_carry_when_borrow(cpu, mmu):
    cpu.a = 0x02
    cpu.b = 0x03
    mmu.mem[0x0100] = 0x90  # SUB B
    cpu.step()
    assert cpu.a == 0xFF
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 1


def test_sbc_includes_carry_in(cpu, mmu):
    cpu.a = 0x05
    cpu.b = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x98  # SBC A,B
    cpu.step()
    assert cpu.a == 0x03


def test_and_sets_half_carry_clears_carry(cpu, mmu):
    cpu.a = 0xF0
    cpu.b = 0xFF
    mmu.mem[0x0100] = 0xA0  # AND B
    cpu.step()
    assert cpu.a == 0xF0
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_xor_a_a_zeroes_and_sets_zero_flag(cpu, mmu):
    cpu.a = 0x5A
    mmu.mem[0x0100] = 0xAF  # XOR A
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_or_clears_flags_except_zero(cpu, mmu):
    cpu.a = 0x00
    cpu.b = 0x00
    mmu.mem[0x0100] = 0xB0  # OR B
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 0


def test_cp_does_not_modify_a(cpu, mmu):
    cpu.a = 0x10
    cpu.b = 0x10
    mmu.mem[0x0100] = 0xB8  # CP B
    cpu.step()
    assert cpu.a == 0x10
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_add_a_hl_indirect_costs_8_cycles(cpu, mmu):
    cpu.a = 0x01
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x01
    mmu.mem[0x0100] = 0x86  # ADD A,(HL)
    cycles = cpu.step()
    assert cpu.a == 0x02
    assert cycles == 8


@pytest.mark.parametrize("opcode,a,operand,expected", [
    (0xC6, 0x01, 0x01, 0x02),  # ADD A,d8
    (0xD6, 0x05, 0x03, 0x02),  # SUB d8
    (0xE6, 0xFF, 0x0F, 0x0F),  # AND d8
    (0xF6, 0x00, 0x0F, 0x0F),  # OR d8
])
def test_immediate_arithmetic(cpu, mmu, opcode, a, operand, expected):
    cpu.a = a
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = operand
    cpu.step()
    assert cpu.a == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_arithmetic_8bit.py -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Add arithmetic/logic to `cpu.py`**

```python
    def _alu_add(self, value, carry_in=0):
        result = self.a + value + carry_in
        self.set_flag(self.HALF_CARRY_FLAG, ((self.a & 0xF) + (value & 0xF) + carry_in) > 0xF)
        self.set_flag(self.CARRY_FLAG, result > 0xFF)
        self.a = result & 0xFF
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)

    def _alu_sub(self, value, carry_in=0, store=True):
        result = self.a - value - carry_in
        self.set_flag(self.HALF_CARRY_FLAG, (self.a & 0xF) < ((value & 0xF) + carry_in))
        self.set_flag(self.CARRY_FLAG, result < 0)
        result &= 0xFF
        self.set_flag(self.ZERO_FLAG, result == 0)
        self.set_flag(self.SUB_FLAG, True)
        if store:
            self.a = result

    def _alu_and(self, value):
        self.a &= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, True)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_or(self, value):
        self.a |= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, False)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_xor(self, value):
        self.a ^= value
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.SUB_FLAG, False)
        self.set_flag(self.HALF_CARRY_FLAG, False)
        self.set_flag(self.CARRY_FLAG, False)

    def _alu_dispatch(self, op_idx, value):
        carry = self.get_flag(self.CARRY_FLAG)
        if op_idx == 0: self._alu_add(value)
        elif op_idx == 1: self._alu_add(value, carry)
        elif op_idx == 2: self._alu_sub(value)
        elif op_idx == 3: self._alu_sub(value, carry)
        elif op_idx == 4: self._alu_and(value)
        elif op_idx == 5: self._alu_xor(value)
        elif op_idx == 6: self._alu_or(value)
        elif op_idx == 7: self._alu_sub(value, 0, store=False)  # CP
```

Extend `execute` (insert before the final `raise`):

```python
        if 0x80 <= opcode <= 0xBF:
            op_idx = (opcode >> 3) & 0x07
            src = opcode & 0x07
            self._alu_dispatch(op_idx, self._get_r8(src))
            return 8 if src == 6 else 4
        if opcode in (0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE):
            op_idx = (opcode >> 3) & 0x07
            self._alu_dispatch(op_idx, self.fetch8())
            return 8
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_arithmetic_8bit.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_arithmetic_8bit.py
git commit -m "feat: 8-bit ALU instructions (ADD/ADC/SUB/SBC/AND/XOR/OR/CP)"
```

---

### Task 10: INC/DEC (8-bit, 16-bit) and 16-bit ADD HL,rr

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_incdec.py`

**Interfaces:**
- Consumes: `_get_r8`/`_set_r8` (Task 7), `bc/de/hl/sp` (Task 6).
- Produces: `execute()` handles `INC r8`/`DEC r8` (`0x04,0x0C,...,0x3C` / `0x05,0x0D,...,0x3D`), `INC rr`/`DEC rr` (`0x03,0x13,0x23,0x33` / `0x0B,0x1B,0x2B,0x3B`), `ADD HL,rr` (`0x09,0x19,0x29,0x39`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_incdec.py
import pytest


@pytest.mark.parametrize("opcode,attr", [(0x04, "b"), (0x0C, "c"), (0x14, "d"), (0x3C, "a")])
def test_inc_r8(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x0F)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x10
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0


def test_inc_r8_wraps_and_sets_zero(cpu, mmu):
    cpu.a = 0xFF
    mmu.mem[0x0100] = 0x3C
    cpu.step()
    assert cpu.a == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_inc_r8_does_not_touch_carry(cpu, mmu):
    cpu.set_flag(cpu.CARRY_FLAG, True)
    cpu.a = 0x01
    mmu.mem[0x0100] = 0x3C
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


@pytest.mark.parametrize("opcode,attr", [(0x05, "b"), (0x0D, "c"), (0x3D, "a")])
def test_dec_r8(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x10)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x0F
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 1


def test_inc_hl_indirect(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x05
    mmu.mem[0x0100] = 0x34  # INC (HL)
    cycles = cpu.step()
    assert mmu.mem[0xC000] == 0x06
    assert cycles == 12


@pytest.mark.parametrize("opcode,attr", [(0x03, "bc"), (0x13, "de"), (0x23, "hl"), (0x33, "sp")])
def test_inc_rr(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0xFFFF)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0x0000


@pytest.mark.parametrize("opcode,attr", [(0x0B, "bc"), (0x1B, "de"), (0x2B, "hl"), (0x3B, "sp")])
def test_dec_rr(cpu, mmu, opcode, attr):
    setattr(cpu, attr, 0x0000)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert getattr(cpu, attr) == 0xFFFF


def test_inc_dec_rr_does_not_touch_flags(cpu, mmu):
    cpu.f = 0xF0
    cpu.bc = 0x1000
    mmu.mem[0x0100] = 0x03
    cpu.step()
    assert cpu.f == 0xF0


@pytest.mark.parametrize("opcode,attr", [(0x09, "bc"), (0x19, "de"), (0x39, "sp")])
def test_add_hl_rr(cpu, mmu, opcode, attr):
    cpu.hl = 0x0FFF
    setattr(cpu, attr, 0x0001)
    mmu.mem[0x0100] = opcode
    cpu.step()
    assert cpu.hl == 0x1000
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_add_hl_hl(cpu, mmu):
    cpu.hl = 0x8000
    mmu.mem[0x0100] = 0x29
    cpu.step()
    assert cpu.hl == 0x0000
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_add_hl_rr_preserves_zero_flag(cpu, mmu):
    cpu.set_flag(cpu.ZERO_FLAG, True)
    cpu.hl = 0x0001
    cpu.bc = 0x0001
    mmu.mem[0x0100] = 0x09
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_incdec.py -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Add INC/DEC/ADD HL,rr to `cpu.py`**

```python
    def _inc_r8(self, idx):
        value = self._get_r8(idx)
        result = (value + 1) & 0xFF
        self.set_flag(self.HALF_CARRY_FLAG, (value & 0xF) == 0xF)
        self.set_flag(self.ZERO_FLAG, result == 0)
        self.set_flag(self.SUB_FLAG, False)
        self._set_r8(idx, result)

    def _dec_r8(self, idx):
        value = self._get_r8(idx)
        result = (value - 1) & 0xFF
        self.set_flag(self.HALF_CARRY_FLAG, (value & 0xF) == 0x0)
        self.set_flag(self.ZERO_FLAG, result == 0)
        self.set_flag(self.SUB_FLAG, True)
        self._set_r8(idx, result)

    def _add_hl(self, value):
        result = self.hl + value
        self.set_flag(self.HALF_CARRY_FLAG, ((self.hl & 0xFFF) + (value & 0xFFF)) > 0xFFF)
        self.set_flag(self.CARRY_FLAG, result > 0xFFFF)
        self.set_flag(self.SUB_FLAG, False)
        self.hl = result & 0xFFFF
```

Extend `execute` (insert before the final `raise`):

```python
        if opcode in (0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C):
            idx = (opcode >> 3) & 0x07
            self._inc_r8(idx)
            return 12 if idx == 6 else 4
        if opcode in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D):
            idx = (opcode >> 3) & 0x07
            self._dec_r8(idx)
            return 12 if idx == 6 else 4
        if opcode in (0x03, 0x13, 0x23, 0x33):
            attr = {0x03: "bc", 0x13: "de", 0x23: "hl", 0x33: "sp"}[opcode]
            setattr(self, attr, (getattr(self, attr) + 1) & 0xFFFF)
            return 8
        if opcode in (0x0B, 0x1B, 0x2B, 0x3B):
            attr = {0x0B: "bc", 0x1B: "de", 0x2B: "hl", 0x3B: "sp"}[opcode]
            setattr(self, attr, (getattr(self, attr) - 1) & 0xFFFF)
            return 8
        if opcode in (0x09, 0x19, 0x29, 0x39):
            attr = {0x09: "bc", 0x19: "de", 0x29: "hl", 0x39: "sp"}[opcode]
            self._add_hl(getattr(self, attr))
            return 8
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_incdec.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_incdec.py
git commit -m "feat: INC/DEC (8-bit, 16-bit) and ADD HL,rr"
```

---

### Task 11: Accumulator rotates and DAA/CPL/SCF/CCF

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_rotates_misc.py`

**Interfaces:**
- Consumes: flag helpers (Task 6).
- Produces: `execute()` handles `RLCA` (`0x07`), `RRCA` (`0x0F`), `RLA` (`0x17`), `RRA` (`0x1F`), `DAA` (`0x27`), `CPL` (`0x2F`), `SCF` (`0x37`), `CCF` (`0x3F`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_rotates_misc.py
def test_rlca_rotates_left_through_bit7_to_carry(cpu, mmu):
    cpu.a = 0x85  # 1000_0101
    mmu.mem[0x0100] = 0x07
    cpu.step()
    assert cpu.a == 0x0B  # 0000_1011
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.ZERO_FLAG) == 0  # RLCA always clears Z


def test_rrca_rotates_right_through_bit0_to_carry(cpu, mmu):
    cpu.a = 0x01
    mmu.mem[0x0100] = 0x0F
    cpu.step()
    assert cpu.a == 0x80
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_rla_rotates_through_existing_carry(cpu, mmu):
    cpu.a = 0x80
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x17
    cpu.step()
    assert cpu.a == 0x01
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_rra_rotates_through_existing_carry(cpu, mmu):
    cpu.a = 0x01
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x1F
    cpu.step()
    assert cpu.a == 0x80
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cpl_inverts_a_and_sets_flags(cpu, mmu):
    cpu.a = 0x0F
    mmu.mem[0x0100] = 0x2F
    cpu.step()
    assert cpu.a == 0xF0
    assert cpu.get_flag(cpu.SUB_FLAG) == 1
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_scf_sets_carry_clears_n_h(cpu, mmu):
    mmu.mem[0x0100] = 0x37
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.SUB_FLAG) == 0
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 0


def test_ccf_flips_carry(cpu, mmu):
    cpu.set_flag(cpu.CARRY_FLAG, True)
    mmu.mem[0x0100] = 0x3F
    cpu.step()
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_daa_after_addition_adjusts_to_valid_bcd(cpu, mmu):
    # 0x45 + 0x38 = 0x7D in binary, should become 0x83 in BCD
    cpu.a = 0x45
    cpu.b = 0x38
    mmu.mem[0x0100] = 0x80  # ADD A,B
    mmu.mem[0x0101] = 0x27  # DAA
    cpu.step()
    cpu.step()
    assert cpu.a == 0x83
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_rotates_misc.py -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Add to `cpu.py`**

```python
    def _rlca(self):
        carry = (self.a >> 7) & 1
        self.a = ((self.a << 1) | carry) & 0xFF
        self.f = 0
        self.set_flag(self.CARRY_FLAG, carry)

    def _rrca(self):
        carry = self.a & 1
        self.a = ((self.a >> 1) | (carry << 7)) & 0xFF
        self.f = 0
        self.set_flag(self.CARRY_FLAG, carry)

    def _rla(self):
        old_carry = self.get_flag(self.CARRY_FLAG)
        new_carry = (self.a >> 7) & 1
        self.a = ((self.a << 1) | old_carry) & 0xFF
        self.f = 0
        self.set_flag(self.CARRY_FLAG, new_carry)

    def _rra(self):
        old_carry = self.get_flag(self.CARRY_FLAG)
        new_carry = self.a & 1
        self.a = ((self.a >> 1) | (old_carry << 7)) & 0xFF
        self.f = 0
        self.set_flag(self.CARRY_FLAG, new_carry)

    def _daa(self):
        adjust = 0
        carry = self.get_flag(self.CARRY_FLAG)
        if self.get_flag(self.SUB_FLAG):
            if self.get_flag(self.HALF_CARRY_FLAG):
                adjust += 0x06
            if carry:
                adjust += 0x60
            self.a = (self.a - adjust) & 0xFF
        else:
            if self.get_flag(self.HALF_CARRY_FLAG) or (self.a & 0x0F) > 0x09:
                adjust += 0x06
            if carry or self.a > 0x99:
                adjust += 0x60
                carry = 1
            self.a = (self.a + adjust) & 0xFF
        self.set_flag(self.ZERO_FLAG, self.a == 0)
        self.set_flag(self.HALF_CARRY_FLAG, False)
        self.set_flag(self.CARRY_FLAG, carry)
```

Extend `execute` (insert before the final `raise`):

```python
        if opcode == 0x07:
            self._rlca(); return 4
        if opcode == 0x0F:
            self._rrca(); return 4
        if opcode == 0x17:
            self._rla(); return 4
        if opcode == 0x1F:
            self._rra(); return 4
        if opcode == 0x27:
            self._daa(); return 4
        if opcode == 0x2F:
            self.a = (~self.a) & 0xFF
            self.set_flag(self.SUB_FLAG, True)
            self.set_flag(self.HALF_CARRY_FLAG, True)
            return 4
        if opcode == 0x37:
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, False)
            self.set_flag(self.CARRY_FLAG, True)
            return 4
        if opcode == 0x3F:
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, False)
            self.set_flag(self.CARRY_FLAG, not self.get_flag(self.CARRY_FLAG))
            return 4
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_rotates_misc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_rotates_misc.py
git commit -m "feat: accumulator rotates and DAA/CPL/SCF/CCF"
```

---

### Task 12: Jumps, calls, returns, RST

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_control_flow.py`

**Interfaces:**
- Consumes: `_push16`/`_pop16` (Task 8), flag helpers (Task 6).
- Produces: `execute()` handles `JP a16`/`JP cc,a16`/`JP (HL)`, `JR r8`/`JR cc,r8`, `CALL a16`/`CALL cc,a16`, `RET`/`RET cc`/`RETI`, `RST n`. Condition code order: `0=NZ,1=Z,2=NC,3=C`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_control_flow.py
import pytest


def test_jp_a16(cpu, mmu):
    mmu.mem[0x0100] = 0xC3
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == 0xC000


def test_jp_hl(cpu, mmu):
    cpu.hl = 0xD000
    mmu.mem[0x0100] = 0xE9
    cpu.step()
    assert cpu.pc == 0xD000


@pytest.mark.parametrize("opcode,flag,value,should_jump", [
    (0xC2, "ZERO_FLAG", 0, True),   # JP NZ - jumps when Z clear
    (0xC2, "ZERO_FLAG", 1, False),
    (0xCA, "ZERO_FLAG", 1, True),   # JP Z - jumps when Z set
    (0xD2, "CARRY_FLAG", 0, True),  # JP NC
    (0xDA, "CARRY_FLAG", 1, True),  # JP C
])
def test_jp_conditional(cpu, mmu, opcode, flag, value, should_jump):
    cpu.set_flag(getattr(cpu, flag), value)
    mmu.mem[0x0100] = opcode
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == (0xC000 if should_jump else 0x0103)


def test_jr_forward(cpu, mmu):
    mmu.mem[0x0100] = 0x18
    mmu.mem[0x0101] = 0x05
    cpu.step()
    assert cpu.pc == 0x0107


def test_jr_backward(cpu, mmu):
    cpu.pc = 0x0110
    mmu.mem[0x0110] = 0x18
    mmu.mem[0x0111] = 0xFB  # -5
    cpu.step()
    assert cpu.pc == 0x010D


def test_call_pushes_return_address(cpu, mmu):
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xCD
    mmu.mem[0x0101] = 0x00
    mmu.mem[0x0102] = 0xC0
    cpu.step()
    assert cpu.pc == 0xC000
    assert cpu.sp == 0xFFFC
    assert mmu.mem[0xFFFC] == 0x03
    assert mmu.mem[0xFFFD] == 0x01


def test_ret_pops_return_address(cpu, mmu):
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x03
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = 0xC9
    cpu.step()
    assert cpu.pc == 0x0103
    assert cpu.sp == 0xFFFE


def test_reti_sets_ime(cpu, mmu):
    cpu.sp = 0xFFFC
    mmu.mem[0xFFFC] = 0x00
    mmu.mem[0xFFFD] = 0x01
    mmu.mem[0x0100] = 0xD9
    cpu.step()
    assert cpu.ime is True


def test_rst(cpu, mmu):
    cpu.sp = 0xFFFE
    mmu.mem[0x0100] = 0xEF  # RST 0x28
    cpu.step()
    assert cpu.pc == 0x0028
    assert mmu.mem[0xFFFC] == 0x01
    assert mmu.mem[0xFFFD] == 0x01
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_control_flow.py -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Add control flow to `cpu.py`**

```python
    def _check_cc(self, cc):
        if cc == 0: return self.get_flag(self.ZERO_FLAG) == 0
        if cc == 1: return self.get_flag(self.ZERO_FLAG) == 1
        if cc == 2: return self.get_flag(self.CARRY_FLAG) == 0
        return self.get_flag(self.CARRY_FLAG) == 1
```

Extend `execute` (insert before the final `raise`):

```python
        if opcode == 0xC3:
            self.pc = self.fetch16()
            return 16
        if opcode == 0xE9:
            self.pc = self.hl
            return 4
        if opcode in (0xC2, 0xCA, 0xD2, 0xDA):
            cc = (opcode >> 3) & 0x03
            addr = self.fetch16()
            if self._check_cc(cc):
                self.pc = addr
                return 16
            return 12
        if opcode == 0x18:
            offset = self._signed8(self.fetch8())
            self.pc = (self.pc + offset) & 0xFFFF
            return 12
        if opcode in (0x20, 0x28, 0x30, 0x38):
            cc = (opcode >> 3) & 0x03
            offset = self._signed8(self.fetch8())
            if self._check_cc(cc):
                self.pc = (self.pc + offset) & 0xFFFF
                return 12
            return 8
        if opcode == 0xCD:
            addr = self.fetch16()
            self._push16(self.pc)
            self.pc = addr
            return 24
        if opcode in (0xC4, 0xCC, 0xD4, 0xDC):
            cc = (opcode >> 3) & 0x03
            addr = self.fetch16()
            if self._check_cc(cc):
                self._push16(self.pc)
                self.pc = addr
                return 24
            return 12
        if opcode == 0xC9:
            self.pc = self._pop16()
            return 16
        if opcode in (0xC0, 0xC8, 0xD0, 0xD8):
            cc = (opcode >> 3) & 0x03
            if self._check_cc(cc):
                self.pc = self._pop16()
                return 20
            return 8
        if opcode == 0xD9:
            self.pc = self._pop16()
            self.ime = True
            return 16
        if opcode in (0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF):
            self._push16(self.pc)
            self.pc = opcode & 0x38
            return 16
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_control_flow.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_control_flow.py
git commit -m "feat: jumps, calls, returns, RST"
```

---

### Task 13: CB-prefixed instructions (rotates/shifts/swap, BIT/RES/SET)

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_cb.py`

**Interfaces:**
- Consumes: `_get_r8`/`_set_r8` (Task 7), flag helpers (Task 6).
- Produces: `execute()` handles `0xCB` by fetching a second byte and dispatching to `_execute_cb(cb_opcode)`, which covers `RLC/RRC/RL/RR/SLA/SRA/SWAP/SRL r8` (`0x00-0x3F`) and `BIT/RES/SET b,r8` (`0x40-0xFF`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cpu_cb.py
import pytest


def test_cb_rlc_sets_zero_flag_when_result_zero(cpu, mmu):
    cpu.b = 0x00
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x00  # RLC B
    cpu.step()
    assert cpu.b == 0x00
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_cb_rlc_rotates_and_sets_carry(cpu, mmu):
    cpu.b = 0x85
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x00
    cpu.step()
    assert cpu.b == 0x0B
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cb_swap(cpu, mmu):
    cpu.a = 0xAB
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x37  # SWAP A
    cpu.step()
    assert cpu.a == 0xBA
    assert cpu.get_flag(cpu.CARRY_FLAG) == 0


def test_cb_sla(cpu, mmu):
    cpu.c = 0x80
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x21  # SLA C
    cpu.step()
    assert cpu.c == 0x00
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1
    assert cpu.get_flag(cpu.ZERO_FLAG) == 1


def test_cb_sra_preserves_sign_bit(cpu, mmu):
    cpu.d = 0x81
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x2A  # SRA D
    cpu.step()
    assert cpu.d == 0xC0
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


def test_cb_srl_clears_bit7(cpu, mmu):
    cpu.e = 0x81
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x3B  # SRL E
    cpu.step()
    assert cpu.e == 0x40
    assert cpu.get_flag(cpu.CARRY_FLAG) == 1


@pytest.mark.parametrize("bit,value,expected_zero", [(7, 0x80, 0), (7, 0x00, 1), (0, 0x01, 0)])
def test_cb_bit(cpu, mmu, bit, value, expected_zero):
    cpu.h = value
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x40 | (bit << 3) | 4  # BIT bit,H
    cpu.step()
    assert cpu.get_flag(cpu.ZERO_FLAG) == expected_zero
    assert cpu.get_flag(cpu.HALF_CARRY_FLAG) == 1


def test_cb_res_clears_bit(cpu, mmu):
    cpu.l = 0xFF
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x80 | (3 << 3) | 5  # RES 3,L
    cpu.step()
    assert cpu.l == 0xF7


def test_cb_set_sets_bit(cpu, mmu):
    cpu.l = 0x00
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0xC0 | (3 << 3) | 5  # SET 3,L
    cpu.step()
    assert cpu.l == 0x08


def test_cb_bit_hl_indirect_costs_12_cycles(cpu, mmu):
    cpu.hl = 0xC000
    mmu.mem[0xC000] = 0x80
    mmu.mem[0x0100] = 0xCB
    mmu.mem[0x0101] = 0x46  # BIT 0,(HL)
    cycles = cpu.step()
    assert cycles == 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_cb.py -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Add CB dispatch to `cpu.py`**

```python
    def _cb_rlc(self, value):
        carry = (value >> 7) & 1
        result = ((value << 1) | carry) & 0xFF
        self.set_flag(self.CARRY_FLAG, carry)
        return result

    def _cb_rrc(self, value):
        carry = value & 1
        result = ((value >> 1) | (carry << 7)) & 0xFF
        self.set_flag(self.CARRY_FLAG, carry)
        return result

    def _cb_rl(self, value):
        old_carry = self.get_flag(self.CARRY_FLAG)
        new_carry = (value >> 7) & 1
        result = ((value << 1) | old_carry) & 0xFF
        self.set_flag(self.CARRY_FLAG, new_carry)
        return result

    def _cb_rr(self, value):
        old_carry = self.get_flag(self.CARRY_FLAG)
        new_carry = value & 1
        result = ((value >> 1) | (old_carry << 7)) & 0xFF
        self.set_flag(self.CARRY_FLAG, new_carry)
        return result

    def _cb_sla(self, value):
        carry = (value >> 7) & 1
        result = (value << 1) & 0xFF
        self.set_flag(self.CARRY_FLAG, carry)
        return result

    def _cb_sra(self, value):
        carry = value & 1
        result = ((value >> 1) | (value & 0x80)) & 0xFF
        self.set_flag(self.CARRY_FLAG, carry)
        return result

    def _cb_swap(self, value):
        result = ((value << 4) | (value >> 4)) & 0xFF
        self.set_flag(self.CARRY_FLAG, False)
        return result

    def _cb_srl(self, value):
        carry = value & 1
        result = (value >> 1) & 0xFF
        self.set_flag(self.CARRY_FLAG, carry)
        return result

    _CB_ROTATE_OPS = (_cb_rlc, _cb_rrc, _cb_rl, _cb_rr, _cb_sla, _cb_sra, _cb_swap, _cb_srl)

    def _execute_cb(self, cb_opcode):
        idx = cb_opcode & 0x07
        op_group = (cb_opcode >> 6) & 0x03
        bit = (cb_opcode >> 3) & 0x07
        value = self._get_r8(idx)

        if op_group == 0:  # rotates/shifts/swap
            fn = self._CB_ROTATE_OPS[bit]
            result = fn(self, value)
            self.set_flag(self.ZERO_FLAG, result == 0)
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, False)
            self._set_r8(idx, result)
        elif op_group == 1:  # BIT
            self.set_flag(self.ZERO_FLAG, (value & (1 << bit)) == 0)
            self.set_flag(self.SUB_FLAG, False)
            self.set_flag(self.HALF_CARRY_FLAG, True)
        elif op_group == 2:  # RES
            self._set_r8(idx, value & ~(1 << bit) & 0xFF)
        else:  # SET
            self._set_r8(idx, value | (1 << bit))

        if op_group == 1:
            return 12 if idx == 6 else 8
        return 16 if idx == 6 else 8
```

Extend `execute` (insert before the final `raise`):

```python
        if opcode == 0xCB:
            return self._execute_cb(self.fetch8())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_cb.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full CPU test suite**

Run: `pytest tests/test_cpu_*.py -v`
Expected: all PASS. This confirms the full SM83 instruction set (Tasks 6-13) is implemented and self-consistent.

- [ ] **Step 6: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_cb.py
git commit -m "feat: CB-prefixed instructions (rotates/shifts/swap, BIT/RES/SET)"
```

---

### Task 14: Interrupt servicing in the CPU step loop

**Files:**
- Modify: `gbemulator/core/cpu.py`
- Test: `tests/test_cpu_interrupts.py`

**Interfaces:**
- Consumes: `interrupts.pending_vector`/`.clear` (Task 4), `_push16` (Task 8), `mmu.read`/`write` for `IF`/`IE` (Task 5).
- Produces: `CPU.step()` services a pending, enabled interrupt when `ime` is true (or wakes from `halted` regardless of `ime`), pushing `pc` and jumping to the interrupt vector. Depended on by Task 22 (GameBoy orchestrator — VBlank interrupt drives nothing directly, but Timer/Joypad/PPU interrupts must actually fire during play).

- [ ] **Step 1: Write the failing test**

```python
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
    cpu.step()
    assert cpu.halted is False


def test_interrupt_service_costs_20_cycles(cpu, mmu):
    cpu.ime = True
    mmu.write(0xFFFF, 0xFF)
    interrupts.request(mmu, interrupts.VBLANK)
    cycles = cpu.step()
    assert cycles == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cpu_interrupts.py -v`
Expected: FAIL — no interrupt servicing wired into `step()` yet (PC won't jump, `test_halted_cpu_wakes_on_pending_interrupt_even_if_ime_false` fails).

- [ ] **Step 3: Wire interrupt servicing into `step()`**

Add the import at the top of `cpu.py`:

```python
from . import interrupts
```

Replace `step()`:

```python
    def step(self):
        if self.halted:
            if interrupts.pending_vector(self.mmu) is not None:
                self.halted = False
            else:
                return 4

        if self.ime_pending:
            self.ime = True
            self.ime_pending = False

        if self.ime:
            pending = interrupts.pending_vector(self.mmu)
            if pending is not None:
                bit, vector = pending
                self.ime = False
                interrupts.clear(self.mmu, bit)
                self._push16(self.pc)
                self.pc = vector
                return 20

        opcode = self.fetch8()
        return self.execute(opcode)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cpu_interrupts.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full CPU suite again to check for regressions**

Run: `pytest tests/test_cpu_*.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add gbemulator/core/cpu.py tests/test_cpu_interrupts.py
git commit -m "feat: interrupt servicing in CPU step loop"
```

---

### Task 15: Timer (DIV/TIMA/TMA/TAC)

**Files:**
- Create: `gbemulator/core/timer.py`
- Modify: `gbemulator/core/mmu.py`
- Test: `tests/test_timer.py`

**Interfaces:**
- Consumes: `interrupts.request` (Task 4), MMU with public `.mem` (Task 5).
- Produces: `Timer(mmu)` with `.tick(cycles)` and `.reset_div()`; `MMU.write` already special-cases `0xFF04` (Task 5) to call `mmu.timer.reset_div()` once `mmu.timer` is set. Depended on by Task 21 (GameBoy orchestrator ticks the timer every frame loop iteration).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_timer.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_timer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.timer'`.

- [ ] **Step 3: Write `timer.py`**

```python
# gbemulator/core/timer.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_timer.py -v`
Expected: all PASS (`MMU.write`'s `0xFF04` special-case from Task 5 already routes to `timer.reset_div()`).

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/timer.py tests/test_timer.py
git commit -m "feat: timer (DIV/TIMA/TMA/TAC)"
```

---

### Task 16: Joypad

**Files:**
- Create: `gbemulator/core/joypad.py`
- Test: `tests/test_joypad.py`

**Interfaces:**
- Consumes: `interrupts.request` (Task 4), MMU (Task 5, already delegates `0xFF00` to `mmu.joypad` when set).
- Produces: `Joypad(mmu)` with `.read()`, `.write(value)`, `.set_button(name, pressed)` for names `up/down/left/right/a/b/select/start`. Depended on by Task 23 (pygame frontend forwards key events) and Task 21 (GameBoy orchestrator wires `mmu.joypad = joypad`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_joypad.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_joypad.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.joypad'`.

- [ ] **Step 3: Write `joypad.py`**

```python
# gbemulator/core/joypad.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_joypad.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/joypad.py tests/test_joypad.py
git commit -m "feat: joypad input handling"
```

---

### Task 17: PPU skeleton (mode timing state machine)

**Files:**
- Create: `gbemulator/core/ppu.py`
- Test: `tests/test_ppu_timing.py`

**Interfaces:**
- Consumes: `interrupts.request` (Task 4), MMU with public `.mem` (Task 5).
- Produces: `PPU(mmu)` with `.tick(cycles)`, `.framebuffer` (numpy `uint8` array, shape `(144, 160)`, values 0-3), `.frame_ready` (bool, set on entering VBlank, cleared by caller), and mode constants `MODE_OAM=2, MODE_TRANSFER=3, MODE_HBLANK=0, MODE_VBLANK=1`. `LY` (`0xFF44`) is updated as scanlines advance; STAT (`0xFF41`) low 2 bits reflect current mode; VBlank interrupt requested on entering line 144. `_render_scanline()` is a no-op stub — filled in by Tasks 18-20. Depended on by Task 21 (GameBoy orchestrator).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ppu_timing.py
from gbemulator.core.ppu import PPU
from gbemulator.core import interrupts


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def test_starts_in_oam_mode():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    assert ppu.mode == PPU.MODE_OAM


def test_transitions_oam_to_transfer_after_80_cycles():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(80)
    assert ppu.mode == PPU.MODE_TRANSFER


def test_transitions_transfer_to_hblank_after_172_more_cycles():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(80)
    ppu.tick(172)
    assert ppu.mode == PPU.MODE_HBLANK


def test_full_scanline_advances_ly_and_returns_to_oam():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    ppu.tick(456)  # one full scanline: 80 + 172 + 204
    assert mmu.mem[0xFF44] == 1
    assert ppu.mode == PPU.MODE_OAM


def test_144th_scanline_enters_vblank_and_requests_interrupt():
    mmu = FakeMMU()
    mmu.write(0xFFFF, 0xFF)
    ppu = PPU(mmu)
    for _ in range(144):
        ppu.tick(456)
    assert ppu.mode == PPU.MODE_VBLANK
    assert ppu.frame_ready is True
    assert mmu.read(0xFF0F) & interrupts.VBLANK == interrupts.VBLANK


def test_after_154_scanlines_wraps_to_line_0_and_oam():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    for _ in range(154):
        ppu.tick(456)
    assert mmu.mem[0xFF44] == 0
    assert ppu.mode == PPU.MODE_OAM


def test_framebuffer_shape():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    assert ppu.framebuffer.shape == (144, 160)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ppu_timing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.ppu'`.

- [ ] **Step 3: Write `ppu.py`**

```python
# gbemulator/core/ppu.py
import numpy as np

from . import interrupts

LY_ADDR = 0xFF44
STAT_ADDR = 0xFF41


class PPU:
    MODE_HBLANK = 0
    MODE_VBLANK = 1
    MODE_OAM = 2
    MODE_TRANSFER = 3

    def __init__(self, mmu):
        self.mmu = mmu
        self.mode = self.MODE_OAM
        self.mode_clock = 0
        self.ly = 0
        self.frame_ready = False
        self.framebuffer = np.zeros((144, 160), dtype=np.uint8)
        self._update_stat()

    def _update_stat(self):
        stat = self.mmu.mem[STAT_ADDR]
        self.mmu.mem[STAT_ADDR] = (stat & 0xFC) | (self.mode & 0x03)

    def tick(self, cycles):
        self.mode_clock += cycles
        if self.mode == self.MODE_OAM:
            if self.mode_clock >= 80:
                self.mode_clock -= 80
                self.mode = self.MODE_TRANSFER
        elif self.mode == self.MODE_TRANSFER:
            if self.mode_clock >= 172:
                self.mode_clock -= 172
                self.mode = self.MODE_HBLANK
                self._render_scanline()
        elif self.mode == self.MODE_HBLANK:
            if self.mode_clock >= 204:
                self.mode_clock -= 204
                self._advance_line()
                if self.ly == 144:
                    self.mode = self.MODE_VBLANK
                    interrupts.request(self.mmu, interrupts.VBLANK)
                    self.frame_ready = True
                else:
                    self.mode = self.MODE_OAM
        elif self.mode == self.MODE_VBLANK:
            if self.mode_clock >= 456:
                self.mode_clock -= 456
                self._advance_line()
                if self.ly > 153:
                    self.ly = 0
                    self.mmu.mem[LY_ADDR] = 0
                    self.mode = self.MODE_OAM
        self._update_stat()

    def _advance_line(self):
        self.ly += 1
        self.mmu.mem[LY_ADDR] = self.ly & 0xFF

    def _render_scanline(self):
        pass  # filled in by Tasks 18-20
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ppu_timing.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/ppu.py tests/test_ppu_timing.py
git commit -m "feat: PPU mode timing state machine"
```

---

### Task 18: PPU background rendering

**Files:**
- Modify: `gbemulator/core/ppu.py`
- Test: `tests/test_ppu_background.py`

**Interfaces:**
- Consumes: `PPU` skeleton (Task 17): `.framebuffer`, `.ly`, `.mmu.mem`.
- Produces: `PPU._decode_tile_row(low_byte, high_byte)` returning a list of 8 color indices (0-3, MSB-first); `PPU._render_background_row()` called from `_render_scanline()` when LCDC bit 0 is set, reading LCDC (`0xFF40`), SCX/SCY (`0xFF43`/`0xFF42`), BGP (`0xFF47`), writing palette-applied shades into `framebuffer[ly]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ppu_background.py
from gbemulator.core.ppu import PPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def _set_tile(mmu, tile_index, rows):
    """rows: list of 8 (low_byte, high_byte) tuples, unsigned tile data at 0x8000."""
    base = 0x8000 + tile_index * 16
    for i, (lo, hi) in enumerate(rows):
        mmu.mem[base + i * 2] = lo
        mmu.mem[base + i * 2 + 1] = hi


def test_decode_tile_row_msb_first():
    mmu = FakeMMU()
    ppu = PPU(mmu)
    # low=0b10000001, high=0b11000011 -> pixel0: hi=1,lo=1->3; pixel7: hi=1,lo=1->3
    pixels = ppu._decode_tile_row(0b10000001, 0b11000011)
    assert pixels[0] == 3
    assert pixels[7] == 3
    assert pixels[1] == 2  # hi=1,lo=0


def test_background_row_uses_tile_data_and_palette():
    mmu = FakeMMU()
    # Tile 0: solid color index 3 on every pixel of row 0
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    # BG tilemap at 0x9800: all tile index 0
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
    mmu.mem[0xFF40] = 0x91  # LCDC: BG enabled (bit0), tile data 0x8000 (bit4), BG map 0x9800 (bit3=0)
    mmu.mem[0xFF47] = 0xE4  # BGP: identity mapping (00->0,01->1,10->2,11->3)
    mmu.mem[0xFF42] = 0  # SCY
    mmu.mem[0xFF43] = 0  # SCX
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    assert ppu.framebuffer[0][0] == 3
    assert ppu.framebuffer[0][7] == 3


def test_background_row_respects_scroll():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # tile 0: all color 0
    _set_tile(mmu, 1, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # tile 1: row0 all color 3
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
    mmu.mem[0x9800 + 1] = 1  # second tile in the map is tile 1
    mmu.mem[0xFF40] = 0x91
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF42] = 0
    mmu.mem[0xFF43] = 8  # scroll right by 8 -> first visible tile is map tile index 1
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    assert ppu.framebuffer[0][0] == 3


def test_background_disabled_leaves_framebuffer_blank():
    mmu = FakeMMU()
    mmu.mem[0xFF40] = 0x90  # bit0 (BG enable) clear
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu.tick(456)  # runs a full scanline through _render_scanline
    assert ppu.framebuffer[0][0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ppu_background.py -v`
Expected: FAIL — `AttributeError: 'PPU' object has no attribute '_decode_tile_row'`.

- [ ] **Step 3: Add background rendering to `ppu.py`**

```python
    def _decode_tile_row(self, low_byte, high_byte):
        return [
            (((high_byte >> (7 - i)) & 1) << 1) | ((low_byte >> (7 - i)) & 1)
            for i in range(8)
        ]

    def _apply_palette(self, color_index, palette_byte):
        return (palette_byte >> (color_index * 2)) & 0x03

    def _render_background_row(self):
        lcdc = self.mmu.mem[0xFF40]
        if not (lcdc & 0x01):
            return
        scy = self.mmu.mem[0xFF42]
        scx = self.mmu.mem[0xFF43]
        bgp = self.mmu.mem[0xFF47]
        tile_map_base = 0x9C00 if (lcdc & 0x08) else 0x9800
        tile_data_signed = not (lcdc & 0x10)

        y = (self.ly + scy) & 0xFF
        tile_row = y // 8
        pixel_row = y % 8

        for screen_x in range(160):
            x = (screen_x + scx) & 0xFF
            tile_col = x // 8
            pixel_col = x % 8

            map_index = tile_map_base + tile_row * 32 + tile_col
            tile_index = self.mmu.mem[map_index]
            if tile_data_signed:
                signed_index = tile_index - 256 if tile_index > 127 else tile_index
                tile_addr = 0x9000 + signed_index * 16
            else:
                tile_addr = 0x8000 + tile_index * 16

            row_addr = tile_addr + pixel_row * 2
            low_byte = self.mmu.mem[row_addr]
            high_byte = self.mmu.mem[row_addr + 1]
            color_index = self._decode_tile_row(low_byte, high_byte)[pixel_col]
            self.framebuffer[self.ly][screen_x] = self._apply_palette(color_index, bgp)

    def _render_scanline(self):
        self._render_background_row()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ppu_background.py tests/test_ppu_timing.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/ppu.py tests/test_ppu_background.py
git commit -m "feat: PPU background layer rendering"
```

---

### Task 19: PPU window rendering

**Files:**
- Modify: `gbemulator/core/ppu.py`
- Test: `tests/test_ppu_window.py`

**Interfaces:**
- Consumes: `_decode_tile_row`, `_apply_palette` (Task 18).
- Produces: `PPU._render_window_row()`, called from `_render_scanline()` after the background, drawing over background pixels when LCDC bit 5 is set and `ly >= WY` and `screen_x >= WX - 7`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ppu_window.py
from gbemulator.core.ppu import PPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def _set_tile(mmu, tile_index, rows):
    base = 0x8000 + tile_index * 16
    for i, (lo, hi) in enumerate(rows):
        mmu.mem[base + i * 2] = lo
        mmu.mem[base + i * 2 + 1] = hi


def test_window_drawn_when_enabled_and_within_bounds():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # bg tile: color 0
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # window tile: row0 color 3
    for i in range(32):
        mmu.mem[0x9800 + i] = 0  # BG map all tile 0
        mmu.mem[0x9C00 + i] = 5  # window map all tile 5
    mmu.mem[0xFF40] = 0xF1  # LCDC: BG on, window on (bit5), window map 0x9C00 (bit6), tile data 0x8000 (bit4)
    mmu.mem[0xFF47] = 0xE4  # BGP identity
    mmu.mem[0xFF4A] = 0  # WY = 0
    mmu.mem[0xFF4B] = 7  # WX = 7 -> window starts at screen x=0
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 3


def test_window_not_drawn_above_wy():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
        mmu.mem[0x9C00 + i] = 5
    mmu.mem[0xFF40] = 0xF1
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF4A] = 10  # WY = 10, window hasn't started at ly=0
    mmu.mem[0xFF4B] = 7
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 0


def test_window_disabled_leaves_background():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)
    _set_tile(mmu, 5, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    for i in range(32):
        mmu.mem[0x9800 + i] = 0
        mmu.mem[0x9C00 + i] = 5
    mmu.mem[0xFF40] = 0x91  # window disabled (bit5 clear)
    mmu.mem[0xFF47] = 0xE4
    mmu.mem[0xFF4A] = 0
    mmu.mem[0xFF4B] = 7
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_background_row()
    ppu._render_window_row()
    assert ppu.framebuffer[0][0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ppu_window.py -v`
Expected: FAIL — `AttributeError: 'PPU' object has no attribute '_render_window_row'`.

- [ ] **Step 3: Add window rendering to `ppu.py`**

```python
    def _render_window_row(self):
        lcdc = self.mmu.mem[0xFF40]
        if not (lcdc & 0x20):
            return
        wy = self.mmu.mem[0xFF4A]
        wx = self.mmu.mem[0xFF4B]
        if self.ly < wy:
            return

        bgp = self.mmu.mem[0xFF47]
        tile_map_base = 0x9C00 if (lcdc & 0x40) else 0x9800
        tile_data_signed = not (lcdc & 0x10)

        window_y = self.ly - wy
        tile_row = window_y // 8
        pixel_row = window_y % 8

        for screen_x in range(160):
            window_x = screen_x - (wx - 7)
            if window_x < 0:
                continue
            tile_col = window_x // 8
            pixel_col = window_x % 8

            map_index = tile_map_base + tile_row * 32 + tile_col
            tile_index = self.mmu.mem[map_index]
            if tile_data_signed:
                signed_index = tile_index - 256 if tile_index > 127 else tile_index
                tile_addr = 0x9000 + signed_index * 16
            else:
                tile_addr = 0x8000 + tile_index * 16

            row_addr = tile_addr + pixel_row * 2
            low_byte = self.mmu.mem[row_addr]
            high_byte = self.mmu.mem[row_addr + 1]
            color_index = self._decode_tile_row(low_byte, high_byte)[pixel_col]
            self.framebuffer[self.ly][screen_x] = self._apply_palette(color_index, bgp)
```

Update `_render_scanline`:

```python
    def _render_scanline(self):
        self._render_background_row()
        self._render_window_row()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ppu_window.py tests/test_ppu_background.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/ppu.py tests/test_ppu_window.py
git commit -m "feat: PPU window layer rendering"
```

---

### Task 20: PPU sprite rendering

**Files:**
- Modify: `gbemulator/core/ppu.py`
- Test: `tests/test_ppu_sprites.py`

**Interfaces:**
- Consumes: `_decode_tile_row` (Task 18), OAM at `0xFE00-0xFE9F` (4 bytes/entry: Y, X, tile index, attributes).
- Produces: `PPU._render_sprites_row()`, called last from `_render_scanline()`, supporting 8x8 sprites (LCDC bit 2 = 0) and 8x16 (bit 2 = 1), X/Y flip, OBP0/OBP1 palette select, and background priority (attribute bit 7).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ppu_sprites.py
from gbemulator.core.ppu import PPU


class FakeMMU:
    def __init__(self):
        self.mem = bytearray(0x10000)

    def read(self, addr):
        return self.mem[addr]

    def write(self, addr, value):
        self.mem[addr] = value & 0xFF


def _set_tile(mmu, tile_index, rows):
    base = 0x8000 + tile_index * 16
    for i, (lo, hi) in enumerate(rows):
        mmu.mem[base + i * 2] = lo
        mmu.mem[base + i * 2 + 1] = hi


def _set_sprite(mmu, slot, y, x, tile, attrs):
    base = 0xFE00 + slot * 4
    mmu.mem[base] = y
    mmu.mem[base + 1] = x
    mmu.mem[base + 2] = tile
    mmu.mem[base + 3] = attrs


def test_sprite_drawn_at_correct_position():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)  # row0 color 3
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)  # screen pos: y=0, x=0
    mmu.mem[0xFF40] = 0x93  # LCDC: BG+sprites enabled, 8x8 sprites
    mmu.mem[0xFF48] = 0xE4  # OBP0 identity
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 3


def test_sprite_off_screen_not_drawn():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    _set_sprite(mmu, 0, y=0, x=8, tile=0, attrs=0x00)  # y=16-16=0 -> off top of screen
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 0


def test_sprite_color_0_is_transparent():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0x00, 0x00)] * 8)  # all color 0
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu.framebuffer[0][0] = 2  # pre-existing background pixel
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 2  # untouched, sprite pixel was transparent


def test_sprites_disabled_via_lcdc():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0xFF, 0xFF)] + [(0x00, 0x00)] * 7)
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x00)
    mmu.mem[0xFF40] = 0x91  # bit1 (sprite enable) clear
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][0] == 0


def test_x_flip_mirrors_tile_row():
    mmu = FakeMMU()
    _set_tile(mmu, 0, [(0b10000000, 0b10000000)] + [(0x00, 0x00)] * 7)  # only pixel0 = color3
    _set_sprite(mmu, 0, y=16, x=8, tile=0, attrs=0x20)  # bit5 = x-flip
    mmu.mem[0xFF40] = 0x93
    mmu.mem[0xFF48] = 0xE4
    ppu = PPU(mmu)
    ppu.ly = 0
    ppu._render_sprites_row()
    assert ppu.framebuffer[0][7] == 3  # flipped from position 0 to position 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ppu_sprites.py -v`
Expected: FAIL — `AttributeError: 'PPU' object has no attribute '_render_sprites_row'`.

- [ ] **Step 3: Add sprite rendering to `ppu.py`**

```python
    def _render_sprites_row(self):
        lcdc = self.mmu.mem[0xFF40]
        if not (lcdc & 0x02):
            return
        sprite_height = 16 if (lcdc & 0x04) else 8

        sprites_on_line = []
        for slot in range(40):
            base = 0xFE00 + slot * 4
            sprite_y = self.mmu.mem[base] - 16
            if sprite_y <= self.ly < sprite_y + sprite_height:
                sprites_on_line.append(slot)
            if len(sprites_on_line) == 10:
                break

        for slot in reversed(sprites_on_line):
            base = 0xFE00 + slot * 4
            sprite_y = self.mmu.mem[base] - 16
            sprite_x = self.mmu.mem[base + 1] - 8
            tile_index = self.mmu.mem[base + 2]
            attrs = self.mmu.mem[base + 3]
            y_flip = bool(attrs & 0x40)
            x_flip = bool(attrs & 0x20)
            palette_addr = 0xFF49 if (attrs & 0x10) else 0xFF48
            palette = self.mmu.mem[palette_addr]

            if sprite_height == 16:
                tile_index &= 0xFE

            row_in_sprite = self.ly - sprite_y
            if y_flip:
                row_in_sprite = sprite_height - 1 - row_in_sprite

            tile_addr = 0x8000 + tile_index * 16 + row_in_sprite * 2
            low_byte = self.mmu.mem[tile_addr]
            high_byte = self.mmu.mem[tile_addr + 1]
            pixels = self._decode_tile_row(low_byte, high_byte)
            if x_flip:
                pixels = pixels[::-1]

            for col in range(8):
                screen_x = sprite_x + col
                if not (0 <= screen_x < 160):
                    continue
                color_index = pixels[col]
                if color_index == 0:
                    continue  # transparent
                self.framebuffer[self.ly][screen_x] = self._apply_palette(color_index, palette)
```

Update `_render_scanline`:

```python
    def _render_scanline(self):
        self._render_background_row()
        self._render_window_row()
        self._render_sprites_row()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ppu_sprites.py tests/test_ppu_window.py tests/test_ppu_background.py tests/test_ppu_timing.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/ppu.py tests/test_ppu_sprites.py
git commit -m "feat: PPU sprite layer rendering"
```

---

### Task 21: GameBoy orchestrator

**Files:**
- Create: `gbemulator/core/gameboy.py`
- Test: `tests/test_gameboy.py`
- Test fixture: `tests/fixtures/tiny_rom.gb` (generated inline by the test, not committed as a binary — see Step 1)

**Interfaces:**
- Consumes: `Cartridge` (Task 2), `MMU` (Task 5), `CPU` (Tasks 6-14), `PPU` (Tasks 17-20), `Timer` (Task 15), `Joypad` (Task 16).
- Produces: `GameBoy(rom_path)` with `.cartridge`, `.mmu`, `.cpu`, `.ppu`, `.timer`, `.joypad`, and `.run_frame()` returning the completed `framebuffer`. Depended on by Task 22 (Blargg harness) and Task 23 (pygame frontend).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gameboy.py
import struct
import pytest

from gbemulator.core.gameboy import GameBoy


def _write_tiny_rom(path):
    rom = bytearray(32 * 1024)
    # A tight loop: 0x0100: JP 0x0150 ; 0x0150: infinite JR -2 (spins forever, one instruction per step)
    rom[0x100] = 0xC3
    rom[0x101] = 0x50
    rom[0x102] = 0x01
    rom[0x150] = 0x18  # JR
    rom[0x151] = 0xFE  # -2, jumps to itself
    rom[0x147] = 0x00  # ROM-only
    rom[0x148] = 0x00
    rom[0x149] = 0x00
    with open(path, "wb") as f:
        f.write(rom)


@pytest.fixture
def tiny_rom_path(tmp_path):
    path = tmp_path / "tiny.gb"
    _write_tiny_rom(path)
    return str(path)


def test_gameboy_loads_rom_and_wires_components(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    assert gb.cpu.mmu is gb.mmu
    assert gb.mmu.joypad is gb.joypad
    assert gb.mmu.timer is gb.timer


def test_run_frame_returns_completed_framebuffer(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    framebuffer = gb.run_frame()
    assert framebuffer.shape == (144, 160)


def test_run_frame_advances_ppu_a_full_frame_worth_of_cycles(tiny_rom_path):
    gb = GameBoy(tiny_rom_path)
    gb.run_frame()
    assert gb.ppu.frame_ready is False  # reset after being consumed by run_frame
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gameboy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.core.gameboy'`.

- [ ] **Step 3: Write `gameboy.py`**

```python
# gbemulator/core/gameboy.py
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
        return self.ppu.framebuffer
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gameboy.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add gbemulator/core/gameboy.py tests/test_gameboy.py
git commit -m "feat: GameBoy orchestrator wiring CPU/PPU/timer/joypad"
```

---

### Task 22: Blargg `cpu_instrs` integration test

**Files:**
- Modify: `gbemulator/core/mmu.py`
- Test: `tests/test_blargg.py`
- Create: `roms/blargg/README.md` (download instructions — the ROM itself is not committed as a binary in this task)

**Interfaces:**
- Consumes: `GameBoy` (Task 21).
- Produces: `MMU.serial_output` (list of ints) capturing bytes written via the serial port protocol (`0xFF01` then `0xFF02=0x81`), used by the test to detect Blargg's `Passed`/`Failed` text without a display.

- [ ] **Step 1: Add serial capture to `mmu.py`**

```python
    def __init__(self, cartridge):
        self.cartridge = cartridge
        self.mem = bytearray(0x10000)
        self.joypad = None
        self.timer = None
        self.serial_output = []
```

Add to `write()`, before the final `self.mem[addr] = value` line:

```python
        if addr == 0xFF02 and value == 0x81:
            self.serial_output.append(self.mem[0xFF01])
            self.mem[addr] = 0
            return
```

- [ ] **Step 2: Add a unit test for the serial hook (fast, no ROM needed)**

```python
# tests/test_mmu.py  (append)
def test_serial_output_captured_on_0x81_write():
    mmu = MMU(FakeCartridge())
    mmu.write(0xFF01, ord("A"))
    mmu.write(0xFF02, 0x81)
    assert mmu.serial_output == [ord("A")]
```

Run: `pytest tests/test_mmu.py -v`
Expected: FAIL first (no `serial_output` yet — confirms the test exercises new behavior), then PASS after Step 1's implementation is in place.

- [ ] **Step 3: Write `roms/blargg/README.md` with download instructions**

```markdown
# Blargg Test ROMs

This directory intentionally does not commit ROM binaries. To run
`tests/test_blargg.py`, download `cpu_instrs.gb` from Blargg's test ROM
suite (search "blargg gb-test-roms cpu_instrs", widely mirrored on
GitHub as freely redistributable test ROMs) and place it at:

    roms/blargg/cpu_instrs.gb

`tests/test_blargg.py` skips itself automatically if the file is absent.
```

- [ ] **Step 4: Write the Blargg integration test**

```python
# tests/test_blargg.py
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
```

- [ ] **Step 5: Run the fast unit test to verify it passes**

Run: `pytest tests/test_mmu.py -v`
Expected: all PASS.

- [ ] **Step 6: Run the Blargg test (skips cleanly if the ROM isn't downloaded)**

Run: `pytest tests/test_blargg.py -v`
Expected: `SKIPPED` if `roms/blargg/cpu_instrs.gb` is absent, or `PASSED` if present and the CPU implementation (Tasks 6-14) is correct. If it prints `Failed` output instead, use the printed serial text (Blargg names the specific failing instruction/test number) to debug the relevant CPU task before proceeding.

- [ ] **Step 7: Commit**

```bash
git add gbemulator/core/mmu.py tests/test_mmu.py tests/test_blargg.py roms/blargg/README.md
git commit -m "feat: serial output capture and Blargg cpu_instrs integration test"
```

---

### Task 23: pygame frontend

**Files:**
- Create: `gbemulator/frontend/pygame_app.py`
- Test: `tests/test_pygame_app.py`

**Interfaces:**
- Consumes: `GameBoy` (Task 21), `Joypad.set_button` (Task 16).
- Produces: `KEY_MAP` (dict of pygame key constant -> button name), `SHADE_COLORS` (list of 4 RGB tuples), `framebuffer_to_rgb(framebuffer)` (pure function, numpy `(144,160)` uint8 -> `(160,144,3)` uint8, testable without a display), and `run(rom_path)` (opens a window and runs the main loop — not exercised by automated tests, since it requires a real display).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pygame_app.py
import numpy as np

from gbemulator.frontend.pygame_app import framebuffer_to_rgb, SHADE_COLORS


def test_framebuffer_to_rgb_maps_shades_to_colors():
    framebuffer = np.zeros((144, 160), dtype=np.uint8)
    framebuffer[0][0] = 3
    rgb = framebuffer_to_rgb(framebuffer)
    assert rgb.shape == (160, 144, 3)
    assert tuple(rgb[0][0]) == SHADE_COLORS[3]
    assert tuple(rgb[1][0]) == SHADE_COLORS[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pygame_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gbemulator.frontend.pygame_app'`.

- [ ] **Step 3: Write `pygame_app.py`**

```python
# gbemulator/frontend/pygame_app.py
import sys

import numpy as np
import pygame

from ..core.gameboy import GameBoy

SCALE = 3
SHADE_COLORS = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]
_PALETTE_LUT = np.array(SHADE_COLORS, dtype=np.uint8)

KEY_MAP = {
    pygame.K_RIGHT: "right",
    pygame.K_LEFT: "left",
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_x: "a",
    pygame.K_z: "b",
    pygame.K_SPACE: "select",
    pygame.K_RETURN: "start",
}


def framebuffer_to_rgb(framebuffer):
    rgb = _PALETTE_LUT[framebuffer]  # (144, 160, 3)
    return rgb.swapaxes(0, 1)  # pygame surfarray expects (width, height, 3)


def run(rom_path):
    gb = GameBoy(rom_path)
    pygame.init()
    screen = pygame.display.set_mode((160 * SCALE, 144 * SCALE))
    pygame.display.set_caption("gbemulator")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in KEY_MAP:
                gb.joypad.set_button(KEY_MAP[event.key], True)
            elif event.type == pygame.KEYUP and event.key in KEY_MAP:
                gb.joypad.set_button(KEY_MAP[event.key], False)

        framebuffer = gb.run_frame()
        rgb = framebuffer_to_rgb(framebuffer)
        surface = pygame.surfarray.make_surface(rgb)
        surface = pygame.transform.scale(surface, (160 * SCALE, 144 * SCALE))
        screen.blit(surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run(sys.argv[1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pygame_app.py -v`
Expected: PASS. (`pygame.init()`/display are not invoked by this test — only the pure `framebuffer_to_rgb` function is exercised, so it runs headless.)

- [ ] **Step 5: Commit**

```bash
git add gbemulator/frontend/pygame_app.py tests/test_pygame_app.py
git commit -m "feat: pygame frontend with framebuffer rendering and input"
```

---

### Task 24: Full test suite run and manual smoke test

**Files:**
- None created — verification-only task.

**Interfaces:**
- Consumes: everything from Tasks 1-23.

- [ ] **Step 1: Run the complete automated test suite**

Run: `pytest -v`
Expected: all tests PASS (or SKIPPED only for `test_blargg.py` if the ROM wasn't downloaded).

- [ ] **Step 2: If `roms/blargg/cpu_instrs.gb` is available, confirm it passes**

Run: `pytest tests/test_blargg.py -v -s`
Expected: PASSED, with `Passed` visible if you inspect the captured serial output.

- [ ] **Step 3: Manual smoke test with a public-domain/homebrew ROM**

Obtain a public-domain or homebrew `.gb` ROM (e.g. from itch.io's homebrew Game Boy game listings) and run:

```bash
python -m gbemulator.frontend.pygame_app path/to/homebrew.gb
```

Expected: a window opens showing Game Boy graphics; arrow keys/Z/X/Enter/Space control the game per `KEY_MAP` in `pygame_app.py`.

- [ ] **Step 4: Note any visual bugs for follow-up**

If sprites/background/window look wrong, note the specific symptom (e.g. "sprites offset by one tile," "window not appearing") — this is expected debugging territory for a first-pass PPU implementation and is out of scope to fix speculatively in this plan. File it as a follow-up rather than guessing at a fix.

---
