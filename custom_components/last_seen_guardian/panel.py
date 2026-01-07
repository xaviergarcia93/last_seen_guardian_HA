from __future__ import annotations

import inspect
from homeassistant.core import HomeAssistant

from .const import PANEL_URL_PATH, PANEL_TITLE, PANEL_ICON

async def _maybe_await(result):
    """Si result es coroutine, await; si no, devolver tal cual."""
    if inspect.isawaitable(result):
        return await result
    return result

async def async_register_panel(hass: HomeAssistant) -> None:
    """
    Registra el panel (JS) de la forma más compatible posible.
    Tries panel_custom (recomendado), fallback a frontend.
    """
    module_url = "/local/last_seen_guardian/panel.js?v=0.4.4"

    # Intento 1: panel_custom
    try:
        from homeassistant.components import panel_custom

        res = panel_custom.async_register_panel(
            hass,
            webcomponent_name="last-seen-guardian-panel",
            frontend_url_path=PANEL_URL_PATH,
            module_url=module_url,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=True,
            config={},
        )
        await _maybe_await(res)
        return
    except Exception:
        # Fallback si falla el panel_custom
        pass

    # Intento 2: frontend legacy
    from homeassistant.components import frontend

    res = frontend.async_register_panel(
        hass,
        component_name="custom",
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        config={
            "_panel_custom": {
                "name": "last-seen-guardian-panel",
                "js_url": module_url,
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=True,
    )
    await _maybe_await(res)