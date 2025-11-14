"""Command line entry point for the UI format helper."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import uilb
from . import pathmap


def _detect_format_from_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == '.uilb':
        return 'uilb'
    raise ValueError(f"Unsupported file extension '{ext}'")


def _cmd_decompile(args: argparse.Namespace) -> None:
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    fmt = _detect_format_from_path(input_path)
    if fmt == 'uilb':
        uilb.decompile_to_json(input_path, output_path)
    else:
        raise ValueError(f"Unsupported format '{fmt}'")


def _cmd_compile(args: argparse.Namespace) -> None:
    input_json = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    fmt = _detect_format_from_path(output_path)
    if fmt == 'uilb':
        uilb.compile_from_json(input_json, output_path)
    else:
        raise ValueError(f"Unsupported format '{fmt}'")


def _cmd_convert(args: argparse.Namespace) -> None:
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    mapping: dict[str, int]
    if args.path_map:
        mapping = json.loads(Path(args.path_map).expanduser().read_text())
    else:
        mapping = pathmap.load_default_mapping()
    uilb.convert_gz_to_tpp(input_path, output_path, mapping)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MGSV UI format helper")
    sub = parser.add_subparsers(dest='command', required=True)

    dec = sub.add_parser('decompile', help='Convert a binary UI file into JSON')
    dec.add_argument('input', help='Path to the input .uilb file')
    dec.add_argument('output', help='Destination JSON file')
    dec.set_defaults(func=_cmd_decompile)

    comp = sub.add_parser('compile', help='Build a binary UI file from JSON')
    comp.add_argument('input', help='Source JSON description')
    comp.add_argument('output', help='Destination binary file (extension determines format)')
    comp.set_defaults(func=_cmd_compile)

    conv = sub.add_parser('convert', help='Convert a PC GZ layout into the TPP format')
    conv.add_argument('input', help='Path to the source .uilb file (must be a GZ archive)')
    conv.add_argument('output', help='Destination .uilb file that will be written in the TPP layout format')
    conv.add_argument('--path-map', help='Optional JSON file that maps resource paths to TPP path hashes')
    conv.set_defaults(func=_cmd_convert)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
