# gbemulator

A Game Boy (DMG) emulator written in Python, inspired by [geaz/emu-gameboy](https://github.com/geaz/emu-gameboy).

## Run (Windows, no Python required)

Build `dist/gbemulator.exe` once (see below), then just double-click it. If you
don't pass a ROM as an argument, it opens a file picker. Controls: arrow keys
= D-pad, `X` = A, `Z` = B, `Space` = Select, `Enter` = Start.

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
