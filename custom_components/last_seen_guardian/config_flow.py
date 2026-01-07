"""Config flow for Last Seen Guardian integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_CHECK_INTERVAL, DEFAULT_THRESHOLD_MULTIPLIER

_LOGGER = logging.getLogger(__name__)


class LSGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Last Seen Guardian."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Create entry
            return self.async_create_entry(
                title="Last Seen Guardian",
                data=user_input,
            )

        # Show form
        data_schema = vol.Schema({
            vol.Optional(
                "check_every_minutes",
                default=DEFAULT_CHECK_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            vol.Optional(
                "alert_threshold_multiplier",
                default=DEFAULT_THRESHOLD_MULTIPLIER
            ): vol.All(vol.Coerce(float), vol.Range(min=1.5, max=10.0)),
            vol.Optional(
                "enable_notifications",
                default=True
            ): cv.boolean,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "default_interval": str(DEFAULT_CHECK_INTERVAL),
                "default_multiplier": str(DEFAULT_THRESHOLD_MULTIPLIER),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LSGOptionsFlowHandler:
        """Get the options flow for this handler."""
        return LSGOptionsFlowHandler(config_entry)


class LSGOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Last Seen Guardian."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input
            check_interval = user_input.get("check_every_minutes")
            threshold = user_input.get("alert_threshold_multiplier")

            if check_interval and (check_interval < 5 or check_interval > 120):
                errors["check_every_minutes"] = "invalid_interval"

            if threshold and (threshold < 1.5 or threshold > 10.0):
                errors["alert_threshold_multiplier"] = "invalid_threshold"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_data = {**self.config_entry.data, **self.config_entry.options}

        options_schema = vol.Schema({
            vol.Optional(
                "check_every_minutes",
                default=current_data.get("check_every_minutes", DEFAULT_CHECK_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            vol.Optional(
                "alert_threshold_multiplier",
                default=current_data.get(
                    "alert_threshold_multiplier",
                    DEFAULT_THRESHOLD_MULTIPLIER
                )
            ): vol.All(vol.Coerce(float), vol.Range(min=1.5, max=10.0)),
            vol.Optional(
                "enable_notifications",
                default=current_data.get("enable_notifications", True)
            ): cv.boolean,
            vol.Optional(
                "notify_target",
                default=current_data.get("notify_target", "notify.notify")
            ): cv.string,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "current_interval": str(
                    current_data.get("check_every_minutes", DEFAULT_CHECK_INTERVAL)
                ),
                "current_multiplier": str(
                    current_data.get(
                        "alert_threshold_multiplier",
                        DEFAULT_THRESHOLD_MULTIPLIER
                    )
                ),
            },
        )