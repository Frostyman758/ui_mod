"""Helpers for loading the built-in GZ -> TPP path hash mapping."""
from __future__ import annotations

from importlib import resources
import json
from typing import Dict


def load_default_mapping() -> Dict[str, int]:
    """Load the bundled JSON map that resolves resource paths to path hashes."""
    data_path = resources.files(__package__).joinpath('data/path_hashes.json')
    return json.loads(data_path.read_text())
