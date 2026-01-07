"""Panel registration for Last Seen Guardian."""
from __future__ import annotations

import logging
import os
from homeassistant.core import HomeAssistant
from homeassistant.components import frontend, panel_custom

from .const import DOMAIN, PANEL_URL_PATH, PANEL_TITLE, PANEL_ICON

_LOGGER = logging.getLogger(__name__)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Last Seen Guardian panel."""
    
    # Get the path to our www directory
    panel_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "www",
        "last_seen_guardian"
    )
    
    # Normalize path
    panel_dir = os.path.normpath(panel_dir)
    
    # Check if directory exists
    if not os.path.exists(panel_dir):
        _LOGGER.error("Panel directory not found: %s", panel_dir)
        _LOGGER.error("Expected structure: www/last_seen_guardian/panel.js")
        return
    
    # Check if panel.js exists
    panel_js = os.path.join(panel_dir, "panel.js")
    if not os.path.exists(panel_js):
        _LOGGER.error("panel.js not found at: %s", panel_js)
        return
    
    try:
        # Register the panel using panel_custom
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="last-seen-guardian-panel",
            frontend_url_path=PANEL_URL_PATH,
            module_url="/local/last_seen_guardian/panel.js",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=False,
            config_panel_domain=DOMAIN,
        )
        
        _LOGGER.info(
            "Panel registered successfully: %s (icon: %s)",
            PANEL_TITLE,
            PANEL_ICON
        )
        
    except Exception as e:
        _LOGGER.exception("Failed to register panel: %s", e)
        
        # Try alternative registration method (frontend)
        try:
            _LOGGER.info("Attempting alternative panel registration...")
            
            hass.http.register_static_path(
                f"/local/{DOMAIN}",
                panel_dir,
                cache_headers=False
            )
            
            await hass.components.frontend.async_register_built_in_panel(
                component_name="custom",
                sidebar_title=PANEL_TITLE,
                sidebar_icon=PANEL_ICON,
                frontend_url_path=PANEL_URL_PATH,
                require_admin=False,
                config={
                    "_panel_custom": {
                        "name": "last-seen-guardian-panel",
                        "module_url": f"/local/{DOMAIN}/panel.js",
                    }
                },
            )
            
            _LOGGER.info("Panel registered using alternative method")
            
        except Exception as e2:
            _LOGGER.exception("Alternative panel registration also failed: %s", e2)


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the Last Seen Guardian panel."""
    try:
        # Panel custom doesn't provide unregister, but we can remove from frontend
        if hasattr(hass.components, "frontend"):
            hass.components.frontend.async_remove_panel(PANEL_URL_PATH)
            _LOGGER.info("Panel unregistered successfully")
    except Exception as e:
        _LOGGER.exception("Error unregistering panel: %s", e)