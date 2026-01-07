"""Logbook integration for Last Seen Guardian."""
from __future__ import annotations

from typing import Callable

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    """Describe logbook events for Last Seen Guardian."""

    @callback
    def describe_health_changed_event(event: Event) -> dict[str, str]:
        """Describe health changed event."""
        entity_id = event.data.get("entity_id")
        old_health = event.data.get("old_health", "unknown")
        new_health = event.data.get("new_health", "unknown")
        
        if new_health == "stale":
            icon = "mdi:alert-circle"
            message = f"{entity_id} became unresponsive (from {old_health})"
        elif new_health == "late":
            icon = "mdi:clock-alert"
            message = f"{entity_id} is reporting late (from {old_health})"
        elif new_health == "ok":
            icon = "mdi:check-circle"
            message = f"{entity_id} recovered to normal (from {old_health})"
        else:
            icon = "mdi:help-circle"
            message = f"{entity_id} health changed: {old_health} → {new_health}"
        
        return {
            LOGBOOK_ENTRY_NAME: "Last Seen Guardian",
            LOGBOOK_ENTRY_MESSAGE: message,
            "icon": icon,
        }

    @callback
    def describe_entity_learned_event(event: Event) -> dict[str, str]:
        """Describe entity learned event."""
        entity_id = event.data.get("entity_id")
        event_count = event.data.get("event_count", 0)
        
        return {
            LOGBOOK_ENTRY_NAME: "Last Seen Guardian",
            LOGBOOK_ENTRY_MESSAGE: f"{entity_id} pattern learned after {event_count} events",
            "icon": "mdi:brain",
        }

    async_describe_event(
        DOMAIN,
        f"{DOMAIN}_health_changed",
        describe_health_changed_event,
    )
    
    async_describe_event(
        DOMAIN,
        f"{DOMAIN}_entity_learned",
        describe_entity_learned_event,
    )