"""Parser/builder for ``.uilb`` (UI Layout Binary) containers."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Sequence
import json
import struct

from .binary import BinaryReader, BinaryWriter, BufferBuilder, align
from .types import Quaternion, Vector4, Vector3W


class UiLayoutVersion(Enum):
    GZ = 0
    TPP = 1

    @classmethod
    def from_raw(cls, value: int) -> "UiLayoutVersion":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unsupported UILB version: {value}") from exc


@dataclass
class UiModelData:
    name_index: int
    model_file_path_index: int
    flags: int
    priority: int
    scale: Vector3W
    rotation: Quaternion
    translate: Vector4
    color: Vector4
    billboard_min: float
    billboard_max: float
    connect_model_data_index: int
    connect_model_node_index: int
    inheritance_setting: int
    anim_data_name_indices: List[int]
    use_layout_camera: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UiModelData":
        return cls(
            name_index=data["name_index"],
            model_file_path_index=data["model_file_path_index"],
            flags=data["flags"],
            priority=data["priority"],
            scale=Vector3W.from_dict(data["scale"]),
            rotation=Quaternion.from_dict(data["rotation"]),
            translate=Vector4.from_dict(data["translate"]),
            color=Vector4.from_dict(data["color"]),
            billboard_min=data["billboard_min"],
            billboard_max=data["billboard_max"],
            connect_model_data_index=data["connect_model_data_index"],
            connect_model_node_index=data["connect_model_node_index"],
            inheritance_setting=data["inheritance_setting"],
            anim_data_name_indices=list(data.get("anim_data_name_indices", [])),
            use_layout_camera=data["use_layout_camera"],
        )


@dataclass
class UiAnimData:
    name_index: int
    anim_file_ui_index: int
    anim_file_shader_index: int
    src_node_indices: List[int]
    dest_node_indices: List[int]
    speed: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UiAnimData":
        return cls(
            name_index=data["name_index"],
            anim_file_ui_index=data["anim_file_ui_index"],
            anim_file_shader_index=data["anim_file_shader_index"],
            src_node_indices=list(data.get("src_node_indices", [])),
            dest_node_indices=list(data.get("dest_node_indices", [])),
            speed=data["speed"],
        )


@dataclass
class UiCameraData:
    name_index: int
    use_ortho: int
    fov_type: int
    ortho_height: float
    near_clip: float
    far_clip: float
    fov: float
    translate: Vector4
    rotation: Quaternion

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UiCameraData":
        return cls(
            name_index=data["name_index"],
            use_ortho=data["use_ortho"],
            fov_type=data["fov_type"],
            ortho_height=data["ortho_height"],
            near_clip=data["near_clip"],
            far_clip=data["far_clip"],
            fov=data["fov"],
            translate=Vector4.from_dict(data["translate"]),
            rotation=Quaternion.from_dict(data["rotation"]),
        )


@dataclass
class UiLayoutData:
    name_index: int
    layout_file_path_index: int
    priority: int
    scale: Vector3W
    rotation: Quaternion
    translate: Vector4
    color: Vector4
    connect_model_data_index: int
    connect_model_node_index: int
    visible: int
    use_parent_camera: int
    font_table_index: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UiLayoutData":
        return cls(
            name_index=data["name_index"],
            layout_file_path_index=data["layout_file_path_index"],
            priority=data["priority"],
            scale=Vector3W.from_dict(data["scale"]),
            rotation=Quaternion.from_dict(data["rotation"]),
            translate=Vector4.from_dict(data["translate"]),
            color=Vector4.from_dict(data["color"]),
            connect_model_data_index=data["connect_model_data_index"],
            connect_model_node_index=data["connect_model_node_index"],
            visible=data["visible"],
            use_parent_camera=data["use_parent_camera"],
            font_table_index=data["font_table_index"],
        )


@dataclass
class StrCodeEntry:
    hash: int
    value: int

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "StrCodeEntry":
        return cls(hash=data["hash"], value=data["value"])


@dataclass
class PathStringEntry:
    value: str

    def to_dict(self) -> Dict[str, str]:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "PathStringEntry":
        return cls(value=data["value"])


@dataclass
class UiLayoutBinary:
    version: UiLayoutVersion
    models: List[UiModelData]
    animations: List[UiAnimData]
    cameras: List[UiCameraData]
    layouts: List[UiLayoutData]
    str_codes: List[Any]
    path_entries: List[Any]

    @classmethod
    def from_bytes(cls, data: bytes) -> "UiLayoutBinary":
        reader = BinaryReader(data)
        if reader.read_bytes(4) != b"UILB":
            raise ValueError("Not a UILB file")
        magic = reader.read_uint8()
        if magic != 1:
            raise ValueError(f"Unexpected magic value: {magic}")
        version = UiLayoutVersion.from_raw(reader.read_uint8())
        padding = reader.read_uint16()
        if padding != 0:
            raise ValueError("UILB padding must be zero")

        model_count = reader.read_uint16()
        anim_count = reader.read_uint16()
        camera_count = reader.read_uint16()
        layout_count = reader.read_uint16()
        strcode_count = reader.read_uint16()
        pathcode_count = reader.read_uint16()

        model_offset = reader.read_int32()
        anim_offset = reader.read_int32()
        camera_offset = reader.read_int32()
        layout_offset = reader.read_int32()
        strcode_relative = reader.read_int32()
        path_relative = reader.read_int32()
        buffers_offset = reader.read_int32()

        blob = memoryview(data)

        def read_model_section() -> List[UiModelData]:
            if model_offset == -1 or model_count == 0:
                return []
            reader.seek(model_offset)
            result = []
            for _ in range(model_count):
                name_index = reader.read_int16()
                model_file_index = reader.read_int16()
                flags = reader.read_uint32()
                priority = reader.read_int32()
                scale = Vector3W.read(reader)
                rotation = Quaternion.read(reader)
                translate = Vector4.read(reader)
                color = Vector4.read(reader)
                billboard_min = reader.read_float32()
                billboard_max = reader.read_float32()
                connect_model_data_index = reader.read_int16()
                connect_model_node_index = reader.read_int16()
                inheritance_setting = reader.read_uint32()
                anim_rel = reader.read_int32()
                anim_count = reader.read_int16()
                use_layout_camera = reader.read_uint8()
                padding_flag = reader.read_uint8()
                if padding_flag != 0:
                    raise ValueError("Unexpected non-zero model padding flag")
                anim_indices: List[int] = []
                if anim_count > 0 and anim_rel != -1:
                    start = buffers_offset + anim_rel
                    fmt = '<' + 'h' * anim_count
                    anim_indices = list(struct.unpack_from(fmt, blob, start))
                result.append(
                    UiModelData(
                        name_index=name_index,
                        model_file_path_index=model_file_index,
                        flags=flags,
                        priority=priority,
                        scale=scale,
                        rotation=rotation,
                        translate=translate,
                        color=color,
                        billboard_min=billboard_min,
                        billboard_max=billboard_max,
                        connect_model_data_index=connect_model_data_index,
                        connect_model_node_index=connect_model_node_index,
                        inheritance_setting=inheritance_setting,
                        anim_data_name_indices=anim_indices,
                        use_layout_camera=use_layout_camera,
                    )
                )
            return result

        def read_anim_section() -> List[UiAnimData]:
            if anim_offset == -1 or anim_count == 0:
                return []
            reader.seek(anim_offset)
            entries: List[UiAnimData] = []
            for _ in range(anim_count):
                name_index = reader.read_int16()
                anim_file_ui = reader.read_int16()
                anim_file_shader = reader.read_int16()
                node_count = reader.read_uint16()
                src_rel = reader.read_int32()
                dest_rel = reader.read_int32()
                src_nodes: List[int] = []
                dest_nodes: List[int] = []
                if node_count > 0:
                    if src_rel != -1:
                        fmt = '<' + 'h' * node_count
                        src_nodes = list(struct.unpack_from(fmt, blob, buffers_offset + src_rel))
                    if dest_rel != -1:
                        fmt = '<' + 'h' * node_count
                        dest_nodes = list(struct.unpack_from(fmt, blob, buffers_offset + dest_rel))
                speed = reader.read_float32()
                entries.append(
                    UiAnimData(
                        name_index=name_index,
                        anim_file_ui_index=anim_file_ui,
                        anim_file_shader_index=anim_file_shader,
                        src_node_indices=src_nodes,
                        dest_node_indices=dest_nodes,
                        speed=speed,
                    )
                )
            return entries

        def read_camera_section() -> List[UiCameraData]:
            if camera_offset == -1 or camera_count == 0:
                return []
            reader.seek(camera_offset)
            cameras: List[UiCameraData] = []
            for _ in range(camera_count):
                name_index = reader.read_int16()
                use_ortho = reader.read_uint8()
                fov_type = reader.read_uint8()
                ortho_height = reader.read_float32()
                near_clip = reader.read_float32()
                far_clip = reader.read_float32()
                fov = reader.read_float32()
                translate = Vector4.read(reader)
                rotation = Quaternion.read(reader)
                cameras.append(
                    UiCameraData(
                        name_index=name_index,
                        use_ortho=use_ortho,
                        fov_type=fov_type,
                        ortho_height=ortho_height,
                        near_clip=near_clip,
                        far_clip=far_clip,
                        fov=fov,
                        translate=translate,
                        rotation=rotation,
                    )
                )
            return cameras

        def read_layout_section() -> List[UiLayoutData]:
            if layout_offset == -1 or layout_count == 0:
                return []
            reader.seek(layout_offset)
            layouts: List[UiLayoutData] = []
            for _ in range(layout_count):
                name_index = reader.read_int16()
                layout_file_index = reader.read_int16()
                priority = reader.read_int32()
                scale = Vector3W.read(reader)
                rotation = Quaternion.read(reader)
                translate = Vector4.read(reader)
                color = Vector4.read(reader)
                connect_model_data_index = reader.read_int16()
                connect_model_node_index = reader.read_int16()
                visible = reader.read_uint8()
                use_parent_camera = reader.read_uint8()
                font_table_index = reader.read_int16()
                layouts.append(
                    UiLayoutData(
                        name_index=name_index,
                        layout_file_path_index=layout_file_index,
                        priority=priority,
                        scale=scale,
                        rotation=rotation,
                        translate=translate,
                        color=color,
                        connect_model_data_index=connect_model_data_index,
                        connect_model_node_index=connect_model_node_index,
                        visible=visible,
                        use_parent_camera=use_parent_camera,
                        font_table_index=font_table_index,
                    )
                )
            return layouts

        models = read_model_section()
        animations = read_anim_section()
        cameras = read_camera_section()
        layouts = read_layout_section()

        str_codes: List[Any] = []
        if strcode_count and strcode_relative != -1:
            reader.seek(buffers_offset + strcode_relative)
            if version is UiLayoutVersion.GZ:
                for _ in range(strcode_count):
                    hash_value = reader.read_uint32()
                    value = reader.read_uint32()
                    str_codes.append(StrCodeEntry(hash=hash_value, value=value))
            else:
                for _ in range(strcode_count):
                    str_codes.append(reader.read_uint32())

        path_entries: List[Any] = []
        if version is UiLayoutVersion.GZ:
            if pathcode_count and path_relative != -1:
                reader.seek(path_relative)
                for _ in range(pathcode_count):
                    size = reader.read_uint32()
                    rel = reader.read_uint32()
                    text = ""
                    if rel != 0xFFFFFFFF:
                        start = buffers_offset + rel
                        text = blob[start:start + size].tobytes().decode('utf-8')
                    path_entries.append(PathStringEntry(text))
        else:
            if pathcode_count and path_relative != -1:
                reader.seek(buffers_offset + path_relative)
                for _ in range(pathcode_count):
                    path_entries.append(reader.read_uint64())

        return cls(
            version=version,
            models=models,
            animations=animations,
            cameras=cameras,
            layouts=layouts,
            str_codes=str_codes,
            path_entries=path_entries,
        )

    def to_dict(self) -> Dict[str, Any]:
        def serialize_list(items: Sequence[Any]) -> List[Any]:
            result: List[Any] = []
            for item in items:
                if hasattr(item, "to_dict"):
                    result.append(item.to_dict())
                else:
                    result.append(item)
            return result

        return {
            "version": self.version.name,
            "models": serialize_list(self.models),
            "animations": serialize_list(self.animations),
            "cameras": serialize_list(self.cameras),
            "layouts": serialize_list(self.layouts),
            "str_codes": serialize_list(self.str_codes),
            "path_entries": serialize_list(self.path_entries),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UiLayoutBinary":
        version = UiLayoutVersion[data["version"].upper()]
        def parse_list(items, factory):
            return [factory(item) for item in items]

        models = parse_list(data.get("models", []), UiModelData.from_dict)
        animations = parse_list(data.get("animations", []), UiAnimData.from_dict)
        cameras = parse_list(data.get("cameras", []), UiCameraData.from_dict)
        layouts = parse_list(data.get("layouts", []), UiLayoutData.from_dict)

        if version is UiLayoutVersion.GZ:
            str_codes = parse_list(data.get("str_codes", []), StrCodeEntry.from_dict)
            path_entries = parse_list(data.get("path_entries", []), PathStringEntry.from_dict)
        else:
            str_codes = list(data.get("str_codes", []))
            path_entries = list(data.get("path_entries", []))

        return cls(
            version=version,
            models=models,
            animations=animations,
            cameras=cameras,
            layouts=layouts,
            str_codes=str_codes,
            path_entries=path_entries,
        )

    def to_bytes(self) -> bytes:
        writer = BinaryWriter()
        writer.write_bytes(b"UILB")
        writer.write_uint8(1)
        writer.write_uint8(self.version.value)
        writer.write_uint16(0)

        header_offset = writer.reserve(4 * 4 + 2 * 2 + 7 * 4)

        buffer_builder = BufferBuilder()

        def pack_int16_array(values: List[int]) -> int:
            alloc = buffer_builder.add_int16_array(values)
            return alloc.offset if alloc else -1

        model_offset = -1
        if self.models:
            model_offset = writer.tell()
            for model in self.models:
                writer.write_int16(model.name_index)
                writer.write_int16(model.model_file_path_index)
                writer.write_uint32(model.flags)
                writer.write_int32(model.priority)
                model.scale.write(writer)
                model.rotation.write(writer)
                model.translate.write(writer)
                model.color.write(writer)
                writer.write_float32(model.billboard_min)
                writer.write_float32(model.billboard_max)
                writer.write_int16(model.connect_model_data_index)
                writer.write_int16(model.connect_model_node_index)
                writer.write_uint32(model.inheritance_setting)
                anim_rel = pack_int16_array(model.anim_data_name_indices)
                writer.write_int32(anim_rel)
                writer.write_int16(len(model.anim_data_name_indices))
                writer.write_uint8(model.use_layout_camera)
                writer.write_uint8(0)

        anim_offset = -1
        if self.animations:
            anim_offset = writer.tell()
            for anim in self.animations:
                writer.write_int16(anim.name_index)
                writer.write_int16(anim.anim_file_ui_index)
                writer.write_int16(anim.anim_file_shader_index)
                writer.write_uint16(len(anim.src_node_indices))
                src_rel = pack_int16_array(anim.src_node_indices)
                dest_rel = pack_int16_array(anim.dest_node_indices)
                writer.write_int32(src_rel)
                writer.write_int32(dest_rel)
                writer.write_float32(anim.speed)

        camera_offset = -1
        if self.cameras:
            camera_offset = writer.tell()
            for cam in self.cameras:
                writer.write_int16(cam.name_index)
                writer.write_uint8(cam.use_ortho)
                writer.write_uint8(cam.fov_type)
                writer.write_float32(cam.ortho_height)
                writer.write_float32(cam.near_clip)
                writer.write_float32(cam.far_clip)
                writer.write_float32(cam.fov)
                cam.translate.write(writer)
                cam.rotation.write(writer)

        layout_offset = -1
        if self.layouts:
            layout_offset = writer.tell()
            for layout in self.layouts:
                writer.write_int16(layout.name_index)
                writer.write_int16(layout.layout_file_path_index)
                writer.write_int32(layout.priority)
                layout.scale.write(writer)
                layout.rotation.write(writer)
                layout.translate.write(writer)
                layout.color.write(writer)
                writer.write_int16(layout.connect_model_data_index)
                writer.write_int16(layout.connect_model_node_index)
                writer.write_uint8(layout.visible)
                writer.write_uint8(layout.use_parent_camera)
                writer.write_int16(layout.font_table_index)

        path_relative = -1
        path_table_offset = -1
        if self.version is UiLayoutVersion.GZ:
            if self.path_entries:
                path_table_offset = writer.tell()
                temp_entries: List[tuple[int, int]] = []
                for entry in self.path_entries:
                    text = entry.value if isinstance(entry, PathStringEntry) else entry["value"]
                    encoded = text.encode('utf-8')
                    alloc = buffer_builder.add(encoded, align_to=16)
                    temp_entries.append((len(encoded), alloc.offset))
                for size, rel in temp_entries:
                    writer.write_uint32(size)
                    writer.write_uint32(rel)
        else:
            if self.path_entries:
                alloc = buffer_builder.add_uint64_array(self.path_entries)
                path_relative = alloc.offset if alloc else -1

        strcode_relative = -1
        if self.str_codes:
            if self.version is UiLayoutVersion.GZ:
                data = b"".join(struct.pack('<II', entry.hash, entry.value) for entry in self.str_codes)
            else:
                data = struct.pack('<' + 'I' * len(self.str_codes), *self.str_codes)
            alloc = buffer_builder.add(data, align_to=4)
            strcode_relative = alloc.offset

        writer.align(4)
        buffers_offset = writer.tell()
        buffer_data = buffer_builder.build()
        writer.write_bytes(buffer_data)

        model_count = len(self.models)
        anim_count = len(self.animations)
        camera_count = len(self.cameras)
        layout_count = len(self.layouts)
        strcode_count = len(self.str_codes)
        pathcode_count = len(self.path_entries)

        header_values = struct.pack(
            '<4H2H7i',
            model_count,
            anim_count,
            camera_count,
            layout_count,
            strcode_count,
            pathcode_count,
            model_offset,
            anim_offset,
            camera_offset,
            layout_offset,
            strcode_relative,
            path_table_offset if self.version is UiLayoutVersion.GZ else path_relative,
            buffers_offset if buffer_builder.size() > 0 else -1,
        )
        writer.fill(header_offset, header_values)
        return writer.to_bytes()


def decompile_to_json(input_path: Path, output_path: Path) -> None:
    """Read a ``.uilb`` file and dump its JSON description."""
    layout = UiLayoutBinary.from_bytes(input_path.read_bytes())
    output_path.write_text(json.dumps(layout.to_dict(), indent=2, sort_keys=True))


def compile_from_json(input_json: Path, output_path: Path) -> None:
    data = json.loads(input_json.read_text())
    layout = UiLayoutBinary.from_dict(data)
    output_path.write_bytes(layout.to_bytes())
