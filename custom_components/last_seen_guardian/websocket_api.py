"""LSG: Websocket API for panel <-> backend interaction."""
from homeassistant.components import websocket_api
from .const import DOMAIN

def async_register_websocket(hass):
    """Register WS commands."""

    @websocket_api.async_response
    async def ws_get_entities(hass, connection, msg):
        """Return all device/entity summary for panel."""
        entities = hass.data[DOMAIN].get("entities", [])
        await connection.send_result(msg["id"], {"entities": entities})

    hass.components.websocket_api.async_register_command(
        DOMAIN + "/get_entities", ws_get_entities
    )

    # Extend: add additional commands for settings, health, mode switch, etc.