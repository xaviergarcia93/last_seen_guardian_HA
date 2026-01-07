"""
LSG Notification Manager - v0.6
Smart alerts with throttling, mode awareness, and multi-channel support.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional, List
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from .const import (
    DOMAIN,
    HEALTH_STALE,
    HEALTH_LATE,
    DEFAULT_NOTIFY_SERVICE,
    NOTIFICATION_THROTTLE_SECONDS,
    NOTIFICATION_COOLDOWN_SECONDS,
    MODE_CONFIGS,
)

_LOGGER = logging.getLogger(__name__)


class LSGNotificationManager:
    """Manages smart notifications with throttling and mode awareness."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize notification manager."""
        self._hass = hass
        self._storage = None
        self._evaluator = None
        
        # Throttling state: {entity_id: last_notification_time}
        self._notification_history: Dict[str, float] = {}
        
        # Notification queue
        self._pending_notifications: List[Dict] = []
        
        # Unsub handler
        self._unsub_check = None
    
    async def async_setup(self) -> None:
        """Initialize notification manager."""
        self._storage = self._hass.data[DOMAIN].get("storage")
        self._evaluator = self._hass.data[DOMAIN].get("evaluator")
        
        # Check for pending notifications every minute
        self._unsub_check = async_track_time_interval(
            self._hass,
            self._async_process_notifications,
            timedelta(minutes=1)
        )
        
        _LOGGER.info("Notification manager initialized")
    
    async def _async_process_notifications(self, now=None) -> None:
        """Process pending notifications with throttling."""
        if not self._evaluator:
            return
        
        # Get current mode config
        config = await self._storage.async_get("config")
        current_mode = config.get("modes", {}).get("current", "normal")
        mode_config = MODE_CONFIGS.get(current_mode, MODE_CONFIGS["normal"])
        
        # Check if alerts are enabled for current mode
        if not mode_config.get("alert_enabled", True):
            _LOGGER.debug("Alerts disabled for mode: %s", current_mode)
            return
        
        # Get silent mode status
        silent = mode_config.get("silent_alerts", False)
        
        # Get all health states
        health_states = self._evaluator.get_all_health_states()
        
        current_time = time.time()
        notifications_sent = 0
        
        for entity_id, health in health_states.items():
            # Only notify for STALE and LATE
            if health not in (HEALTH_STALE, HEALTH_LATE):
                continue
            
            # Check throttling
            last_notified = self._notification_history.get(entity_id, 0)
            time_since_last = current_time - last_notified
            
            if time_since_last < NOTIFICATION_THROTTLE_SECONDS:
                continue
            
            # Respect cooldown between different alerts
            if notifications_sent > 0:
                if time_since_last < NOTIFICATION_COOLDOWN_SECONDS:
                    continue
            
            # Send notification
            await self._async_send_notification(
                entity_id, health, silent
            )
            
            self._notification_history[entity_id] = current_time
            notifications_sent += 1
        
        if notifications_sent > 0:
            _LOGGER.info("Sent %d notifications", notifications_sent)
    
    async def _async_send_notification(
        self, entity_id: str, health: str, silent: bool = False
    ) -> None:
        """Send notification for entity health issue."""
        try:
            # Get entity stats and diagnostics
            stats = self._evaluator.get_entity_stats(entity_id)
            diagnosis = self._evaluator.get_diagnostic_context(entity_id)
            
            # Build notification message
            title = f"LSG Alert: {entity_id}"
            
            if health == HEALTH_STALE:
                severity = "🔴 CRITICAL"
            elif health == HEALTH_LATE:
                severity = "🟡 WARNING"
            else:
                severity = "ℹ️ INFO"
            
            # Format message
            message_parts = [
                f"{severity} - Entity health: {health.upper()}",
                ""
            ]
            
            # Add last seen info
            if stats and "last_event" in stats:
                last_seen = _format_relative_time(stats["last_event"])
                message_parts.append(f"⏱ Last seen: {last_seen}")
            
            # Add diagnostic info
            if diagnosis and "potential_causes" in diagnosis:
                causes = diagnosis.get("potential_causes", [])
                if causes:
                    message_parts.append("")
                    message_parts.append("Potential causes:")
                    for cause in causes[:2]:  # Limit to 2 causes
                        message_parts.append(f"• {cause.replace('_', ' ').title()}")
            
            # Add recommendations
            if diagnosis and "recommendations" in diagnosis:
                recommendations = diagnosis.get("recommendations", [])
                if recommendations:
                    message_parts.append("")
                    message_parts.append("Recommendations:")
                    for rec in recommendations[:2]:  # Limit to 2 recommendations
                        message_parts.append(f"• {rec}")
            
            message = "\n".join(message_parts)
            
            # Get notification service from config
            config = await self._storage.async_get("config")
            notify_service = config.get("global", {}).get(
                "notify_target", DEFAULT_NOTIFY_SERVICE
            )
            
            # Prepare notification data
            data = {
                "title": title,
                "message": message,
            }
            
            # Add silent flag if in silent mode
            if silent:
                data["data"] = {"priority": "low", "silent": True}
            
            # Send notification
            domain, service = notify_service.split(".", 1)
            await self._hass.services.async_call(
                domain, service, data
            )
            
            _LOGGER.info(
                "Notification sent for %s (health: %s, silent: %s)",
                entity_id,
                health,
                silent
            )
            
        except Exception as e:
            _LOGGER.exception("Error sending notification for %s: %s", entity_id, e)
    
    async def async_unload(self) -> None:
        """Cleanup notification manager."""
        if self._unsub_check:
            self._unsub_check()
            self._unsub_check = None
        
        _LOGGER.info("Notification manager unloaded")


def _format_relative_time(timestamp: float) -> str:
    """Format timestamp as relative time."""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        return f"{int(diff / 60)} minutes ago"
    elif diff < 86400:
        return f"{int(diff / 3600)} hours ago"
    else:
        return f"{int(diff / 86400)} days ago"