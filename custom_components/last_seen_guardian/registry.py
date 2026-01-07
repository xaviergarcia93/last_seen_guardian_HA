"""LSG: Entity/Device registry and classification."""
import logging
from typing import List, Dict, Optional
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
    async_entries_for_config_entry,
    EVENT_ENTITY_REGISTRY_UPDATED
)
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from .const import DOMAIN, LSG_LABELS, LSG_TAGS

_LOGGER = logging.getLogger(__name__)

class LSGRegistry:
    """Entity registry manager with live updates."""
    
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._entities: List[Dict] = []
        self._unsubscribe = None
        
    async def async_setup(self) -> None:
        """Initialize registry and subscribe to updates."""
        await self.async_refresh()
        
        @callback
        def entity_registry_updated(event):
            """Handle entity registry updates."""
            self._hass.async_create_task(self.async_refresh())
        
        self._unsubscribe = self._hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED,
            entity_registry_updated
        )
        _LOGGER.info("Registry initialized with %d entities", len(self._entities))
    
    async def async_refresh(self) -> None:
        """Scan and classify all entities."""
        entity_registry = async_get_entity_registry(self._hass)
        area_registry = async_get_area_registry(self._hass)
        device_registry = async_get_device_registry(self._hass)
        
        entities = []
        for entity in entity_registry.entities.values():
            # Skip disabled entities
            if entity.disabled:
                continue
                
            device_id = entity.device_id
            area_id = entity.area_id
            
            # Get area from device if entity doesn't have one
            if not area_id and device_id:
                device = device_registry.devices.get(device_id)
                if device:
                    area_id = device.area_id
            
            # Extract labels (HA 2023.7+)
            labels = []
            if hasattr(entity, "labels") and entity.labels:
                labels = [l for l in entity.labels if l in LSG_LABELS]
            
            # Extract categories (alternative to tags)
            categories = []
            if hasattr(entity, "categories") and entity.categories:
                categories = [c for c in entity.categories if c in LSG_TAGS]
            
            entities.append({
                "entity_id": entity.entity_id,
                "area_id": area_id,
                "device_id": device_id,
                "domain": entity.domain,
                "platform": entity.platform,
                "labels": labels,
                "categories": categories,
                "disabled": entity.disabled,
                "hidden": entity.hidden_by is not None
            })
        
        self._entities = entities
        self._hass.data[DOMAIN]["entities"] = entities
        _LOGGER.debug("Registry refreshed: %d entities", len(entities))
    
    def get_entities(self) -> List[Dict]:
        """Return all classified entities."""
        return self._entities
    
    def get_by_area(self, area_id: str) -> List[Dict]:
        """Return entities in specific area."""
        return [e for e in self._entities if e["area_id"] == area_id]
    
    def get_by_label(self, label: str) -> List[Dict]:
        """Return entities with specific label."""
        return [e for e in self._entities if label in e.get("labels", [])]
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Return entities with specific category."""
        return [e for e in self._entities if category in e.get("categories", [])]
    
    def get_by_domain(self, domain: str) -> List[Dict]:
        """Return entities of specific domain."""
        return [e for e in self._entities if e["domain"] == domain]
    
    async def async_unload(self) -> None:
        """Cleanup subscriptions."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None