"""
Last Seen Guardian - Sensor Platform
Creates binary_sensor and sensor entities for system status.
"""
from __future__ import annotations

import logging
import time
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
from homeassistant.helpers.device_registry import DeviceInfo
from datetime import timedelta

from .const import (
    DOMAIN,
    HEALTH_STALE,
    HEALTH_LATE,
    HEALTH_OK,
    HEALTH_UNKNOWN,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_SW_VERSION,
    MIN_EVENTS_FOR_NOTIFICATION,
)

_LOGGER = logging.getLogger(__name__)

# CRITICAL: Wait 15 minutes after startup before updating sensors
SENSOR_STARTUP_DELAY = 900  # 15 minutes


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
        LSGAnyProblemBinarySensor(hass, evaluator, entry),
        LSGFailedEntitiesCountSensor(hass, evaluator, entry),
        LSGHealthySensor(hass, evaluator, entry),
        LSGLateSensor(hass, evaluator, entry),
        LSGStaleSensor(hass, evaluator, entry),
        LSGUnknownSensor(hass, evaluator, entry),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("LSG sensor platform setup complete: %d entities (startup delay: %ds)", 
                len(entities), SENSOR_STARTUP_DELAY)


class LSGBaseSensor:
    """Base class for LSG sensors with device info and startup protection."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize base sensor."""
        self._hass = hass
        self._evaluator = evaluator
        self._entry = entry
        self._unsub_update = None
        self._startup_time = time.time()
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info to group sensors together."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Last Seen Guardian",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            sw_version=DEVICE_SW_VERSION,
        )
    
    def _is_ready(self) -> bool:
        """Check if sensor is ready to update (after startup delay)."""
        elapsed = time.time() - self._startup_time
        return elapsed >= SENSOR_STARTUP_DELAY
    
    async def async_will_remove_from_hass(self) -> None:
        """Cleanup on removal."""
        if self._unsub_update:
            self._unsub_update()


class LSGAnyProblemBinarySensor(LSGBaseSensor, BinarySensorEntity):
    """Binary sensor indicating if any entity has problems."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Any Problem"
        self._attr_unique_id = f"{DOMAIN}_any_problem"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-circle"
        self._is_on = False
    
    @property
    def is_on(self) -> bool:
        """Return true if there are problems."""
        return self._is_on
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        if not self._is_ready():
            return {
                "status": "learning",
                "message": "Waiting for initial learning phase",
                "stale_entities": 0,
                "late_entities": 0,
                "total_monitored": 0,
            }
        
        health_states = self._evaluator.get_all_health_states()
        
        # Only count entities with sufficient learning
        valid_entities = {
            eid: h for eid, h in health_states.items()
            if self._evaluator.get_entity_stats(eid) and
            self._evaluator.get_entity_stats(eid).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        }
        
        stale_count = sum(1 for h in valid_entities.values() if h == HEALTH_STALE)
        late_count = sum(1 for h in valid_entities.values() if h == HEALTH_LATE)
        
        return {
            "status": "active",
            "stale_entities": stale_count,
            "late_entities": late_count,
            "total_monitored": len(valid_entities),
            "learning_entities": len(health_states) - len(valid_entities),
        }
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            """Update sensor state."""
            if not self._is_ready():
                self._is_on = False
                _LOGGER.debug("Sensor in startup delay, state=OFF")
            else:
                self._update_state()
            
            self.async_write_ha_state()
        
        # Update every 5 minutes (not 1)
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        
        # Immediate update
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        # Only count entities with sufficient learning
        valid_entities = [
            h for eid, h in health_states.items()
            if self._evaluator.get_entity_stats(eid) and
            self._evaluator.get_entity_stats(eid).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        ]
        
        self._is_on = any(
            h in (HEALTH_STALE, HEALTH_LATE) 
            for h in valid_entities
        )


class LSGFailedEntitiesCountSensor(LSGBaseSensor, SensorEntity):
    """Sensor showing count of failed (stale) entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Failed Entities"
        self._attr_unique_id = f"{DOMAIN}_failed_entities"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
        self._failed_list = []
    
    @property
    def native_value(self) -> int:
        """Return the count of failed entities."""
        return self._state
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return list of failed entity IDs."""
        if not self._is_ready():
            return {
                "entity_ids": [],
                "count": 0,
                "status": "learning",
            }
        
        return {
            "entity_ids": self._failed_list,
            "count": len(self._failed_list),
            "status": "active",
        }
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            """Update sensor state."""
            if not self._is_ready():
                self._state = 0
                self._failed_list = []
            else:
                self._update_state()
            
            self.async_write_ha_state()
        
        # Update every 5 minutes
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        # Only count entities with sufficient learning
        self._failed_list = [
            entity_id 
            for entity_id, health in health_states.items() 
            if health == HEALTH_STALE and
            self._evaluator.get_entity_stats(entity_id) and
            self._evaluator.get_entity_stats(entity_id).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        ]
        self._state = len(self._failed_list)


class LSGHealthySensor(LSGBaseSensor, SensorEntity):
    """Sensor showing count of healthy entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Healthy Entities"
        self._attr_unique_id = f"{DOMAIN}_healthy_entities"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            if not self._is_ready():
                self._state = 0
            else:
                self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        # Only count entities with sufficient learning
        self._state = sum(
            1 for eid, h in health_states.items()
            if h == HEALTH_OK and
            self._evaluator.get_entity_stats(eid) and
            self._evaluator.get_entity_stats(eid).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        )


class LSGLateSensor(LSGBaseSensor, SensorEntity):
    """Sensor showing count of late entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Late Entities"
        self._attr_unique_id = f"{DOMAIN}_late_entities"
        self._attr_icon = "mdi:clock-alert-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            if not self._is_ready():
                self._state = 0
            else:
                self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        self._state = sum(
            1 for eid, h in health_states.items()
            if h == HEALTH_LATE and
            self._evaluator.get_entity_stats(eid) and
            self._evaluator.get_entity_stats(eid).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        )


class LSGStaleSensor(LSGBaseSensor, SensorEntity):
    """Sensor showing count of stale entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Stale Entities"
        self._attr_unique_id = f"{DOMAIN}_stale_entities"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            if not self._is_ready():
                self._state = 0
            else:
                self._update_state()
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        self._state = sum(
            1 for eid, h in health_states.items()
            if h == HEALTH_STALE and
            self._evaluator.get_entity_stats(eid) and
            self._evaluator.get_entity_stats(eid).get("event_count", 0) >= MIN_EVENTS_FOR_NOTIFICATION
        )


class LSGUnknownSensor(LSGBaseSensor, SensorEntity):
    """Sensor showing count of unknown entities."""
    
    def __init__(self, hass: HomeAssistant, evaluator, entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(hass, evaluator, entry)
        self._attr_name = "LSG Unknown Entities"
        self._attr_unique_id = f"{DOMAIN}_unknown_entities"
        self._attr_icon = "mdi:help-circle-outline"
        self._attr_native_unit_of_measurement = "entities"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = 0
    
    @property
    def native_value(self) -> int:
        """Return the count."""
        return self._state
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return learning status."""
        if not self._is_ready():
            return {
                "status": "startup_delay",
                "message": "Sensors will activate after startup delay",
            }
        
        return {
            "status": "active",
        }
    
    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        @callback
        def _update(now=None):
            if not self._is_ready():
                # Show all as unknown during learning
                health_states = self._evaluator.get_all_health_states()
                self._state = len(health_states)
            else:
                self._update_state()
            
            self.async_write_ha_state()
        
        self._unsub_update = async_track_time_interval(
            self._hass, _update, timedelta(minutes=5)
        )
        _update()
    
    def _update_state(self) -> None:
        """Update the sensor state."""
        health_states = self._evaluator.get_all_health_states()
        
        # Count entities still in learning phase
        self._state = sum(
            1 for eid, h in health_states.items()
            if h == HEALTH_UNKNOWN or (
                self._evaluator.get_entity_stats(eid) and
                self._evaluator.get_entity_stats(eid).get("event_count", 0) < MIN_EVENTS_FOR_NOTIFICATION
            )
        )