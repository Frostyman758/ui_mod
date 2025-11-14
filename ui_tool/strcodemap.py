"""Loaders for the bundled UIGB strcode conversion tables."""
from __future__ import annotations

from importlib import resources
import json
from typing import Dict


def load_default_mapping() -> Dict[int, int]:
    """Return the derived map that remaps GZ strcode64 hashes to TPP strcode32 values."""
    data_path = resources.files(__package__).joinpath('data/uigb_strcode_map.json')
    raw = json.loads(data_path.read_text())
    # JSON parsers keep ints intact, but iterate to ensure the keys are ints.
    return {int(key): int(value) for key, value in raw.items()}
