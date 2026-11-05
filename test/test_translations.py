"""Every translation must use the same placeholders as en.json."""

import json
import re
from pathlib import Path

TRANSLATIONS = (
    Path(__file__).parent.parent / "custom_components/garbage_collection/translations"
)


def _flat(data: dict, prefix: str = ""):
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from _flat(value, path)
        else:
            yield path, value


def _placeholders(value: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", value))


def test_placeholders_match_english() -> None:
    """Home Assistant drops a translated string whose placeholders differ."""
    english = dict(_flat(json.loads((TRANSLATIONS / "en.json").read_text("utf-8"))))
    mismatches = [
        f"{file.name} {key}"
        for file in TRANSLATIONS.glob("*.json")
        if not file.name.startswith("sensor.")
        for key, value in _flat(json.loads(file.read_text("utf-8")))
        # An empty string falls back to English, so it is fine
        if key in english
        and value
        and _placeholders(value) != _placeholders(english[key])
    ]
    assert not mismatches
