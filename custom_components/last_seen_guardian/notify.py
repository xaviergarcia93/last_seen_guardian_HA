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


class LSGNotificationManager:
    """Manages smart notifications with throttling and mode awareness."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize notification manager."""
        self._hass = hass
        self._storage = None
        self._evaluator = None
        
        # Throttling state: {entity_id: last_notification_time}
        self._notification_history: Dict[str, float] = {}
        
        # Track which entities are currently in alert state
        self._entities_in_alert: Set[str] = set()
        
        # Notification queue (for rate limiting)
        self._pending_notifications: List[Dict] = []
        
        # Unsub handlers
        self._unsub_check = None
        
        # Statistics
        self._stats = {
            "total_sent": 0,
            "total_throttled": 0,
            "total_suppressed_by_mode": 0,
        }
    
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
        """Process pending notifications with throttling and mode awareness."""
        if not self._evaluator or not self._storage:
            return
        
        # Get configuration
        try:
            config = await self._storage.async_get("config")
        except Exception as e:
            _LOGGER.error("Could not load config: %s", e)
            return
        
        # Check if notifications are enabled globally
        if not config.get("global", {}).get("enable_notifications", True):
            return
        
        # Get current mode config
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
        newly_alerted = set()
        recovered = set()
        
        # Find entities with issues
        for entity_id, health in health_states.items():
            # Only notify for STALE and LATE
            if health in (HEALTH_STALE, HEALTH_LATE):
                # Check if this is a new alert
                if entity_id not in self._entities_in_alert:
                    newly_alerted.add(entity_id)
                    self._entities_in_alert.add(entity_id)
                
                # Check throttling
                last_notified = self._notification_history.get(entity_id, 0)
                time_since_last = current_time - last_notified
                
                if time_since_last < NOTIFICATION_THROTTLE_SECONDS:
                    self._stats["total_throttled"] += 1
                    continue
                
                # Respect cooldown between different alerts
                if notifications_sent > 0:
                    if time_since_last < NOTIFICATION_COOLDOWN_SECONDS:
                        continue
                
                # Send notification
                await self._async_send_notification(
                    entity_id, health, silent, is_new=entity_id in newly_alerted
                )
                
                self._notification_history[entity_id] = current_time
                notifications_sent += 1
                
            else:
                # Entity recovered
                if entity_id in self._entities_in_alert:
                    recovered.add(entity_id)
                    self._entities_in_alert.discard(entity_id)
        
        # Send recovery notifications (optional)
        if recovered and not silent:
            await self._async_send_recovery_notification(recovered)
        
        if notifications_sent > 0:
            _LOGGER.info(
                "Sent %d notifications (mode: %s, silent: %s)",
                notifications_sent,
                current_mode,
                silent
            )
    
    async def _async_send_notification(
        self, 
        entity_id: str, 
        health: str, 
        silent: bool = False,
        is_new: bool = False
    ) -> None:
        """Send notification for entity health issue."""
        try:
            # Get entity stats and diagnostics
            stats = self._evaluator.get_entity_stats(entity_id)
            diagnosis = self._evaluator.get_diagnostic_context(entity_id) if stats else {}
            
            # Build notification message
            if is_new:
                title = f"🔔 LSG: New Alert - {entity_id}"
            else:
                title = f"LSG Alert: {entity_id}"
            
            if health == HEALTH_STALE:
                severity = "🔴 CRITICAL"
                emoji = "🚨"
            elif health == HEALTH_LATE:
                severity = "🟡 WARNING"
                emoji = "⚠️"
            else:
                severity = "ℹ️ INFO"
                emoji = "ℹ️"
            
            # Format message
            message_parts = [
                f"{emoji}{severity} - Entity health: {health.upper()}",
                ""
            ]
            
            # Add last seen info
            if stats and "last_event" in stats:
                last_seen = _format_relative_time(stats["last_event"])
                message_parts.append(f"⏱ Last seen: {last_seen}")
            
            # Add EWMA info
            if stats and "interval_ewma" in stats and stats["interval_ewma"]:
                expected_interval = _format_duration(stats["interval_ewma"])
                message_parts.append(f"📊 Expected interval: {expected_interval}")
            
            # Add diagnostic info
            if diagnosis and "potential_causes" in diagnosis:
                causes = diagnosis.get("potential_causes", [])
                if causes:
                    message_parts.append("")
                    message_parts.append("🔍 Potential causes:")
                    for cause in causes[:2]:  # Limit to 2 causes
                        message_parts.append(f"  • {cause.replace('_', ' ').title()}")
            
            # Add recommendations
            if diagnosis and "recommendations" in diagnosis:
                recommendations = diagnosis.get("recommendations", [])
                if recommendations:
                    message_parts.append("")
                    message_parts.append("💡 Recommendations:")
                    for rec in recommendations[:2]:  # Limit to 2 recommendations
                        message_parts.append(f"  • {rec}")
            
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
            
            # Add data for mobile notifications
            notification_data = {
                "tag": f"lsg_{entity_id}",
                "group": "last_seen_guardian",
            }
            
            # Add silent flag if in silent mode
            if silent:
                notification_data["priority"] = "low"
                notification_data["silent"] = True
            else:
                notification_data["priority"] = "high"
            
            # Add action buttons
            notification_data["actions"] = [
                {
                    "action": "lsg_view_entity",
                    "title": "View Entity"
                },
                {
                    "action": "lsg_dismiss",
                    "title": "Dismiss"
                }
            ]
            
            data["data"] = notification_data
            
            # Send notification
            domain, service = notify_service.split(".", 1)
            await self._hass.services.async_call(
                domain, service, data
            )
            
            self._stats["total_sent"] += 1
            
            _LOGGER.info(
                "Notification sent for %s (health: %s, silent: %s, new: %s)",
                entity_id,
                health,
                silent,
                is_new
            )
            
        except Exception as e:
            _LOGGER.exception("Error sending notification for %s: %s", entity_id, e)
    
    async def _async_send_recovery_notification(
        self, recovered_entities: Set[str]
    ) -> None:
        """Send notification for recovered entities."""
        try:
            if not recovered_entities:
                return
            
            # Get config
            config = await self._storage.async_get("config")
            notify_service = config.get("global", {}).get(
                "notify_target", DEFAULT_NOTIFY_SERVICE
            )
            
            count = len(recovered_entities)
            
            title = f"✅ LSG: {count} Entit{'y' if count == 1 else 'ies'} Recovered"
            
            message_parts = [
                f"The following entit{'y has' if count == 1 else 'ies have'} returned to normal:",
                ""
            ]
            
            # List recovered entities (max 10)
            for entity_id in list(recovered_entities)[:10]:
                message_parts.append(f"  ✓ {entity_id}")
            
            if count > 10:
                message_parts.append(f"  ... and {count - 10} more")
            
            message = "\n".join(message_parts)
            
            data = {
                "title": title,
                "message": message,
                "data": {
                    "tag": "lsg_recovery",
                    "group": "last_seen_guardian",
                    "priority": "low",
                }
            }
            
            # Send notification
            domain, service = notify_service.split(".", 1)
            await self._hass.services.async_call(
                domain, service, data
            )
            
            _LOGGER.info("Recovery notification sent for %d entities", count)
            
        except Exception as e:
            _LOGGER.exception("Error sending recovery notification: %s", e)
    
    def get_stats(self) -> Dict[str, any]:
        """Get notification statistics."""
        return {
            **self._stats,
            "entities_in_alert": len(self._entities_in_alert),
            "notification_history_size": len(self._notification_history),
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


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f} hours"
    else:
        days = seconds / 86400
        return f"{days:.1f} days"