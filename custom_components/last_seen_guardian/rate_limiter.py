"""
Rate Limiter for WebSocket API - v0.6
Prevents spam and abuse of WebSocket commands.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Dict, Tuple, List, Optional
import logging

from homeassistant.core import HomeAssistant

from .const import RATE_LIMIT_WINDOW, RATE_LIMIT_MAX_CALLS

_LOGGER = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for WebSocket commands with sliding window algorithm."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize rate limiter."""
        self._hass = hass
        
        # Store: {connection_id: deque([(timestamp, command), ...])}
        # Using deque for efficient removal of old entries
        self._calls: Dict[str, deque] = defaultdict(lambda: deque(maxlen=RATE_LIMIT_MAX_CALLS * 2))
        
        # Track blocked connections
        self._blocked_until: Dict[str, float] = {}
        
        # Statistics
        self._total_calls = 0
        self._total_blocked = 0
        
    def check_rate_limit(
        self, 
        connection_id: str, 
        command: str
    ) -> Tuple[bool, int]:
        """
        Check if connection has exceeded rate limit.
        
        Uses sliding window algorithm for accurate rate limiting.
        
        Args:
            connection_id: Unique identifier for the connection
            command: Command being executed
        
        Returns:
            Tuple of (is_allowed, remaining_quota)
        """
        now = time.time()
        
        # Check if connection is temporarily blocked
        if connection_id in self._blocked_until:
            blocked_until = self._blocked_until[connection_id]
            if now < blocked_until:
                remaining_block = int(blocked_until - now)
                _LOGGER.warning(
                    "Connection %s is blocked for %d more seconds",
                    connection_id,
                    remaining_block
                )
                return False, 0
            else:
                # Unblock
                del self._blocked_until[connection_id]
        
        # Get call history for this connection
        call_history = self._calls[connection_id]
        
        # Remove calls outside the window (sliding window)
        window_start = now - RATE_LIMIT_WINDOW
        
        # Remove old calls from the left
        while call_history and call_history[0][0] < window_start:
            call_history.popleft()
        
        # Count calls in current window
        current_calls = len(call_history)
        
        # Check limit
        if current_calls >= RATE_LIMIT_MAX_CALLS:
            self._total_blocked += 1
            
            # Block connection for 60 seconds
            self._blocked_until[connection_id] = now + 60
            
            _LOGGER.warning(
                "Rate limit exceeded for connection %s: %d calls in %ds window (command: %s). Blocked for 60s.",
                connection_id,
                current_calls,
                RATE_LIMIT_WINDOW,
                command
            )
            
            return False, 0
        
        # Record this call
        call_history.append((now, command))
        self._total_calls += 1
        
        remaining = RATE_LIMIT_MAX_CALLS - current_calls - 1
        
        if remaining < 5:
            _LOGGER.debug(
                "Connection %s has %d calls remaining in window",
                connection_id,
                remaining
            )
        
        return True, remaining
    
    def reset_connection(self, connection_id: str) -> None:
        """
        Reset rate limit for a connection.
        
        Args:
            connection_id: Connection to reset
        """
        if connection_id in self._calls:
            del self._calls[connection_id]
        
        if connection_id in self._blocked_until:
            del self._blocked_until[connection_id]
        
        _LOGGER.debug("Rate limit reset for connection %s", connection_id)
    
    def get_stats(self, connection_id: Optional[str] = None) -> Dict[str, any]:
        """
        Get rate limit stats for connection or global stats.
        
        Args:
            connection_id: Optional connection ID. If None, returns global stats.
        
        Returns:
            Dictionary with statistics
        """
        if connection_id:
            # Stats for specific connection
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW
            
            if connection_id not in self._calls:
                return {
                    "connection_id": connection_id,
                    "calls_in_window": 0,
                    "remaining_quota": RATE_LIMIT_MAX_CALLS,
                    "window_seconds": RATE_LIMIT_WINDOW,
                    "is_blocked": False,
                }
            
            # Count current calls
            call_history = self._calls[connection_id]
            current_calls = sum(1 for ts, _ in call_history if ts > window_start)
            
            # Check if blocked
            is_blocked = False
            blocked_remaining = 0
            if connection_id in self._blocked_until:
                blocked_until = self._blocked_until[connection_id]
                if now < blocked_until:
                    is_blocked = True
                    blocked_remaining = int(blocked_until - now)
            
            return {
                "connection_id": connection_id,
                "calls_in_window": current_calls,
                "remaining_quota": max(0, RATE_LIMIT_MAX_CALLS - current_calls),
                "window_seconds": RATE_LIMIT_WINDOW,
                "is_blocked": is_blocked,
                "blocked_remaining_seconds": blocked_remaining,
            }
        else:
            # Global stats
            return {
                "total_connections": len(self._calls),
                "total_calls": self._total_calls,
                "total_blocked": self._total_blocked,
                "currently_blocked": len(self._blocked_until),
                "rate_limit_window": RATE_LIMIT_WINDOW,
                "rate_limit_max_calls": RATE_LIMIT_MAX_CALLS,
            }
    
    def get_all_connections(self) -> List[Dict[str, any]]:
        """
        Get stats for all active connections.
        
        Returns:
            List of connection stats dictionaries
        """
        connections = []
        
        for connection_id in self._calls.keys():
            connections.append(self.get_stats(connection_id))
        
        return connections
    
    def cleanup_stale_connections(self, max_age_seconds: int = 3600) -> int:
        """
        Remove connections with no recent activity.
        
        Args:
            max_age_seconds: Remove connections inactive for this long
        
        Returns:
            Number of connections cleaned up
        """
        now = time.time()
        cutoff = now - max_age_seconds
        
        stale_connections = []
        
        for connection_id, call_history in self._calls.items():
            if not call_history:
                stale_connections.append(connection_id)
            else:
                # Check last call time
                last_call_time = call_history[-1][0]
                if last_call_time < cutoff:
                    stale_connections.append(connection_id)
        
        # Remove stale connections
        for connection_id in stale_connections:
            del self._calls[connection_id]
            if connection_id in self._blocked_until:
                del self._blocked_until[connection_id]
        
        if stale_connections:
            _LOGGER.info(
                "Cleaned up %d stale connections (inactive > %ds)",
                len(stale_connections),
                max_age_seconds
            )
        
        return len(stale_connections)
    
    def get_command_stats(self, connection_id: str) -> Dict[str, int]:
        """
        Get breakdown of commands executed by connection.
        
        Args:
            connection_id: Connection to analyze
        
        Returns:
            Dictionary mapping command names to counts
        """
        if connection_id not in self._calls:
            return {}
        
        command_counts = defaultdict(int)
        
        for _, command in self._calls[connection_id]:
            command_counts[command] += 1
        
        return dict(command_counts)