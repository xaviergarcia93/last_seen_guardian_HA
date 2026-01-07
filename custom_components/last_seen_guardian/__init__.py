"""
Last Seen Guardian Integration for Home Assistant.

Monitors entity activity patterns, learns behavior using EWMA,
and evaluates device health status.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, DEFAULT_CHECK_INTERVAL, PLATFORMS, VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Last Seen Guardian component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("Last Seen Guardian component initialized")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Last Seen Guardian from a config entry."""
    _LOGGER.info("Setting up Last Seen Guardian integration v%s", VERSION)
    
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})
    
    # Track initialization state
    hass.data[DOMAIN]["_ready"] = False
    hass.data[DOMAIN]["_unsub_eval"] = None
    hass.data[DOMAIN]["version"] = VERSION
    
    try:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 1: Initialize Storage Layer
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Initializing storage layer...")
        
        from .storage import LSGStorage
        
        try:
            storage = await LSGStorage.async_create(hass)
            hass.data[DOMAIN]["storage"] = storage
            _LOGGER.info("✓ Storage layer initialized")
        except Exception as e:
            _LOGGER.exception("Failed to initialize storage: %s", e)
            raise ConfigEntryNotReady(f"Storage initialization failed: {e}") from e
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 2: Initialize Registry (Entity Classification)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Initializing entity registry...")
        
        from .registry import LSGRegistry
        
        try:
            registry = LSGRegistry(hass)
            await registry.async_setup()
            hass.data[DOMAIN]["registry"] = registry
            _LOGGER.info("✓ Entity registry initialized with %d entities", 
                        len(registry.get_entities()))
        except Exception as e:
            _LOGGER.exception("Failed to initialize registry: %s", e)
            # Registry is not critical, continue without it
            _LOGGER.warning("Continuing without registry support")
            hass.data[DOMAIN]["registry"] = None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 3: Initialize Evaluator (Learning Engine)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Initializing evaluator engine...")
        
        from .evaluator import LSGEvaluator
        
        try:
            evaluator = LSGEvaluator(hass)
            await evaluator.async_setup()
            hass.data[DOMAIN]["evaluator"] = evaluator
            _LOGGER.info("✓ Evaluator engine initialized")
        except Exception as e:
            _LOGGER.exception("Failed to initialize evaluator: %s", e)
            raise ConfigEntryNotReady(f"Evaluator initialization failed: {e}") from e
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 4: Initialize Notification Manager (v0.6)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Initializing notification manager...")
        
        from .notify import LSGNotificationManager
        
        try:
            notifier = LSGNotificationManager(hass)
            await notifier.async_setup()
            hass.data[DOMAIN]["notifier"] = notifier
            _LOGGER.info("✓ Notification manager initialized")
        except Exception as e:
            _LOGGER.exception("Failed to initialize notifier: %s", e)
            # Notifications are not critical
            _LOGGER.warning("Continuing without notification support")
            hass.data[DOMAIN]["notifier"] = None
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 5: Register WebSocket API
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Registering WebSocket API...")
        
        try:
            from .websocket_api import async_setup_websocket
            
            async_setup_websocket(hass)
            _LOGGER.info("✓ WebSocket API registered")
        except Exception as e:
            _LOGGER.exception("Failed to register WebSocket API: %s", e)
            # WebSocket is critical for panel functionality
            raise ConfigEntryNotReady(f"WebSocket API registration failed: {e}") from e
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 6: Register Frontend Panel
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Registering frontend panel...")
        
        try:
            from .panel import async_register_panel
            
            await async_register_panel(hass)
            _LOGGER.info("✓ Frontend panel registered")
        except Exception as e:
            _LOGGER.exception("Failed to register panel: %s", e)
            # Panel registration failure is not critical
            _LOGGER.warning("Panel not available, but core functionality will work")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 7: Setup Periodic Evaluation Loop
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Setting up periodic evaluation...")
        
        # Get check interval from configuration
        check_interval = await _async_get_check_interval(hass, storage)
        
        async def _periodic_evaluation(now=None) -> None:
            """Execute periodic evaluation of all entities."""
            try:
                evaluator_instance = hass.data[DOMAIN].get("evaluator")
                if evaluator_instance:
                    _LOGGER.debug("Running periodic evaluation...")
                    results = await evaluator_instance.async_run_evaluation()
                    _LOGGER.debug("Evaluation completed: %d entities processed", 
                                len(results))
                else:
                    _LOGGER.warning("Evaluator not available for periodic run")
            except Exception as e:
                _LOGGER.exception("Error during periodic evaluation: %s", e)
        
        # Run initial evaluation
        hass.async_create_task(_periodic_evaluation())
        
        # Schedule periodic evaluations
        unsub = async_track_time_interval(
            hass,
            _periodic_evaluation,
            timedelta(minutes=check_interval)
        )
        hass.data[DOMAIN]["_unsub_eval"] = unsub
        
        _LOGGER.info("✓ Periodic evaluation scheduled (every %d minutes)", 
                    check_interval)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 8: Setup Platforms (Sensors)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Setting up platforms...")
        
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("✓ Platforms setup complete")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 9: Register Services
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Registering services...")
        
        try:
            from .services import async_setup_services
            
            await async_setup_services(hass)
            _LOGGER.info("✓ Services registered")
        except Exception as e:
            _LOGGER.exception("Failed to register services: %s", e)
            # Services are not critical
            _LOGGER.warning("Continuing without services")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 10: Register Logbook Integration
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        _LOGGER.debug("Registering logbook integration...")
        
        try:
            from . import logbook
            # Logbook auto-discovers via async_describe_events
            _LOGGER.info("✓ Logbook integration available")
        except Exception as e:
            _LOGGER.exception("Failed to import logbook: %s", e)
            _LOGGER.warning("Continuing without logbook integration")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 11: Mark as Ready
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        hass.data[DOMAIN]["_ready"] = True
        _LOGGER.info("═══════════════════════════════════════════════")
        _LOGGER.info("✓ Last Seen Guardian v%s fully initialized", VERSION)
        _LOGGER.info("═══════════════════════════════════════════════")
        
        return True
        
    except ConfigEntryNotReady:
        # Re-raise to let HA retry initialization
        raise
        
    except Exception as e:
        _LOGGER.exception("Unexpected error during setup: %s", e)
        # Cleanup partial initialization
        await _async_cleanup(hass)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Last Seen Guardian integration")
    
    try:
        # 1. Unload services FIRST
        try:
            from .services import async_unload_services
            await async_unload_services(hass)
            _LOGGER.debug("✓ Services unloaded")
        except Exception as e:
            _LOGGER.exception("Error unloading services: %s", e)
        
        # 2. Unload platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            # 3. Cleanup all components
            await _async_cleanup(hass)
            
            # 4. Clear domain data
            if DOMAIN in hass.data:
                hass.data.pop(DOMAIN)
            
            _LOGGER.info("✓ Last Seen Guardian unloaded successfully")
        
        return unload_ok
        
    except Exception as e:
        _LOGGER.exception("Error during unload: %s", e)
        return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reloading Last Seen Guardian integration")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRIVATE HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _async_get_check_interval(
    hass: HomeAssistant, 
    storage: "LSGStorage"
) -> int:
    """Get check interval from configuration or use default."""
    try:
        config = await storage.async_get("config")
        interval = config.get("global", {}).get("check_every_minutes")
        
        if interval is not None:
            interval = int(interval)
            if interval < 1:
                _LOGGER.warning(
                    "Invalid check interval %d, using default %d",
                    interval,
                    DEFAULT_CHECK_INTERVAL
                )
                return DEFAULT_CHECK_INTERVAL
            return interval
            
    except Exception as e:
        _LOGGER.warning(
            "Could not read check_every_minutes from config: %s. Using default %d",
            e,
            DEFAULT_CHECK_INTERVAL
        )
    
    return DEFAULT_CHECK_INTERVAL


async def _async_cleanup(hass: HomeAssistant) -> None:
    """Cleanup all resources."""
    _LOGGER.debug("Starting cleanup...")
    
    domain_data = hass.data.get(DOMAIN, {})
    
    # 1. Cancel periodic evaluation
    unsub_eval = domain_data.get("_unsub_eval")
    if unsub_eval:
        try:
            unsub_eval()
            _LOGGER.debug("✓ Periodic evaluation cancelled")
        except Exception as e:
            _LOGGER.exception("Error cancelling evaluation loop: %s", e)
    
    # 2. Unload notification manager
    notifier = domain_data.get("notifier")
    if notifier:
        try:
            if hasattr(notifier, "async_unload"):
                await notifier.async_unload()
            _LOGGER.debug("✓ Notification manager unloaded")
        except Exception as e:
            _LOGGER.exception("Error unloading notifier: %s", e)
    
    # 3. Unload evaluator
    evaluator = domain_data.get("evaluator")
    if evaluator:
        try:
            if hasattr(evaluator, "async_unload"):
                await evaluator.async_unload()
            _LOGGER.debug("✓ Evaluator unloaded")
        except Exception as e:
            _LOGGER.exception("Error unloading evaluator: %s", e)
    
    # 4. Unload registry
    registry = domain_data.get("registry")
    if registry:
        try:
            if hasattr(registry, "async_unload"):
                await registry.async_unload()
            _LOGGER.debug("✓ Registry unloaded")
        except Exception as e:
            _LOGGER.exception("Error unloading registry: %s", e)
    
    # 5. Save and close storage
    storage = domain_data.get("storage")
    if storage:
        try:
            if hasattr(storage, "async_save"):
                await storage.async_save()
            _LOGGER.debug("✓ Storage saved and closed")
        except Exception as e:
            _LOGGER.exception("Error saving storage: %s", e)
    
    # 6. Clear references
    domain_data.clear()
    
    _LOGGER.debug("Cleanup completed")