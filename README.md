# gbemulator

A Game Boy (DMG) emulator written in Python. Inspired by [geaz/emu-gameboy](https://github.com/geaz/emu-gameboy), a C++ take on the same idea.

## Running it on Windows

Easiest way: double-click `gbemulator.bat`. It checks that Python's installed, grabs the dependencies the first time you run it, then launches the emulator. Skip the ROM argument (or just drag a ROM onto the file) and it'll open a picker for you. Controls are arrow keys for the D-pad, X for A, Z for B, Space for Select, Enter for Start.

You'll need Python 3.11+ on your `PATH` (grab it from python.org, tick "Add python.exe to PATH" during setup) otherwise nothing else to install. This runs through your normal Python interpreter, which Windows already trusts, so it sidesteps the SmartScreen/Smart App Control grief an unsigned .exe tends to run into.

If you'd rather skip Python entirely, there's a prebuilt `gbemulator.exe` on the [latest release](https://github.com/kyeong6250/gbemulator/releases) (or build your own, see below). It works the same way double-click, pick a ROM if you didn't pass one. The catch: being an unsigned executable, Windows might flag it. SmartScreen may ask you to click through ("More info" → "Run anyway"), or Smart App Control might block it outright. If that happens, just use `gbemulator.bat` instead.

## Running from source

    pip install -r requirements.txt
    python main.py path/to/rom.gb

## Building the .exe

    pip install pyinstaller
    python -m PyInstaller --onefile --noconsole --name gbemulator main.py

That drops a self-contained `dist/gbemulator.exe` (~30MB) that doesn't need Python on whatever machine runs it. `build/`, `dist/`, and `*.spec` are all gitignored, so just rebuild locally rather than expecting them to already be there.

## Tests

    pytest
