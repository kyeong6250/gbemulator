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
