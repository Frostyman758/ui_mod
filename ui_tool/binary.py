"""Binary helpers for reading and writing Fox UI container formats."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List
import struct


def align(value: int, boundary: int) -> int:
    """Align ``value`` to the next ``boundary`` bytes boundary."""
    if boundary <= 1:
        return value
    mask = boundary - 1
    return (value + mask) & ~mask


class BinaryReader:
    """Convenience wrapper around ``memoryview`` for little-endian parsing."""

    def __init__(self, data: bytes):
        self._view = memoryview(data)
        self._offset = 0

    def tell(self) -> int:
        return self._offset

    def seek(self, offset: int) -> None:
        if not 0 <= offset <= len(self._view):
            raise ValueError(f"Offset {offset} outside buffer")
        self._offset = offset

    def skip(self, size: int) -> None:
        self.seek(self._offset + size)

    def align(self, boundary: int) -> None:
        self._offset = align(self._offset, boundary)

    def _read_struct(self, fmt: str):
        size = struct.calcsize(fmt)
        if self._offset + size > len(self._view):
            raise ValueError("Unexpected end of buffer")
        result = struct.unpack_from(fmt, self._view, self._offset)
        self._offset += size
        return result

    def read_bytes(self, size: int) -> bytes:
        start = self._offset
        self.skip(size)
        return self._view[start:self._offset].tobytes()

    def read_uint8(self) -> int:
        return self._read_struct('<B')[0]

    def read_int8(self) -> int:
        return self._read_struct('<b')[0]

    def read_uint16(self) -> int:
        return self._read_struct('<H')[0]

    def read_int16(self) -> int:
        return self._read_struct('<h')[0]

    def read_uint32(self) -> int:
        return self._read_struct('<I')[0]

    def read_int32(self) -> int:
        return self._read_struct('<i')[0]

    def read_uint64(self) -> int:
        return self._read_struct('<Q')[0]

    def read_float32(self) -> float:
        return self._read_struct('<f')[0]

    def read_struct(self, fmt: str):
        return self._read_struct(fmt)

    def slice(self, offset: int, size: int) -> bytes:
        end = offset + size
        if offset < 0 or end > len(self._view):
            raise ValueError("Requested slice outside buffer")
        return self._view[offset:end].tobytes()


class BinaryWriter:
    """Utility that mirrors ``BinaryReader`` for writing."""

    def __init__(self):
        self._buffer = bytearray()

    def tell(self) -> int:
        return len(self._buffer)

    def write_bytes(self, data: bytes) -> None:
        self._buffer.extend(data)

    def write_uint8(self, value: int) -> None:
        self._buffer += struct.pack('<B', value)

    def write_uint16(self, value: int) -> None:
        self._buffer += struct.pack('<H', value)

    def write_int16(self, value: int) -> None:
        self._buffer += struct.pack('<h', value)

    def write_uint32(self, value: int) -> None:
        self._buffer += struct.pack('<I', value)

    def write_int32(self, value: int) -> None:
        self._buffer += struct.pack('<i', value)

    def write_uint64(self, value: int) -> None:
        self._buffer += struct.pack('<Q', value)

    def write_float32(self, value: float) -> None:
        self._buffer += struct.pack('<f', value)

    def write_struct(self, fmt: str, *values) -> None:
        self._buffer += struct.pack(fmt, *values)

    def reserve(self, size: int) -> int:
        offset = len(self._buffer)
        self._buffer.extend(b"\x00" * size)
        return offset

    def fill(self, offset: int, data: bytes) -> None:
        end = offset + len(data)
        if end > len(self._buffer):
            raise ValueError("Fill exceeds buffer size")
        self._buffer[offset:end] = data

    def align(self, boundary: int, padding: bytes = b"\x00") -> None:
        target = align(len(self._buffer), boundary)
        if target > len(self._buffer):
            pad_len = target - len(self._buffer)
            self._buffer.extend(padding * pad_len)

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)


@dataclass
class BufferAllocation:
    offset: int
    size: int


class BufferBuilder:
    """Collects buffer payloads referenced by relative offsets."""

    def __init__(self, alignment: int = 4):
        self._alignment = alignment
        self._cursor = 0
        self._chunks: List[tuple[int, bytes]] = []

    def add(self, data: bytes, align_to: int | None = None) -> BufferAllocation:
        align_to = align_to or self._alignment
        start = align(self._cursor, align_to)
        if start > self._cursor:
            self._chunks.append((self._cursor, b"\x00" * (start - self._cursor)))
        self._chunks.append((start, data))
        self._cursor = start + len(data)
        return BufferAllocation(offset=start, size=len(data))

    def add_uint16_array(self, values: Iterable[int]) -> BufferAllocation | None:
        values = list(values)
        if not values:
            return None
        data = struct.pack('<' + 'H' * len(values), *values)
        return self.add(data, align_to=2)

    def add_int16_array(self, values: Iterable[int]) -> BufferAllocation | None:
        values = list(values)
        if not values:
            return None
        data = struct.pack('<' + 'h' * len(values), *values)
        return self.add(data, align_to=2)

    def add_int16_list(self, values: Iterable[int]) -> BufferAllocation | None:
        # Alias that ensures signed semantics when needed.
        return self.add_int16_array(values)

    def add_uint32_array(self, values: Iterable[int], align_to: int = 4) -> BufferAllocation | None:
        values = list(values)
        if not values:
            return None
        data = struct.pack('<' + 'I' * len(values), *values)
        return self.add(data, align_to=align_to)

    def add_uint64_array(self, values: Iterable[int]) -> BufferAllocation | None:
        values = list(values)
        if not values:
            return None
        data = struct.pack('<' + 'Q' * len(values), *values)
        return self.add(data, align_to=8)

    def add_block(self, size: int, fill_byte: int = 0, align_to: int | None = None) -> BufferAllocation:
        data = bytes([fill_byte]) * size
        return self.add(data, align_to)

    def size(self) -> int:
        return self._cursor

    def build(self) -> bytes:
        if not self._chunks:
            return b''
        result = bytearray(self._cursor)
        for offset, data in self._chunks:
            result[offset:offset + len(data)] = data
        return bytes(result)
