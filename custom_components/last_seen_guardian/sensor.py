"""
Last Seen Guardian - Sensor Platform
Creates binary_sensor and sensor entities for system status.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from .const import DOMAIN, HEALTH_STALE, HEALTH_LATE, HEALTH_OK, HEALTH_UNKNOWN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LSG sensor platform."""
    _LOGGER.debug("Setting up LSG sensor platform")
    
    evaluator = hass.data[DOMAIN].get("evaluator")
    
    if not evaluator:
        _LOGGER.error("Evaluator not available, cannot setup sensors")
        return
    
    # Create sensor entities
    entities = [
        LSGAnyProblemBinarySensor(hass, evaluator),
        LSGFailedEntitiesCountSensor(hass, evaluator),
        LSGHealthySensor(hass, evaluator),
        LSGLateSensor(hass, evaluator),
        LSGStaleSensor(hass, evaluator),
        LSGUnknownSensor(hass, evaluator),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("LSG sensor platform setup complete: %d entities", len(entities))


class LSGAnyProblemBinarySensor(BinarySensorEntity):
    """Binary sensor indicating if any entity has problems."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Any Problem"
        self._attr_unique_id = f"{DOMAIN}_any_problem"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-circle"
        self._is_on = False
        self._unsub_update = None
    
    @property
    def is_on(self) -> bool:
        """Return true if there are problems."""
        return self._is_on
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        health_states = self._evaluator.get_all_health_states()
        
        stale_count = sum(1 for h in health_states.values() if h == HEALTH_STALE)
        late_count = sum(1 for h in health_states.values() if h == HEALTH_LATE)
        
        return {
            "stale_entities": stale_count,
            "late_entities": late_count,
            "total_monitored": len(health_states),
        }
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            """Update sensor state."""
            self._update_state()
            self.async_write_ha_state()
        
        # Update every minute
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        
        # Initial update
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        # Problem if any entity is stale or late
        self._is_on = any(
            h in (HEALTH_STALE, HEALTH_LATE) 
            for h in health_states.values()
        )


class LSGFailedEntitiesCountSensor(SensorEntity):
    """Sensor showing count of failed (stale) entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Failed Entities"
        self._attr_unique_id = f"{DOMAIN}_failed_entities"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._failed_list = []
        self._unsub_update = None
    
    @property
    def native_value(self) -> int:
        """Return the count of failed entities."""
        return self._state
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return list of failed entity IDs."""
        return {
            "entity_ids": self._failed_list,
            "count": len(self._failed_list),
        }
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            """Update sensor state."""
            self._update_state()
            self.async_write_ha_state()
        
        # Update every minute
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        
        # Initial update
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        self._failed_list = [
            entity_id 
            for entity_id, health in health_states.items() 
            if health == HEALTH_STALE
        ]
        self._state = len(self._failed_list)


class LSGHealthySensor(SensorEntity):
    """Sensor showing count of healthy entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Healthy Entities"
        self._attr_unique_id = f"{DOMAIN}_healthy_entities"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._unsub_update = None
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        self._state = sum(1 for h in health_states.values() if h == HEALTH_OK)


class LSGLateSensor(SensorEntity):
    """Sensor showing count of late entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Late Entities"
        self._attr_unique_id = f"{DOMAIN}_late_entities"
        self._attr_icon = "mdi:clock-alert-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._unsub_update = None
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        self._state = sum(1 for h in health_states.values() if h == HEALTH_LATE)


class LSGStaleSensor(SensorEntity):
    """Sensor showing count of stale entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Stale Entities"
        self._attr_unique_id = f"{DOMAIN}_stale_entities"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._unsub_update = None
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        self._state = sum(1 for h in health_states.values() if h == HEALTH_STALE)


class LSGUnknownSensor(SensorEntity):
    """Sensor showing count of unknown entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator):
        """Initialize the sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._attr_name = "LSG Unknown Entities"
        self._attr_unique_id = f"{DOMAIN}_unknown_entities"
        self._attr_icon = "mdi:help-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._unsub_update = None
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=1)
        )
        _update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        self._state = sum(1 for h in health_states.values() if h == HEALTH_UNKNOWN)