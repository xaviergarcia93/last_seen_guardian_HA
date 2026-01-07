"""Service handlers for Last Seen Guardian."""
from __future__ import annotations

import logging
import json
import os
from typing import Dict, Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN, LSG_MODES

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_RESET_LEARNING_SCHEMA = vol.Schema({
    vol.Optional("entity_id"): cv.entity_id,
})

SERVICE_FORCE_EVALUATION_SCHEMA = vol.Schema({})

SERVICE_EXPORT_DIAGNOSTICS_SCHEMA = vol.Schema({
    vol.Optional("entity_id"): cv.entity_id,
    vol.Optional("path"): cv.string,
})

SERVICE_SET_MODE_SCHEMA = vol.Schema({
    vol.Required("mode"): vol.In(LSG_MODES),
})

SERVICE_CLEANUP_DATA_SCHEMA = vol.Schema({
    vol.Optional("remove_orphaned", default=True): cv.boolean,
    vol.Optional("compress_history", default=True): cv.boolean,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Last Seen Guardian."""
    
    async def handle_reset_learning(call: ServiceCall) -> None:
        """Handle reset_learning service call."""
        entity_id = call.data.get("entity_id")
        
        evaluator = hass.data[DOMAIN].get("evaluator")
        if not evaluator:
            _LOGGER.error("Evaluator not available")
            return
        
        if entity_id:
            # Reset specific entity
            if entity_id in evaluator._learning_state:
                del evaluator._learning_state[entity_id]
                await evaluator._async_save_learning_state()
                _LOGGER.info("Learning state reset for %s", entity_id)
            else:
                _LOGGER.warning("Entity %s not found in learning state", entity_id)
        else:
            # Reset all
            evaluator._learning_state.clear()
            await evaluator._async_save_learning_state()
            _LOGGER.info("Learning state reset for all entities")
    
    async def handle_force_evaluation(call: ServiceCall) -> None:
        """Handle force_evaluation service call."""
        evaluator = hass.data[DOMAIN].get("evaluator")
        if not evaluator:
            _LOGGER.error("Evaluator not available")
            return
        
        results = await evaluator.async_run_evaluation()
        
        _LOGGER.info(
            "Forced evaluation complete: %d entities evaluated",
            len(results)
        )
    
    async def handle_export_diagnostics(call: ServiceCall) -> None:
        """Handle export_diagnostics service call."""
        from .data_validator import DataValidator
        import time
        
        entity_id = call.data.get("entity_id")
        path = call.data.get("path")
        
        storage = hass.data[DOMAIN].get("storage")
        evaluator = hass.data[DOMAIN].get("evaluator")
        registry_mgr = hass.data[DOMAIN].get("registry")
        
        if not storage or not evaluator:
            _LOGGER.error("System not initialized")
            return
        
        # Generate diagnostics
        if entity_id:
            # Single entity
            stats = evaluator.get_entity_stats(entity_id)
            if not stats:
                _LOGGER.error("Entity %s not found", entity_id)
                return
            
            entity_metadata = None
            if registry_mgr:
                entities = registry_mgr.get_entities()
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
        else:
            # Full system
            config = await storage.async_get("config")
            learning_state = await storage.async_get("learning_state")
            health_states = evaluator.get_all_health_states()
            data_stats = DataValidator.get_data_stats(learning_state)
            
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
                },
                "entities_count": len(health_states)
            }
        
        # Determine path
        if not path:
            filename = f"lsg_diagnostics_{entity_id if entity_id else 'full'}_{int(time.time())}.json"
            path = os.path.join(hass.config.config_dir, filename)
        
        # Write to file
        try:
            with open(path, 'w') as f:
                json.dump(diagnostics, f, indent=2, default=str)
            
            _LOGGER.info("Diagnostics exported to %s", path)
        except Exception as e:
            _LOGGER.exception("Error writing diagnostics to %s: %s", path, e)
    
    async def handle_set_mode(call: ServiceCall) -> None:
        """Handle set_mode service call."""
        mode = call.data["mode"]
        
        storage = hass.data[DOMAIN].get("storage")
        if not storage:
            _LOGGER.error("Storage not available")
            return
        
        await storage.async_update("config", {
            "modes": {"current": mode}
        })
        
        _LOGGER.info("Mode changed to: %s", mode)
    
    async def handle_cleanup_data(call: ServiceCall) -> None:
        """Handle cleanup_data service call."""
        from .data_validator import DataValidator
        
        remove_orphaned = call.data.get("remove_orphaned", True)
        compress_history = call.data.get("compress_history", True)
        
        storage = hass.data[DOMAIN].get("storage")
        evaluator = hass.data[DOMAIN].get("evaluator")
        
        if not storage or not evaluator:
            _LOGGER.error("System not initialized")
            return
        
        learning_state = await storage.async_get("learning_state")
        
        # Remove orphaned entities
        if remove_orphaned:
            entity_registry = async_get_entity_registry(hass)
            valid_entity_ids = [e.entity_id for e in entity_registry.entities.values()]
            
            learning_state, removed = DataValidator.cleanup_orphaned_entities(
                learning_state, valid_entity_ids
            )
            
            _LOGGER.info("Removed %d orphaned entities", removed)
        
        # Compress history
        if compress_history:
            learning_state = DataValidator.compress_history(learning_state)
            _LOGGER.info("History compressed")
        
        # Save cleaned state
        await storage.async_set("learning_state", learning_state)
        
        _LOGGER.info("Data cleanup complete")
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "reset_learning",
        handle_reset_learning,
        schema=SERVICE_RESET_LEARNING_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "force_evaluation",
        handle_force_evaluation,
        schema=SERVICE_FORCE_EVALUATION_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "export_diagnostics",
        handle_export_diagnostics,
        schema=SERVICE_EXPORT_DIAGNOSTICS_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "set_mode",
        handle_set_mode,
        schema=SERVICE_SET_MODE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "cleanup_data",
        handle_cleanup_data,
        schema=SERVICE_CLEANUP_DATA_SCHEMA,
    )
    
    _LOGGER.info("Services registered: 5 services available")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, "reset_learning")
    hass.services.async_remove(DOMAIN, "force_evaluation")
    hass.services.async_remove(DOMAIN, "export_diagnostics")
    hass.services.async_remove(DOMAIN, "set_mode")
    hass.services.async_remove(DOMAIN, "cleanup_data")
    
    _LOGGER.info("Services unloaded")