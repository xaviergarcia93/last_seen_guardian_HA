"""
LSG Notification Manager - v0.6
Smart alerts with throttling, mode awareness, and multi-channel support.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional, List, Set
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

# CRITICAL: Minimum events before notifying
MIN_EVENTS_FOR_NOTIFICATION = 10


class LSGNotificationManager:
    """Manages smart notifications with throttling and mode awareness."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize notification manager."""
        self._hass = hass
        self._storage = None
        self._evaluator = None
        
        # Throttling state
        self._notification_history: Dict[str, float] = {}
        self._entities_in_alert: Set[str] = set()
        self._pending_notifications: List[Dict] = []
        
        # Unsub handlers
        self._unsub_check = None
        
        # Statistics
        self._stats = {
            "total_sent": 0,
            "total_throttled": 0,
            "total_suppressed_by_mode": 0,
            "total_suppressed_by_learning": 0,
        }
        
        # Startup grace period (don't notify for first 10 minutes)
        self._startup_time = time.time()
        self._startup_grace_period = 600  # 10 minutes
    
    async def async_setup(self) -> None:
        """Initialize notification manager."""
        self._storage = self._hass.data[DOMAIN].get("storage")
        self._evaluator = self._hass.data[DOMAIN].get("evaluator")
        
        # CRITICAL FIX: Check every 5 minutes, not 1 minute
        self._unsub_check = async_track_time_interval(
            self._hass,
            self._async_process_notifications,
            timedelta(minutes=5)  # Changed from 1 to 5
        )
        
        _LOGGER.info("Notification manager initialized (startup grace: %ds)", 
                    self._startup_grace_period)
    
    async def _async_process_notifications(self, now=None) -> None:
        """Process pending notifications with throttling and mode awareness."""
        if not self._evaluator or not self._storage:
            return
        
        # CRITICAL FIX: Don't send notifications during startup
        if time.time() - self._startup_time < self._startup_grace_period:
            _LOGGER.debug("Still in startup grace period, skipping notifications")
            return
        
        # Get configuration
        try:
            config = await self._storage.async_get("config")
        except Exception as e:
            _LOGGER.error("Could not load config: %s", e)
            return
        
        # Check if notifications are enabled globally
        if not config.get("global", {}).get("enable_notifications", True):
            _LOGGER.debug("Notifications disabled globally")
            return
        
        # Get current mode config
        current_mode = config.get("modes", {}).get("current", "normal")
        mode_config = MODE_CONFIGS.get(current_mode, MODE_CONFIGS["normal"])
        
        # Check if alerts are enabled for current mode
        if not mode_config.get("alert_enabled", True):
            self._stats["total_suppressed_by_mode"] += 1
            _LOGGER.debug("Alerts disabled for mode: %s", current_mode)
            return
        
        # Get silent mode status
        silent = mode_config.get("silent_alerts", False)
        
        # Get all health states
        health_states = self._evaluator.get_all_health_states()
        
        current_time = time.time()
        notifications_sent = 0
        notifications_suppressed = 0
        
        for entity_id, health in health_states.items():
            # Only notify for STALE (not LATE to reduce noise)
            if health != HEALTH_STALE:
                continue
            
            # CRITICAL FIX: Check if entity has enough learning data
            stats = self._evaluator.get_entity_stats(entity_id)
            if not stats or stats.get("event_count", 0) < MIN_EVENTS_FOR_NOTIFICATION:
                notifications_suppressed += 1
                self._stats["total_suppressed_by_learning"] += 1
                continue
            
            # Check throttling
            last_notified = self._notification_history.get(entity_id, 0)
            time_since_last = current_time - last_notified
            
            if time_since_last < NOTIFICATION_THROTTLE_SECONDS:
                notifications_suppressed += 1
                self._stats["total_throttled"] += 1
                continue
            
            # Respect cooldown between different alerts
            if notifications_sent > 0:
                # Only send max 3 notifications per cycle
                if notifications_sent >= 3:
                    notifications_suppressed += 1
                    continue
            
            # Send notification
            await self._async_send_notification(
                entity_id, health, silent, stats
            )
            
            self._notification_history[entity_id] = current_time
            self._entities_in_alert.add(entity_id)
            notifications_sent += 1
        
        if notifications_sent > 0 or notifications_suppressed > 0:
            _LOGGER.info(
                "Notification cycle complete: %d sent, %d suppressed",
                notifications_sent,
                notifications_suppressed
            )
    
    async def _async_send_notification(
        self, 
        entity_id: str, 
        health: str, 
        silent: bool = False,
        stats: Dict = None
    ) -> None:
        """Send notification for entity health issue."""
        try:
            diagnosis = self._evaluator.get_diagnostic_context(entity_id) if stats else {}
            
            # Build notification message
            title = f"🚨 LSG Alert: {entity_id}"
            
            severity = "🔴 CRITICAL"
            
            # Format message
            message_parts = [
                f"{severity} - Entity not responding",
                ""
            ]
            
            # Add last seen info
            if stats and "last_event" in stats:
                last_seen = _format_relative_time(stats["last_event"])
                message_parts.append(f"⏱ Last seen: {last_seen}")
            
            # Add ONE recommendation
            if diagnosis and "recommendations" in diagnosis:
                recommendations = diagnosis.get("recommendations", [])
                if recommendations:
                    message_parts.append("")
                    message_parts.append(f"💡 {recommendations[0]}")
            
            message = "\n".join(message_parts)
            
            # Get notification service
            config = await self._storage.async_get("config")
            notify_service = config.get("global", {}).get(
                "notify_target", DEFAULT_NOTIFY_SERVICE
            )
            
            # Prepare notification data
            data = {
                "title": title,
                "message": message,
            }
            
            if silent:
                data["data"] = {"priority": "low", "silent": True}
            
            # Send notification
            domain, service = notify_service.split(".", 1)
            await self._hass.services.async_call(
                domain, service, data
            )
            
            self._stats["total_sent"] += 1
            
            _LOGGER.info("Notification sent for %s", entity_id)
            
        except Exception as e:
            _LOGGER.exception("Error sending notification for %s: %s", entity_id, e)
    
    def get_stats(self) -> Dict[str, any]:
        """Get notification statistics."""
        return {
            **self._stats,
            "entities_in_alert": len(self._entities_in_alert),
        }
    
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