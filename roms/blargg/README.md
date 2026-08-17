# Blargg Test ROMs

This directory intentionally does not commit ROM binaries. To run
`tests/test_blargg.py`, download `cpu_instrs.gb` from Blargg's test ROM
suite (search "blargg gb-test-roms cpu_instrs", widely mirrored on
GitHub as freely redistributable test ROMs) and place it at:

    roms/blargg/cpu_instrs.gb

`tests/test_blargg.py` skips itself automatically if the file is absent.
