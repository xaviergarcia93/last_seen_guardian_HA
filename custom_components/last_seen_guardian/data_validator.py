"""
Data Validator - v0.6
Validates and cleans learning state to prevent unbounded growth.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, Tuple, List

from .const import (
    MAX_LEARNING_STATE_SIZE,
    MAX_HISTORY_PER_ENTITY,
    MAX_HISTORY_AGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class DataValidator:
    """Validates and cleans learning state data."""
    
    @staticmethod
    def validate_learning_state(
        learning_state: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate and clean learning state.
        
        Args:
            learning_state: Dictionary of entity learning states
        
        Returns:
            Tuple of (is_valid, message, cleaned_state)
        """
        if not isinstance(learning_state, dict):
            return False, "learning_state must be a dictionary", {}
        
        cleaned_state = {}
        issues = []
        entities_removed = 0
        
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
            entities_removed = len(sorted_entities) - MAX_LEARNING_STATE_SIZE
            issues.append(f"Pruned {entities_removed} oldest entities")
        
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
            for field in ["last_event", "interval_ewma", "threshold", "interval_variance"]:
                if field in state:
                    try:
                        if field == "event_count":
                            state[field] = int(state[field])
                        else:
                            state[field] = float(state[field])
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Invalid %s for %s, setting to default",
                            field,
                            entity_id
                        )
                        if field == "event_count":
                            state[field] = 0
                        else:
                            state[field] = None
            
            # Validate event_count
            if "event_count" in state:
                try:
                    state["event_count"] = int(state["event_count"])
                    if state["event_count"] < 0:
                        state["event_count"] = 0
                except (ValueError, TypeError):
                    state["event_count"] = 0
            
            # Validate health state
            valid_health_states = ["ok", "late", "stale", "unknown"]
            if "last_health" in state:
                if state["last_health"] not in valid_health_states:
                    _LOGGER.warning(
                        "Invalid health state '%s' for %s, setting to 'unknown'",
                        state["last_health"],
                        entity_id
                    )
                    state["last_health"] = "unknown"
            
            # Ensure technical_context is a dict
            if "technical_context" in state:
                if not isinstance(state["technical_context"], dict):
                    _LOGGER.warning(
                        "Invalid technical_context for %s, resetting",
                        entity_id
                    )
                    state["technical_context"] = {}
            else:
                state["technical_context"] = {}
            
            cleaned_state[entity_id] = state
        
        message = "Learning state validated"
        if issues:
            message += f": {', '.join(issues)}"
        
        _LOGGER.info(
            "Validation complete: %d entities valid, %d removed",
            len(cleaned_state),
            entities_removed
        )
        
        return True, message, cleaned_state
    
    @staticmethod
    def get_data_stats(learning_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about learning state.
        
        Args:
            learning_state: Dictionary of entity learning states
        
        Returns:
            Dictionary with statistics
        """
        if not learning_state:
            return {
                "entity_count": 0,
                "total_events": 0,
                "total_history_items": 0,
                "oldest_event": None,
                "newest_event": None,
                "avg_events_per_entity": 0.0,
                "total_size_estimate_kb": 0.0,
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
        
        # Estimate size in KB (rough approximation)
        import sys
        try:
            size_bytes = sys.getsizeof(str(learning_state))
            size_kb = size_bytes / 1024
        except:
            size_kb = 0.0
        
        entity_count = len(learning_state)
        avg_events = total_events / entity_count if entity_count > 0 else 0.0
        
        return {
            "entity_count": entity_count,
            "total_events": total_events,
            "total_history_items": total_history,
            "oldest_event": min(all_timestamps) if all_timestamps else None,
            "newest_event": max(all_timestamps) if all_timestamps else None,
            "avg_events_per_entity": round(avg_events, 2),
            "total_size_estimate_kb": round(size_kb, 2),
        }
    
    @staticmethod
    def cleanup_orphaned_entities(
        learning_state: Dict[str, Any],
        valid_entity_ids: List[str]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Remove entities from learning state that no longer exist in HA.
        
        Args:
            learning_state: Current learning state
            valid_entity_ids: List of valid entity IDs from entity registry
        
        Returns:
            Tuple of (cleaned_state, removed_count)
        """
        valid_set = set(valid_entity_ids)
        cleaned_state = {}
        removed_count = 0
        
        for entity_id, state in learning_state.items():
            if entity_id in valid_set:
                cleaned_state[entity_id] = state
            else:
                removed_count += 1
                _LOGGER.debug("Removing orphaned entity: %s", entity_id)
        
        if removed_count > 0:
            _LOGGER.info("Removed %d orphaned entities", removed_count)
        
        return cleaned_state, removed_count
    
    @staticmethod
    def compress_history(
        learning_state: Dict[str, Any],
        keep_last_n: int = 50,
        compress_older_than_days: int = 7
    ) -> Dict[str, Any]:
        """
        Compress old history events to save space.
        
        Keeps recent events (last N) in full detail, and compresses
        older events into aggregated statistics.
        
        Args:
            learning_state: Current learning state
            keep_last_n: Number of recent events to keep in full
            compress_older_than_days: Compress events older than this
        
        Returns:
            Learning state with compressed history
        """
        now = time.time()
        cutoff_time = now - (compress_older_than_days * 86400)
        
        for entity_id, state in learning_state.items():
            if "history" not in state or not isinstance(state["history"], list):
                continue
            
            history = state["history"]
            
            # Separate recent and old events
            recent_events = []
            old_events = []
            
            for event in history:
                if not isinstance(event, dict):
                    continue
                    
                timestamp = event.get("timestamp", 0)
                if timestamp > cutoff_time:
                    recent_events.append(event)
                else:
                    old_events.append(event)
            
            # Keep last N recent events
            recent_events = recent_events[-keep_last_n:]
            
            # Compress old events into summary
            if old_events:
                old_intervals = [
                    e.get("interval", 0) 
                    for e in old_events 
                    if "interval" in e
                ]
                
                if old_intervals:
                    compressed_summary = {
                        "compressed": True,
                        "event_count": len(old_events),
                        "avg_interval": sum(old_intervals) / len(old_intervals),
                        "min_interval": min(old_intervals),
                        "max_interval": max(old_intervals),
                        "oldest_timestamp": min(e.get("timestamp", 0) for e in old_events),
                        "newest_timestamp": max(e.get("timestamp", 0) for e in old_events),
                    }
                    
                    # Add compressed summary as first item
                    state["history"] = [compressed_summary] + recent_events
                else:
                    state["history"] = recent_events
            else:
                state["history"] = recent_events
        
        return learning_state
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration dictionary
        
        Returns:
            Tuple of (is_valid, message, cleaned_config)
        """
        if not isinstance(config, dict):
            return False, "Config must be a dictionary", {}
        
        cleaned_config = {}
        issues = []
        
        # Validate global settings
        if "global" in config:
            if not isinstance(config["global"], dict):
                issues.append("Invalid 'global' section, resetting to defaults")
                cleaned_config["global"] = {
                    "check_every_minutes": 15,
                    "alert_threshold_multiplier": 2.5,
                    "enable_notifications": True,
                }
            else:
                global_config = config["global"].copy()
                
                # Validate check_every_minutes
                check_interval = global_config.get("check_every_minutes", 15)
                try:
                    check_interval = int(check_interval)
                    if check_interval < 5 or check_interval > 120:
                        issues.append("check_every_minutes out of range (5-120), using default")
                        check_interval = 15
                except (ValueError, TypeError):
                    issues.append("Invalid check_every_minutes, using default")
                    check_interval = 15
                
                global_config["check_every_minutes"] = check_interval
                
                # Validate threshold_multiplier
                threshold = global_config.get("alert_threshold_multiplier", 2.5)
                try:
                    threshold = float(threshold)
                    if threshold < 1.5 or threshold > 10.0:
                        issues.append("alert_threshold_multiplier out of range (1.5-10.0), using default")
                        threshold = 2.5
                except (ValueError, TypeError):
                    issues.append("Invalid alert_threshold_multiplier, using default")
                    threshold = 2.5
                
                global_config["alert_threshold_multiplier"] = threshold
                
                # Validate enable_notifications
                enable_notif = global_config.get("enable_notifications", True)
                if not isinstance(enable_notif, bool):
                    global_config["enable_notifications"] = True
                
                cleaned_config["global"] = global_config
        else:
            cleaned_config["global"] = {
                "check_every_minutes": 15,
                "alert_threshold_multiplier": 2.5,
                "enable_notifications": True,
            }
        
        # Validate modes
        if "modes" in config:
            if not isinstance(config["modes"], dict):
                issues.append("Invalid 'modes' section, resetting to defaults")
                cleaned_config["modes"] = {
                    "current": "normal",
                    "available": ["normal", "vacation", "night"]
                }
            else:
                modes_config = config["modes"].copy()
                
                # Validate current mode
                current = modes_config.get("current", "normal")
                valid_modes = ["normal", "vacation", "night"]
                if current not in valid_modes:
                    issues.append(f"Invalid current mode '{current}', using 'normal'")
                    current = "normal"
                
                modes_config["current"] = current
                modes_config["available"] = valid_modes
                
                cleaned_config["modes"] = modes_config
        else:
            cleaned_config["modes"] = {
                "current": "normal",
                "available": ["normal", "vacation", "night"]
            }
        
        message = "Config validated"
        if issues:
            message += f": {', '.join(issues)}"
        
        return True, message, cleaned_config