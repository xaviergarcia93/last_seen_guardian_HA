"""LSG: Persistent storage and state management."""
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

async def async_setup_storage(hass: HomeAssistant, entry) -> None:
    """Initialize persistent storage."""
    hass.data[DOMAIN]["store"] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    # Try loading from storage, if not, init defaults
    data = await hass.data[DOMAIN]["store"].async_load()
    if data is None:
        data = {
            "devices": {},
            "settings": {},
            "learning_state": {},
        }
    hass.data[DOMAIN]["storage_data"] = data

async def async_save_storage(hass: HomeAssistant) -> None:
    """Persist current storage_data."""
    store = hass.data[DOMAIN]["store"]
    await store.async_save(hass.data[DOMAIN]["storage_data"])

async def async_get_storage_data(hass: HomeAssistant, key=None):
    """Get storage data or subkey."""
    data = hass.data[DOMAIN]["storage_data"]
    if key:
        return data.get(key, {})
    return data

async def async_update_storage_data(hass: HomeAssistant, key, value):
    """Update and save particular key in storage."""
    hass.data[DOMAIN]["storage_data"][key] = value
    await async_save_storage(hass)