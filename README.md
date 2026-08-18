# gbemulator

A Game Boy (DMG) emulator written in Python, inspired by [geaz/emu-gameboy](https://github.com/geaz/emu-gameboy).

## Run (Windows, easiest)

Double-click `gbemulator.bat`. It checks for Python, installs dependencies on
first run if needed, then launches the emulator. If you don't pass a ROM as
an argument (or drag one onto the `.bat` file), it opens a file picker.
Controls: arrow keys = D-pad, `X` = A, `Z` = B, `Space` = Select, `Enter` = Start.

Requires Python 3.11+ to be installed and on `PATH`
(https://python.org — check "Add python.exe to PATH" during install), but
otherwise needs no manual setup. Unlike `gbemulator.exe` below, it runs
through the already-trusted `python.exe` interpreter, so it won't get flagged
by Windows Smart App Control/SmartScreen the way an unsigned, freshly-built
`.exe` can.

## Run (prebuilt .exe, no Python required)

Download `gbemulator.exe` from the
[latest release](https://github.com/kyeong6250/gbemulator/releases), or build
it yourself (see below), then double-click it. Same file-picker/controls
behavior as above. Being an unsigned executable, Windows may flag it via
SmartScreen ("More info" → "Run anyway") or block it outright under Smart App
Control if that happens, use `gbemulator.bat` instead.

## Run from source

    pip install -r requirements.txt
    python main.py path/to/rom.gb

## Building the .exe

    pip install pyinstaller
    python -m PyInstaller --onefile --noconsole --name gbemulator main.py

The result is `dist/gbemulator.exe` (self-contained, ~30MB, no Python install
needed on the target machine). `build/`, `dist/`, and `*.spec` are gitignored
build artifacts — rebuild locally rather than expecting them in the repo.

## Test

    pytest
