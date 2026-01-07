"""
Health Cache Manager - Performance Optimization
Caches health state calculations to reduce CPU usage.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Tuple, Optional
from collections import OrderedDict

_LOGGER = logging.getLogger(__name__)


class HealthCache:
    """LRU cache for health state calculations."""
    
    def __init__(self, ttl: int = 60, max_size: int = 1000):
        """
        Initialize health cache.
        
        Args:
            ttl: Time to live for cache entries in seconds
            max_size: Maximum number of entries in cache
        """
        self._cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._ttl = ttl
        self._max_size = max_size
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, entity_id: str) -> Optional[str]:
        """
        Get cached health state for entity.
        
        Args:
            entity_id: Entity to lookup
        
        Returns:
            Cached health state or None if not found/expired
        """
        if entity_id not in self._cache:
            self._misses += 1
            return None
        
        health, timestamp = self._cache[entity_id]
        
        # Check if expired
        if time.time() - timestamp > self._ttl:
            del self._cache[entity_id]
            self._misses += 1
            return None
        
        # Move to end (LRU)
        self._cache.move_to_end(entity_id)
        self._hits += 1
        
        return health
    
    def set(self, entity_id: str, health: str) -> None:
        """
        Cache health state for entity.
        
        Args:
            entity_id: Entity ID
            health: Health state to cache
        """
        now = time.time()
        
        # If already exists, update and move to end
        if entity_id in self._cache:
            self._cache[entity_id] = (health, now)
            self._cache.move_to_end(entity_id)
            return
        
        # Check size limit
        if len(self._cache) >= self._max_size:
            # Remove oldest entry (LRU)
            oldest = next(iter(self._cache))
            del self._cache[oldest]
            self._evictions += 1
        
        # Add new entry
        self._cache[entity_id] = (health, now)
    
    def invalidate(self, entity_id: str) -> None:
        """
        Invalidate cache entry for entity.
        
        Args:
            entity_id: Entity to invalidate
        """
        if entity_id in self._cache:
            del self._cache[entity_id]
    
    def invalidate_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        _LOGGER.debug("Health cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired = []
        
        for entity_id, (health, timestamp) in self._cache.items():
            if now - timestamp > self._ttl:
                expired.append(entity_id)
        
        for entity_id in expired:
            del self._cache[entity_id]
        
        if expired:
            _LOGGER.debug("Removed %d expired cache entries", len(expired))
        
        return len(expired)
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._evictions,
        }