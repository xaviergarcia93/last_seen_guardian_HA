# custom_components/last_seen_guardian/tests/test_registry.py
import pytest
from custom_components.last_seen_guardian import registry

@pytest.mark.asyncio
async def test_get_entities_by_area(hass):
    # Provide fake state
    hass.data["last_seen_guardian"] = {
        "entities": [
            {"entity_id": "sensor.k", "area_id": "kitchen"},
            {"entity_id": "sensor.l", "area_id": "living"},
        ]
    }
    result = registry.get_entities_by_area(hass, "kitchen")
    assert len(result) == 1
    assert result[0]["entity_id"] == "sensor.k"