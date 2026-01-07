"""LSG: Websocket API for panel <-> backend interaction."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api
from .const import DOMAIN, LSG_MODES

_LOGGER = logging.getLogger(__name__)

def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register all WebSocket commands."""
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_entities"
    })
    @websocket_api.async_response
    async def ws_get_entities(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Return all entities with health status."""
        try:
            registry = hass.data[DOMAIN].get("registry")
            evaluator = hass.data[DOMAIN].get("evaluator")
            
            if not registry or not evaluator:
                connection.send_error(msg["id"], "not_ready", "System not initialized")
                return
            
            entities = registry.get_entities()
            health_states = evaluator.get_all_health_states()
            
            # Enrich entities with health data
            result = []
            for entity in entities:
                eid = entity["entity_id"]
                result.append({
                    **entity,
                    "health": health_states.get(eid, "unknown"),
                    "stats": evaluator.get_entity_stats(eid)
                })
            
            connection.send_result(msg["id"], {"entities": result})
        except Exception as e:
            _LOGGER.exception("Error in ws_get_entities")
            connection.send_error(msg["id"], "error", str(e))
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_config"
    })
    @websocket_api.async_response
    async def ws_get_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Return current configuration."""
        try:
            storage = hass.data[DOMAIN].get("storage")
            if not storage:
                connection.send_error(msg["id"], "not_ready", "Storage not initialized")
                return
            
            config = await storage.async_get("config")
            connection.send_result(msg["id"], {"config": config})
        except Exception as e:
            _LOGGER.exception("Error in ws_get_config")
            connection.send_error(msg["id"], "error", str(e))
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_config",
        vol.Required("config"): dict
    })
    @websocket_api.async_response
    async def ws_set_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Update configuration."""
        try:
            storage = hass.data[DOMAIN].get("storage")
            if not storage:
                connection.send_error(msg["id"], "not_ready", "Storage not initialized")
                return
            
            await storage.async_update("config", msg["config"])
            connection.send_result(msg["id"], {"success": True})
        except Exception as e:
            _LOGGER.exception("Error in ws_set_config")
            connection.send_error(msg["id"], "error", str(e))
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_mode",
        vol.Required("mode"): vol.In(LSG_MODES)
    })
    @websocket_api.async_response
    async def ws_set_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Change operation mode."""
        try:
            storage = hass.data[DOMAIN].get("storage")
            if not storage:
                connection.send_error(msg["id"], "not_ready", "Storage not initialized")
                return
            
            mode = msg["mode"]
            await storage.async_update("config", {
                "modes": {"current": mode}
            })
            
            _LOGGER.info("Mode changed to: %s", mode)
            connection.send_result(msg["id"], {"mode": mode})
        except Exception as e:
            _LOGGER.exception("Error in ws_set_mode")
            connection.send_error(msg["id"], "error", str(e))
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/run_evaluation"
    })
    @websocket_api.async_response
    async def ws_run_evaluation(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Force evaluation run."""
        try:
            evaluator = hass.data[DOMAIN].get("evaluator")
            if not evaluator:
                connection.send_error(msg["id"], "not_ready", "Evaluator not initialized")
                return
            
            results = await evaluator.async_run_evaluation()
            connection.send_result(msg["id"], {"results": results})
        except Exception as e:
            _LOGGER.exception("Error in ws_run_evaluation")
            connection.send_error(msg["id"], "error", str(e))
    
    # Register all commands
    websocket_api.async_register_command(hass, ws_get_entities)
    websocket_api.async_register_command(hass, ws_get_config)
    websocket_api.async_register_command(hass, ws_set_config)
    websocket_api.async_register_command(hass, ws_set_mode)
    websocket_api.async_register_command(hass, ws_run_evaluation)
    
    _LOGGER.info("WebSocket API registered")