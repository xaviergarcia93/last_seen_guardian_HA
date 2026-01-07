from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .storage import LSGStorage

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # Storage asíncrono
    storage = await LSGStorage.async_create(hass)
    hass.data[DOMAIN]["storage"] = storage

    # WebSocket API
    try:
        from .websocket_api import async_setup_websocket

        async_setup_websocket(hass)
    except Exception as e:
        _LOGGER.exception("Error registrando WebSocket API: %s", e)

    # Panel
    try:
        from .panel import async_register_panel

        await async_register_panel(hass)
    except Exception as e:
        _LOGGER.exception("Error registrando panel: %s", e)

    # Evaluator loop (v0.5.0)
    hass.data[DOMAIN]["_unsub_eval"] = None

    async def _run_eval(now=None) -> None:
        """Run evaluation (no alerts yet)."""
        try:
            from .evaluator import async_run_evaluation

            await async_run_evaluation(hass)
        except Exception:
            _LOGGER.exception("Error en evaluación periódica")

    try:
        cfg = await storage.async_get()
        every_min = int(cfg.get("config", {}).get("global", {}).get("check_every_minutes", 15))
        if every_min < 1:
            every_min = 1
    except Exception:
        _LOGGER.exception("No pude leer check_every_minutes; uso 15")
        every_min = 15

    hass.async_create_task(_run_eval())

    unsub = async_track_time_interval(hass, _run_eval, timedelta(minutes=every_min))
    hass.data[DOMAIN]["_unsub_eval"] = unsub

    _LOGGER.info("Last Seen Guardian: evaluator loop cada %s minutos", every_min)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Cancelar loop
    unsub = hass.data.get(DOMAIN, {}).get("_unsub_eval")
    if unsub:
        try:
            unsub()
        except Exception:
            _LOGGER.exception("Error cancelando evaluator loop")

    # Limpieza
    hass.data.get(DOMAIN, {}).pop("_unsub_eval", None)
    hass.data.get(DOMAIN, {}).pop("storage", None)
    return True