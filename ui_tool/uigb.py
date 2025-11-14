"""Helpers for manipulating ``.uigb`` (UI Graph Binary) containers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Sequence, Tuple

from .binary import BinaryReader, BinaryWriter


@dataclass
class UiGraphHeaderGz:
    node_count: int
    uilb_count: int
    uigb_count: int
    str_code_count: int
    section6_count: int
    path_count: int
    node_table_offset: int
    layout_table_offset: int
    section4_offset: int
    strcodes_relative_offset: int
    strings_offset: int
    buffers_offset: int


@dataclass
class UiGraphStrings:
    values: List[str]
    table_offset: int


def _parse_gz_header(reader: BinaryReader) -> Tuple[UiGraphHeaderGz, int]:
    if reader.read_bytes(4) != b"UIGB":
        raise ValueError("Not a UIGB file")
    magic = reader.read_uint8()
    if magic != 1:
        raise ValueError(f"Unsupported UIGB magic byte {magic}")
    version = reader.read_uint8()
    if version != 0:
        raise ValueError("Input file is not a PC Ground Zeroes UIGB archive")
    padding = reader.read_uint16()
    if padding != 0:
        raise ValueError("Unexpected padding in UIGB header")
    node_count = reader.read_uint16()
    uilb_count = reader.read_uint8()
    uigb_count = reader.read_uint8()
    str_code_count = reader.read_uint8()
    section6_count = reader.read_uint8()
    path_count = reader.read_uint16()
    node_table_offset = reader.read_int32()
    layout_table_offset = reader.read_int32()
    section4_offset = reader.read_int32()
    strcodes_relative_offset = reader.read_int32()
    strings_offset = reader.read_int32()
    buffers_offset = reader.read_int32()
    header = UiGraphHeaderGz(
        node_count=node_count,
        uilb_count=uilb_count,
        uigb_count=uigb_count,
        str_code_count=str_code_count,
        section6_count=section6_count,
        path_count=path_count,
        node_table_offset=node_table_offset,
        layout_table_offset=layout_table_offset,
        section4_offset=section4_offset,
        strcodes_relative_offset=strcodes_relative_offset,
        strings_offset=strings_offset,
        buffers_offset=buffers_offset,
    )
    return header, reader.tell()


def _slice_section(data: bytes, start: int, *candidates: int) -> bytes:
    if start <= 0:
        return b""
    valid = [offset for offset in candidates if offset > start]
    end = min(valid) if valid else len(data)
    if end <= start:
        return b""
    return data[start:end]


def _read_strings(data: bytes, header: UiGraphHeaderGz) -> UiGraphStrings:
    values: List[str] = []
    if header.path_count == 0 or header.strings_offset < 0:
        return UiGraphStrings(values=[], table_offset=-1)
    table_offset = header.strings_offset
    buffers_offset = header.buffers_offset
    reader = BinaryReader(data)
    for index in range(header.path_count):
        entry_offset = table_offset + index * 8
        reader.seek(entry_offset)
        size = reader.read_uint32()
        relative = reader.read_uint32()
        if size == 0:
            values.append("")
            continue
        string_start = buffers_offset + relative
        string_end = string_start + size - 1  # stored size includes the null terminator
        raw = data[string_start:string_end]
        values.append(raw.decode("utf-8"))
    return UiGraphStrings(values=values, table_offset=table_offset)


def _read_strcodes(data: bytes, header: UiGraphHeaderGz) -> List[int]:
    if header.str_code_count == 0 or header.strcodes_relative_offset < 0:
        return []
    base = header.buffers_offset + header.strcodes_relative_offset
    result: List[int] = []
    for index in range(header.str_code_count):
        offset = base + index * 8
        if offset + 8 > len(data):
            raise ValueError("StrCode table extends beyond the end of the file")
        result.append(int.from_bytes(data[offset:offset + 8], "little"))
    return result


def _split_buffer(data: bytes, header: UiGraphHeaderGz, string_lengths: Sequence[Tuple[int, int]]) -> Tuple[bytes, bytes]:
    buffer = data[header.buffers_offset:]
    buffer_length = len(buffer)
    strcode_start = header.strcodes_relative_offset if header.strcodes_relative_offset >= 0 else buffer_length
    strcode_length = header.str_code_count * 8
    strcode_end = min(buffer_length, strcode_start + strcode_length)
    last_string_end = 0
    for size, rel in string_lengths:
        end = rel + size
        if end > last_string_end:
            last_string_end = end
    last_string_end = max(last_string_end, strcode_end)
    prefix = buffer[:strcode_start]
    suffix = buffer[last_string_end:]
    return prefix, suffix


def _collect_string_metadata(data: bytes, header: UiGraphHeaderGz) -> List[Tuple[int, int]]:
    metadata: List[Tuple[int, int]] = []
    if header.path_count == 0 or header.strings_offset < 0:
        return metadata
    reader = BinaryReader(data)
    for index in range(header.path_count):
        entry_offset = header.strings_offset + index * 8
        reader.seek(entry_offset)
        size = reader.read_uint32()
        relative = reader.read_uint32()
        metadata.append((size, relative))
    return metadata


def convert_gz_to_tpp(
    input_path: Path,
    output_path: Path,
    path_map: Mapping[str, int],
    strcode_map: Mapping[int, int],
) -> None:
    """Convert a PC GZ ``.uigb`` file to the TPP layout."""
    data = input_path.read_bytes()
    reader = BinaryReader(data)
    header, _ = _parse_gz_header(reader)
    strings = _read_strings(data, header)
    if len(strings.values) != header.path_count:
        raise ValueError("Failed to read the full UIGB path table")
    string_metadata = _collect_string_metadata(data, header)
    strcodes = _read_strcodes(data, header)

    missing_paths = [value for value in strings.values if value and value not in path_map]
    if missing_paths:
        formatted = "\n - ".join(missing_paths)
        raise KeyError(
            "The path hash map does not include the following UIGB resources:"
            f"\n - {formatted}"
        )
    hashed_paths = [path_map.get(value, 0) for value in strings.values]

    missing_strcodes = [value for value in strcodes if value not in strcode_map]
    if missing_strcodes:
        formatted = "\n - ".join(hex(value) for value in missing_strcodes)
        raise KeyError(
            "The bundled strcode conversion table is missing the following entries:"
            f"\n - {formatted}"
        )
    converted_strcodes = [strcode_map[value] for value in strcodes]

    prefix, suffix = _split_buffer(data, header, string_metadata)
    buffer_writer = BinaryWriter()
    buffer_writer.write_bytes(prefix)
    buffer_writer.align(4)
    strcode_relative = -1
    if converted_strcodes:
        strcode_relative = buffer_writer.tell()
        for value in converted_strcodes:
            buffer_writer.write_uint32(value)
    buffer_writer.align(8)
    path_relative = -1
    if hashed_paths:
        path_relative = buffer_writer.tell()
        for value in hashed_paths:
            buffer_writer.write_uint64(value)
    buffer_writer.write_bytes(suffix)
    new_buffer = buffer_writer.to_bytes()

    node_chunk = _slice_section(
        data,
        header.node_table_offset,
        header.layout_table_offset,
        header.section4_offset,
        header.strings_offset,
        header.buffers_offset,
    )
    layout_chunk = _slice_section(
        data,
        header.layout_table_offset,
        header.section4_offset,
        header.strings_offset,
        header.buffers_offset,
    )
    section4_chunk = _slice_section(
        data,
        header.section4_offset,
        header.strings_offset,
        header.buffers_offset,
    )

    writer = BinaryWriter()
    header_offset = writer.reserve(56)

    def write_chunk(chunk: bytes) -> int:
        if not chunk:
            return -1
        offset = writer.tell()
        writer.write_bytes(chunk)
        return offset

    node_offset = write_chunk(node_chunk)
    layout_offset = write_chunk(layout_chunk)
    section4_offset = write_chunk(section4_chunk)
    buffers_offset = writer.tell()
    writer.write_bytes(new_buffer)

    header_writer = BinaryWriter()
    header_writer.write_bytes(b"UIGB")
    header_writer.write_uint8(1)
    header_writer.write_uint8(1)  # promote to TPP
    header_writer.write_uint16(0)
    header_writer.write_uint16(header.node_count)
    header_writer.write_uint8(header.uilb_count)
    header_writer.write_uint8(header.uigb_count)
    header_writer.write_uint8(0)
    header_writer.write_uint8(header.section6_count)
    header_writer.write_uint16(header.path_count)
    header_writer.write_uint32(len(converted_strcodes))
    header_writer.write_int32(node_offset)
    header_writer.write_int32(layout_offset)
    header_writer.write_int32(section4_offset)
    header_writer.write_int32(-1)  # unknown field
    header_writer.write_int32(-1)  # section6 offset
    header_writer.write_int32(path_relative)
    header_writer.write_uint32(strcode_relative if strcode_relative >= 0 else 0xFFFFFFFF)
    header_writer.write_int32(-1)
    header_writer.write_int32(buffers_offset)
    header_bytes = header_writer.to_bytes()
    if len(header_bytes) != 56:
        raise ValueError("Unexpected UIGB header size")
    writer.fill(header_offset, header_bytes)
    output_path.write_bytes(writer.to_bytes())
