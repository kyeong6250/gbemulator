# Game Boy Emulator — Design Spec

Date: 2026-08-17

## Goal

Build a Game Boy (DMG) emulator in Python, inspired by [geaz/emu-gameboy](https://github.com/geaz/emu-gameboy) (a C++ Game Boy emulator). This is a learning/programming-experience project, not a daily-use emulator — it targets correctness good enough to pass standard test ROMs and run simple/homebrew games, not perfect hardware-accurate emulation.

## Scope

**In scope (v1):**
- SM83 (LR35902) CPU: full instruction set including CB-prefixed bit operations, interrupts
- Memory bus (MMU): ROM/RAM banks, VRAM, WRAM, OAM, I/O registers, HRAM, IE register
- Cartridge support: ROM-only (32KB, no bank switching) and MBC1 (bank switching)
- PPU (graphics): scanline-based renderer producing a 160×144 framebuffer — background, window, and sprite layers
- Timer: DIV/TIMA/TMA/TAC registers and timer interrupt
- Joypad input
- Interrupt controller: VBlank, LCD STAT, Timer, Serial, Joypad
- pygame-based frontend: window, framebuffer display, keyboard input, 60fps throttling

**Out of scope (v1) — explicitly deferred:**
- APU / sound emulation
- MBC2, MBC3, MBC5, or other mappers beyond MBC1
- Cycle-accurate (T-state) CPU/PPU timing
- Save states, debugger UI, rewind
- Game Boy Color (CGB) features

## Timing model

Instruction-stepped synchronization, matching the reference project's approach: the CPU executes one instruction via `step()`, returning the number of cycles consumed. The PPU, timer, and interrupt controller are then advanced by that many cycles. This is simpler to implement and debug than full T-state-level cycle accuracy, at the cost of not perfectly emulating a handful of timing-sensitive games/effects. Sufficient for standard test ROMs and most simple/homebrew games.

## Architecture

A clean split between a pure emulation **core** (no I/O dependencies, fully testable headlessly) and a thin **frontend** (pygame) that displays frames and forwards input events. This allows unit tests and Blargg-ROM correctness tests to run without opening a window or requiring a display.

```
Cartridge/MBC → MMU (bus) ← CPU
                   ↑           ↓ step() cycles
                 PPU/Timer/Joypad/Interrupts (advanced by cycles)
                   ↓
             Framebuffer (160x144)
                   ↓
         pygame frontend (blit + input polling)
```

## Components

- **`Cartridge` / `MBC`** — parses the ROM header (title, cartridge type, ROM/RAM size), dispatches reads/writes through the correct mapper: `NoMBC` (ROM-only) or `MBC1` (bank switching for ROM and optionally RAM).
- **`MMU`** — single address-space router mapping CPU reads/writes to the correct backing store: cartridge ROM/RAM (via MBC), VRAM (0x8000-0x9FFF), WRAM (0xC000-0xDFFF), OAM (0xFE00-0xFE9F), I/O registers (0xFF00-0xFF7F), HRAM (0xFF80-0xFFFE), IE register (0xFFFF).
- **`CPU`** — SM83 registers (A, F, B, C, D, E, H, L, SP, PC) and flags; full opcode table including CB-prefixed bit operations; `step()` fetches/decodes/executes one instruction, handles pending interrupt dispatch, and returns cycles taken.
- **`PPU`** — scanline-based state machine cycling through OAM Search → Pixel Transfer → HBlank per scanline, and VBlank after the visible 144 lines; renders background, window, and sprite layers into a 160×144 framebuffer; sets LCD STAT and requests VBlank/STAT interrupts.
- **`Timer`** — DIV (divider), TIMA (counter), TMA (modulo), TAC (control) registers; requests a timer interrupt on TIMA overflow.
- **`Joypad`** — maps pygame key events (arrows, Z/X, Enter, Space) to the joypad I/O register (0xFF00) and requests joypad interrupts.
- **`GameBoy`** — top-level orchestrator. `run_frame()` loops `cpu.step()`, advancing PPU/timer/joypad by the returned cycle count and servicing interrupts, until the PPU signals a completed frame (VBlank).

## Data flow

1. Frontend calls `gameboy.run_frame()`.
2. Loop: `cpu.step()` executes one instruction → returns cycle count.
3. PPU, timer, and joypad are advanced by that cycle count; any requested interrupts are queued.
4. CPU checks/services pending interrupts at each `step()` boundary (if IME is enabled).
5. Loop continues until the PPU completes a full frame (enters VBlank).
6. Frontend blits the 160×144 framebuffer to the pygame window, polls keyboard input, updates the joypad register, and throttles to 60fps.

## Project structure

```
gbemulator/
  core/
    cpu.py          # SM83 registers, flags, step()
    opcodes.py       # opcode table + implementations
    mmu.py           # memory bus/routing
    ppu.py           # PPU state machine + framebuffer
    timer.py
    joypad.py
    interrupts.py
    cartridge.py      # ROM header parsing
    mbc.py            # NoMBC + MBC1
    gameboy.py         # top-level orchestrator
  frontend/
    pygame_app.py       # window, input polling, 60fps throttle
  tests/
    test_cpu_*.py        # per opcode-group unit tests
    test_blargg.py        # runs Blargg ROMs headlessly, asserts pass/fail
  roms/
    blargg/               # Blargg test ROMs (freely redistributable)
  main.py                  # entry point: loads ROM, runs GameBoy + frontend
```

## Testing strategy

`core/` has zero pygame dependency, so all correctness tests run headless:

- **Unit tests** (TDD, module by module): opcode groups (8-bit/16-bit loads, arithmetic, jumps/calls, CB-prefixed bit operations) tested against documented SM83 behavior — write a failing test, implement, repeat.
- **Integration tests**: run Blargg's test ROMs (`cpu_instrs`, `instr_timing`, etc.) for a bounded number of cycles and assert on the pass/fail text Blargg writes to memory (0xA000) or serial output. No visual inspection required.

## Error handling

- Unknown/unimplemented opcode → raise immediately with PC and opcode value logged. Fail loud during bring-up rather than silently corrupting state.
- Unsupported cartridge/MBC type in the ROM header → raise a clear error at load time.
- No handling for malformed/corrupt ROM dumps beyond header validation — out of scope; the emulator is developed and tested against known-good ROMs (Blargg test ROMs, public-domain/homebrew ROMs).

## Legal note on ROMs

No copyrighted commercial game ROMs will be included in the repository. Test ROMs used are Blargg's (freely redistributable for this purpose) and/or public-domain/homebrew ROMs.
