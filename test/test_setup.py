"""Setup, reload and shared calendar ownership (HA 2026.11 setup lock)."""

import asyncio

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.garbage_collection import const


def _entry(title: str, hidden: bool = False) -> MockConfigEntry:
    return MockConfigEntry(
        domain=const.DOMAIN,
        options={"frequency": "weekly", "collection_days": ["mon"], "hidden": hidden},
        title=title,
        version=6,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    # A deadlocked forward never returns, so fail fast instead of hanging.
    async with asyncio.timeout(10):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state == config_entries.ConfigEntryState.LOADED


def _calendars(hass: HomeAssistant) -> list[str]:
    return hass.states.async_entity_ids("calendar")


async def test_two_entries_share_one_calendar(hass: HomeAssistant) -> None:
    """Second entry joins the calendar of the first one."""
    first, second = _entry("first"), _entry("second")
    await _setup(hass, first)
    await _setup(hass, second)
    assert _calendars(hass) == ["calendar.garbage_collection"]
    cal = hass.data[const.DOMAIN][const.CALENDAR_PLATFORM]
    assert sorted(cal.entities) == ["sensor.first", "sensor.second"]


async def test_reload_keeps_calendar(hass: HomeAssistant) -> None:
    """Options update reloads the entry without deadlock or lost calendar."""
    first, second = _entry("first"), _entry("second")
    await _setup(hass, first)
    await _setup(hass, second)
    async with asyncio.timeout(10):
        hass.config_entries.async_update_entry(
            first, options={**first.options, "collection_days": ["tue"]}
        )
        await hass.async_block_till_done()
    assert first.state == config_entries.ConfigEntryState.LOADED
    assert _calendars(hass) == ["calendar.garbage_collection"]
    cal = hass.data[const.DOMAIN][const.CALENDAR_PLATFORM]
    assert sorted(cal.entities) == ["sensor.first", "sensor.second"]


async def test_hidden_entry_does_not_own_calendar(hass: HomeAssistant) -> None:
    """A hidden first entry leaves the calendar to the next visible one."""
    await _setup(hass, _entry("hidden", hidden=True))
    assert _calendars(hass) == []
    await _setup(hass, _entry("visible"))
    assert _calendars(hass) == ["calendar.garbage_collection"]
    cal = hass.data[const.DOMAIN][const.CALENDAR_PLATFORM]
    assert cal.entities == ["sensor.visible"]
