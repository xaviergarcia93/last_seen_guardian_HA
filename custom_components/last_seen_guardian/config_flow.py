"""LSG: UI config flow."""
from homeassistant import config_entries
from .const import DOMAIN

class LsgConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a LSG config flow."""

    async def async_step_user(self, user_input=None):
        """Handle user setup panel."""
        errors = {}
        if user_input is not None:
            # Save settings if validated
            return self.async_create_entry(title="LSG", data={})
        return self.async_show_form(
            step_id="user", data_schema=None, errors=errors
        )