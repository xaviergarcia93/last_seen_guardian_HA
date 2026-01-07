"""LSG: Persistent storage and state management with deep merge support."""
import logging
from typing import Any, Dict, Optional
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class LSGStorage:
    """Persistent storage manager for Last Seen Guardian with deep merge."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize storage manager."""
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, Any] = {
            "devices": {},
            "config": {
                "global": {
                    "check_every_minutes": 15,
                    "alert_threshold_multiplier": 2.5,
                    "enable_notifications": True,
                    "notify_target": "notify.notify"
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
                # Deep merge loaded data with defaults
                self._data = self._deep_merge(self._data, data)
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
        """
        Get storage data or specific key.
        
        Args:
            key: Optional key to retrieve. If None, returns all data.
        
        Returns:
            Data for the key or all data if key is None.
        """
        if key:
            return self._data.get(key, {})
        return self._data
    
    async def async_set(self, key: str, value: Any) -> None:
        """
        Update and persist a specific key (replaces entire value).
        
        Args:
            key: Key to update
            value: New value for the key
        """
        self._data[key] = value
        await self.async_save()
    
    async def async_update(self, key: str, updates: Dict[str, Any]) -> None:
        """
        Deep merge updates into a nested key.
        
        This performs a recursive merge, preserving existing nested keys
        that are not being updated.
        
        Args:
            key: Top-level key to update
            updates: Dictionary of updates to merge
        
        Example:
            # Current state:
            config = {
                "global": {"check_every_minutes": 15, "threshold": 2.5},
                "modes": {"current": "normal"}
            }
            
            # Update only modes.current:
            await storage.async_update("config", {
                "modes": {"current": "vacation"}
            })
            
            # Result (global preserved):
            config = {
                "global": {"check_every_minutes": 15, "threshold": 2.5},
                "modes": {"current": "vacation"}
            }
        """
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        
        # Deep merge updates
        self._data[key] = self._deep_merge(self._data[key], updates)
        await self.async_save()
    
    async def async_delete(self, key: str) -> None:
        """
        Delete a key from storage.
        
        Args:
            key: Key to delete
        """
        if key in self._data:
            del self._data[key]
            await self.async_save()
            _LOGGER.debug("Deleted key: %s", key)
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """
        Recursively merge two dictionaries.
        
        Args:
            base: Base dictionary
            updates: Dictionary with updates
        
        Returns:
            Merged dictionary
        
        Note:
            - For nested dicts: recursively merge
            - For other types: updates value replaces base value
            - For lists: updates list replaces base list (no merge)
        """
        result = base.copy()
        
        for key, value in updates.items():
            if (
                key in result 
                and isinstance(result[key], dict) 
                and isinstance(value, dict)
            ):
                # Recursively merge nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Replace value (including lists)
                result[key] = value
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        learning_state = self._data.get("learning_state", {})
        
        return {
            "total_keys": len(self._data),
            "learning_state_entities": len(learning_state),
            "config_present": "config" in self._data,
            "devices_count": len(self._data.get("devices", {})),
        }