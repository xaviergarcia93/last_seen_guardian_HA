"""
Data Validator - v0.6
Validates and cleans learning state to prevent unbounded growth.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, Tuple

from .const import (
    MAX_LEARNING_STATE_SIZE,
    MAX_HISTORY_PER_ENTITY,
    MAX_HISTORY_AGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class DataValidator:
    """Validates and cleans learning state data."""
    
    @staticmethod
    def validate_learning_state(learning_state: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate and clean learning state.
        
        Returns:
            Tuple of (is_valid, message, cleaned_state)
        """
        if not isinstance(learning_state, dict):
            return False, "learning_state must be a dictionary", {}
        
        cleaned_state = {}
        issues = []
        
        # Check size limit
        if len(learning_state) > MAX_LEARNING_STATE_SIZE:
            _LOGGER.warning(
                "Learning state size %d exceeds limit %d, pruning oldest entries",
                len(learning_state),
                MAX_LEARNING_STATE_SIZE
            )
            
            # Sort by last_event and keep most recent
            sorted_entities = sorted(
                learning_state.items(),
                key=lambda x: x[1].get("last_event", 0),
                reverse=True
            )
            
            learning_state = dict(sorted_entities[:MAX_LEARNING_STATE_SIZE])
            issues.append(f"Pruned to {MAX_LEARNING_STATE_SIZE} entities")
        
        # Validate each entity
        now = time.time()
        max_age_seconds = MAX_HISTORY_AGE_DAYS * 86400
        
        for entity_id, state in learning_state.items():
            if not isinstance(state, dict):
                _LOGGER.warning("Invalid state for %s, skipping", entity_id)
                continue
            
            # Validate required fields
            required_fields = ["last_event", "event_count"]
            if not all(field in state for field in required_fields):
                _LOGGER.warning(
                    "Entity %s missing required fields, skipping",
                    entity_id
                )
                continue
            
            # Clean history
            if "history" in state and isinstance(state["history"], list):
                original_count = len(state["history"])
                
                # Remove old events
                state["history"] = [
                    event for event in state["history"]
                    if isinstance(event, dict) 
                    and event.get("timestamp", 0) > (now - max_age_seconds)
                ]
                
                # Limit history size
                if len(state["history"]) > MAX_HISTORY_PER_ENTITY:
                    state["history"] = state["history"][-MAX_HISTORY_PER_ENTITY:]
                
                cleaned_count = len(state["history"])
                
                if original_count != cleaned_count:
                    _LOGGER.debug(
                        "Cleaned history for %s: %d -> %d events",
                        entity_id,
                        original_count,
                        cleaned_count
                    )
            
            # Validate numeric fields
            for field in ["last_event", "interval_ewma", "threshold", "event_count"]:
                if field in state:
                    try:
                        state[field] = float(state[field]) if field != "event_count" else int(state[field])
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Invalid %s for %s, setting to None",
                            field,
                            entity_id
                        )
                        state[field] = None if field != "event_count" else 0
            
            cleaned_state[entity_id] = state
        
        message = "Learning state validated"
        if issues:
            message += f": {', '.join(issues)}"
        
        return True, message, cleaned_state
    
    @staticmethod
    def get_data_stats(learning_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about learning state."""
        if not learning_state:
            return {
                "entity_count": 0,
                "total_events": 0,
                "total_history_items": 0,
                "oldest_event": None,
                "newest_event": None,
            }
        
        total_events = sum(
            state.get("event_count", 0) 
            for state in learning_state.values()
        )
        
        total_history = sum(
            len(state.get("history", [])) 
            for state in learning_state.values()
        )
        
        all_timestamps = [
            state.get("last_event")
            for state in learning_state.values()
            if state.get("last_event")
        ]
        
        return {
            "entity_count": len(learning_state),
            "total_events": total_events,
            "total_history_items": total_history,
            "oldest_event": min(all_timestamps) if all_timestamps else None,
            "newest_event": max(all_timestamps) if all_timestamps else None,
        }