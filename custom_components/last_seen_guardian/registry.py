"""LSG: Entity/Device registry and classification."""
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LSG_LABELS, LSG_TAGS
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

async def async_setup_registry(hass: HomeAssistant, entry):
    """Scan entities and classify by area, label, tag."""
    entities = []
    entity_registry = async_get_entity_registry(hass)
    area_registry = async_get_area_registry(hass)
    device_registry = async_get_device_registry(hass)

    # Build device/entity lookup
    for entity in entity_registry.entities.values():
        device_id = entity.device_id
        area_id = entity.area_id
        if not area_id and device_id:
            device = device_registry.devices.get(device_id)
            if device:
                area_id = device.area_id
        domain = entity.domain
        labels, tags = [], []
        if hasattr(entity, "labels"):
            labels = [l for l in entity.labels if l in LSG_LABELS]
        if hasattr(entity, "tags"):
            tags = [t for t in entity.tags if t in LSG_TAGS]
        entities.append(dict(
            entity_id=entity.entity_id,
            area_id=area_id,
            device_id=device_id,
            domain=domain,
            labels=labels,
            tags=tags,
        ))
    hass.data[DOMAIN]["entities"] = entities

def get_entities_by_area(hass: HomeAssistant, area_id: str):
    """Return entities belonging to an area."""
    return [e for e in hass.data[DOMAIN]["entities"] if e["area_id"] == area_id]

def get_entities_by_tag(hass: HomeAssistant, tag: str):
    """Return entities by functional tag."""
    return [e for e in hass.data[DOMAIN]["entities"] if tag in e.get("tags", [])]

def get_entities_by_label(hass: HomeAssistant, label: str):
    """Return entities by label."""
    return [e for e in hass.data[DOMAIN]["entities"] if label in e.get("labels", [])]