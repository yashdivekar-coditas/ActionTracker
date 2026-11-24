"""People directory: full name -> email, read from a JSON file."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class PeopleError(Exception):
    pass


def load_people(path: Path) -> Dict[str, str]:
    """A missing file is an empty directory; a malformed one is an error the user must fix."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PeopleError(f"cannot read people directory {path}: {exc}") from exc
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise PeopleError(f"people directory {path} must map full names to email addresses")
    return data
