from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Return the source root or the PyInstaller temporary bundle root."""
    bundle_root = getattr(sys, "_MEIPASS", None)

    if bundle_root:
        return Path(bundle_root)

    return Path(__file__).resolve().parents[1]


def resource_path(relative_path: str) -> Path:
    """Return an absolute path for a bundled resource."""
    return project_root() / relative_path
