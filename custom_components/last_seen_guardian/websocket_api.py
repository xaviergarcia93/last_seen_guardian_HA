"""LSG: Websocket API for panel <-> backend interaction with rate limiting."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api

from .const import DOMAIN, LSG_MODES
from .rate_limiter import RateLimiter

_LOGGER = logging.getLogger(__name__)


def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register all WebSocket commands with rate limiting."""
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(hass)
    hass.data[DOMAIN]["rate_limiter"] = rate_limiter
    
    def rate_limited_command(handler):
        """Decorator to add rate limiting to WebSocket commands."""
        async def wrapper(
            hass: HomeAssistant,
            connection: websocket_api.ActiveConnection,
            msg: dict
        ):
            connection_id = id(connection)
            command = msg.get("type", "unknown")
            
            # Check rate limit
            allowed, remaining = rate_limiter.check_rate_limit(connection_id, command)
            
            if not allowed:
                connection.send_error(
                    msg["id"],
                    "rate_limit_exceeded",
                    "Rate limit exceeded. Please slow down your requests."
                )
                return
            
            # Execute handler
            try:
                await handler(hass, connection, msg)
            except Exception as e:
                _LOGGER.exception("Error in WebSocket command %s: %s", command, e)
                connection.send_error(msg["id"], "error", str(e))
        
        return wrapper
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 1: GET ENTITIES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_entities"
    })
    @websocket_api.async_response
    @rate_limited_command
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
                stats = evaluator.get_entity_stats(eid)
                
                result.append({
                    **entity,
                    "health": health_states.get(eid, "unknown"),
                    "stats": stats
                })
            
            connection.send_result(msg["id"], {"entities": result})
            
        except Exception as e:
            _LOGGER.exception("Error in ws_get_entities")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 2: GET CONFIG
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_config"
    })
    @websocket_api.async_response
    @rate_limited_command
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
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 3: SET CONFIG
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_config",
        vol.Required("config"): dict
    })
    @websocket_api.async_response
    @rate_limited_command
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
            
            # Use deep merge via async_update
            await storage.async_update("config", msg["config"])
            
            _LOGGER.info("Configuration updated via WebSocket")
            connection.send_result(msg["id"], {"success": True})
            
        except Exception as e:
            _LOGGER.exception("Error in ws_set_config")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 4: SET MODE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_mode",
        vol.Required("mode"): vol.In(LSG_MODES)
    })
    @websocket_api.async_response
    @rate_limited_command
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
            
            # Use deep merge to only update mode
            await storage.async_update("config", {
                "modes": {"current": mode}
            })
            
            _LOGGER.info("Mode changed to: %s", mode)
            connection.send_result(msg["id"], {"mode": mode, "success": True})
            
        except Exception as e:
            _LOGGER.exception("Error in ws_set_mode")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 5: RUN EVALUATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/run_evaluation"
    })
    @websocket_api.async_response
    @rate_limited_command
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
            
            # Count by health
            summary = {
                "ok": sum(1 for h in results.values() if h == "ok"),
                "late": sum(1 for h in results.values() if h == "late"),
                "stale": sum(1 for h in results.values() if h == "stale"),
                "unknown": sum(1 for h in results.values() if h == "unknown"),
                "total": len(results)
            }
            
            connection.send_result(msg["id"], {
                "results": results,
                "summary": summary
            })
            
        except Exception as e:
            _LOGGER.exception("Error in ws_run_evaluation")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 6: GET HISTORY (v0.8)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_history",
        vol.Required("entity_id"): str,
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=1000))
    })
    @websocket_api.async_response
    @rate_limited_command
    async def ws_get_history(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Get entity history."""
        try:
            evaluator = hass.data[DOMAIN].get("evaluator")
            if not evaluator:
                connection.send_error(msg["id"], "not_ready", "Evaluator not initialized")
                return
            
            entity_id = msg["entity_id"]
            limit = msg.get("limit", 100)
            
            stats = evaluator.get_entity_stats(entity_id)
            if not stats:
                connection.send_result(msg["id"], {
                    "entity_id": entity_id,
                    "history": []
                })
                return
            
            history = stats.get("history", [])[-limit:]
            
            connection.send_result(msg["id"], {
                "entity_id": entity_id,
                "history": history,
                "count": len(history)
            })
            
        except Exception as e:
            _LOGGER.exception("Error in ws_get_history")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMMAND 7: EXPORT DIAGNOSTICS (v0.8)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/export_diagnostics",
        vol.Optional("entity_id"): str
    })
    @websocket_api.async_response
    @rate_limited_command
    async def ws_export_diagnostics(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict
    ) -> None:
        """Export full diagnostics or for specific entity."""
        try:
            from .data_validator import DataValidator
            import time
            
            storage = hass.data[DOMAIN].get("storage")
            evaluator = hass.data[DOMAIN].get("evaluator")
            registry = hass.data[DOMAIN].get("registry")
            
            if not storage or not evaluator:
                connection.send_error(msg["id"], "not_ready", "System not initialized")
                return
            
            entity_id = msg.get("entity_id")
            
            # Single entity diagnostics
            if entity_id:
                stats = evaluator.get_entity_stats(entity_id)
                if not stats:
                    connection.send_error(
                        msg["id"],
                        "not_found",
                        f"Entity {entity_id} not found in learning state"
                    )
                    return
                
                # Find entity metadata
                entity_metadata = None
                if registry:
                    entities = registry.get_entities()
                    entity_metadata = next(
                        (e for e in entities if e["entity_id"] == entity_id),
                        None
                    )
                
                diagnostics = {
                    "entity_id": entity_id,
                    "timestamp": time.time(),
                    "health": evaluator.get_entity_health(entity_id),
                    "stats": stats,
                    "metadata": entity_metadata
                }
                
                connection.send_result(msg["id"], {"diagnostics": diagnostics})
                return
            
            # Full system diagnostics
            config = await storage.async_get("config")
            learning_state = await storage.async_get("learning_state")
            health_states = evaluator.get_all_health_states()
            
            # Get stats
            data_stats = DataValidator.get_data_stats(learning_state)
            
            # Get all entities with health
            entities_data = []
            if registry:
                for entity in registry.get_entities():
                    eid = entity["entity_id"]
                    entities_data.append({
                        "entity_id": eid,
                        "health": health_states.get(eid, "unknown"),
                        "stats": evaluator.get_entity_stats(eid),
                        "metadata": entity
                    })
            
            diagnostics = {
                "version": hass.data[DOMAIN].get("version", "unknown"),
                "timestamp": time.time(),
                "config": config,
                "data_stats": data_stats,
                "health_summary": {
                    "ok": sum(1 for h in health_states.values() if h == "ok"),
                    "late": sum(1 for h in health_states.values() if h == "late"),
                    "stale": sum(1 for h in health_states.values() if h == "stale"),
                    "unknown": sum(1 for h in health_states.values() if h == "unknown"),
                    "total": len(health_states)
                },
                "entities": entities_data
            }
            
            connection.send_result(msg["id"], {"diagnostics": diagnostics})
            
        except Exception as e:
            _LOGGER.exception("Error in ws_export_diagnostics")
            connection.send_error(msg["id"], "error", str(e))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # REGISTER ALL COMMANDS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    websocket_api.async_register_command(hass, ws_get_entities)
    websocket_api.async_register_command(hass, ws_get_config)
    websocket_api.async_register_command(hass, ws_set_config)
    websocket_api.async_register_command(hass, ws_set_mode)
    websocket_api.async_register_command(hass, ws_run_evaluation)
    websocket_api.async_register_command(hass, ws_get_history)
    websocket_api.async_register_command(hass, ws_export_diagnostics)
    
    _LOGGER.info("WebSocket API registered: 7 commands with rate limiting")