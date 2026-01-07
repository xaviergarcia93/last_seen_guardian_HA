"""
Recorder integration for Last Seen Guardian.
Publishes events to Home Assistant event bus for long-term history.
"""
from __future__ import annotations

import logging
from typing import Dict, Any

from homeassistant.core import HomeAssistant, Event

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LSGRecorderIntegration:
    """Integration with Home Assistant Recorder."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize recorder integration."""
        self._hass = hass
    
    def fire_health_changed_event(
        self,
        entity_id: str,
        old_health: str,
        new_health: str,
        stats: Dict[str, Any]
    ) -> None:
        """
        Fire event when entity health changes.
        
        Args:
            entity_id: Entity that changed
            old_health: Previous health state
            new_health: New health state
            stats: Entity statistics
        """
        event_data = {
            "entity_id": entity_id,
            "old_health": old_health,
            "new_health": new_health,
            "interval_ewma": stats.get("interval_ewma"),
            "threshold": stats.get("threshold"),
            "event_count": stats.get("event_count"),
        }
        
        # Add technical context if available
        if "technical_context" in stats:
            context = stats["technical_context"]
            if "battery_level" in context:
                event_data["battery_level"] = context["battery_level"]
            if "lqi" in context:
                event_data["lqi"] = context["lqi"]
            if "rssi" in context:
                event_data["rssi"] = context["rssi"]
        
        self._hass.bus.async_fire(
            f"{DOMAIN}_health_changed",
            event_data
        )
        
        _LOGGER.debug(
            "Health changed event fired: %s (%s -> %s)",
            entity_id,
            old_health,
            new_health
        )
    
    def fire_entity_learned_event(
        self,
        entity_id: str,
        interval_ewma: float,
        event_count: int
    ) -> None:
        """
        Fire event when entity has enough data to be considered "learned".
        
        Args:
            entity_id: Entity that completed learning
            interval_ewma: Calculated EWMA interval
            event_count: Number of events observed
        """
        self._hass.bus.async_fire(
            f"{DOMAIN}_entity_learned",
            {
                "entity_id": entity_id,
                "interval_ewma": interval_ewma,
                "event_count": event_count,
            }
        )
        
        _LOGGER.info(
            "Entity learned event fired: %s (EWMA: %.2fs, events: %d)",
            entity_id,
            interval_ewma,
            event_count
        )