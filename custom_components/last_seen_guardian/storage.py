"""LSG: Persistent storage and state management."""
import logging
from typing import Any, Dict, Optional
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

class LSGStorage:
    """Persistent storage manager for Last Seen Guardian."""
    
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, Any] = {
            "devices": {},
            "config": {
                "global": {
                    "check_every_minutes": 15,
                    "alert_threshold_multiplier": 2.5
                },
                "modes": {
                    "current": "normal",
                    "available": ["normal", "vacation", "night"]
                }
            },
            "learning_state": {},
            "health_history": {}
        }
        
    @classmethod
    async def async_create(cls, hass: HomeAssistant) -> "LSGStorage":
        """Factory method to create and initialize storage."""
        instance = cls(hass)
        await instance.async_load()
        return instance
    
    async def async_load(self) -> None:
        """Load data from storage or initialize defaults."""
        try:
            data = await self._store.async_load()
            if data is not None:
                self._data.update(data)
                _LOGGER.debug("Loaded storage data: %s keys", len(self._data))
            else:
                _LOGGER.info("No storage found, using defaults")
                await self.async_save()
        except Exception as e:
            _LOGGER.exception("Error loading storage: %s", e)
    
    async def async_save(self) -> None:
        """Persist current data to storage."""
        try:
            await self._store.async_save(self._data)
            _LOGGER.debug("Storage saved successfully")
        except Exception as e:
            _LOGGER.exception("Error saving storage: %s", e)
    
    async def async_get(self, key: Optional[str] = None) -> Any:
        """Get storage data or specific key."""
        if key:
            return self._data.get(key, {})
        return self._data
    
    async def async_set(self, key: str, value: Any) -> None:
        """Update and persist a specific key."""
        self._data[key] = value
        await self.async_save()
    
    async def async_update(self, key: str, updates: Dict[str, Any]) -> None:
        """Deep update a nested key."""
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        self._data[key].update(updates)
        await self.async_save()