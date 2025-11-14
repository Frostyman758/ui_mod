"""Common math/struct helpers that mirror the bt template typedefs."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

from .binary import BinaryReader, BinaryWriter


@dataclass
class Vector3:
    x: float
    y: float
    z: float

    @classmethod
    def read(cls, reader: BinaryReader) -> "Vector3":
        return cls(reader.read_float32(), reader.read_float32(), reader.read_float32())

    def write(self, writer: BinaryWriter) -> None:
        writer.write_float32(self.x)
        writer.write_float32(self.y)
        writer.write_float32(self.z)

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vector3":
        return cls(**data)


@dataclass
class Vector4:
    x: float
    y: float
    z: float
    w: float

    @classmethod
    def read(cls, reader: BinaryReader) -> "Vector4":
        return cls(
            reader.read_float32(),
            reader.read_float32(),
            reader.read_float32(),
            reader.read_float32(),
        )

    def write(self, writer: BinaryWriter) -> None:
        writer.write_float32(self.x)
        writer.write_float32(self.y)
        writer.write_float32(self.z)
        writer.write_float32(self.w)

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vector4":
        return cls(**data)


# ``Vector3W`` in the templates is simply a four-component vector.
Vector3W = Vector4


@dataclass
class Quaternion(Vector4):
    """Quaternions share the same memory layout as Vector4."""


def vector_from_dict(cls, data: Dict[str, Any]):
    return cls(**data)
