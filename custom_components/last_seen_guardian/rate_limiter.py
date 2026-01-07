"""
Rate Limiter for WebSocket API - v0.6
Prevents spam and abuse of WebSocket commands.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple
import logging

from homeassistant.core import HomeAssistant

from .const import RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_CALLS

_LOGGER = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for WebSocket commands."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize rate limiter."""
        self._hass = hass
        # Store: {connection_id: [(timestamp, command), ...]}
        self._calls: Dict[str, list] = defaultdict(list)
        
    def check_rate_limit(self, connection_id: str, command: str) -> Tuple[bool, int]:
        """
        Check if connection has exceeded rate limit.
        
        Returns:
            Tuple of (is_allowed, remaining_quota)
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        # Clean old calls outside window
        if connection_id in self._calls:
            self._calls[connection_id] = [
                (ts, cmd) for ts, cmd in self._calls[connection_id]
                if ts > window_start
            ]
        
        # Count calls in current window
        current_calls = len(self._calls[connection_id])
        
        # Check limit
        if current_calls >= RATE_LIMIT_MAX_CALLS:
            _LOGGER.warning(
                "Rate limit exceeded for connection %s: %d calls in %ds window",
                connection_id,
                current_calls,
                RATE_LIMIT_WINDOW
            )
            return False, 0
        
        # Record this call
        self._calls[connection_id].append((now, command))
        
        remaining = RATE_LIMIT_MAX_CALLS - current_calls - 1
        return True, remaining
    
    def reset_connection(self, connection_id: str) -> None:
        """Reset rate limit for a connection."""
        if connection_id in self._calls:
            del self._calls[connection_id]
    
    def get_stats(self, connection_id: str) -> Dict[str, int]:
        """Get rate limit stats for connection."""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        if connection_id not in self._calls:
            return {
                "calls_in_window": 0,
                "remaining_quota": RATE_LIMIT_MAX_CALLS,
                "window_seconds": RATE_LIMIT_WINDOW
            }
        
        # Count current calls
        current_calls = sum(
            1 for ts, _ in self._calls[connection_id]
            if ts > window_start
        )
        
        return {
            "calls_in_window": current_calls,
            "remaining_quota": max(0, RATE_LIMIT_MAX_CALLS - current_calls),
            "window_seconds": RATE_LIMIT_WINDOW
        }