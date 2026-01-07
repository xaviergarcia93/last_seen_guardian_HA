"""LSG: Core evaluator - Data pattern learning & state evaluation."""
import logging
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, HEALTH_OK, HEALTH_LATE, HEALTH_STALE, HEALTH_UNKNOWN

_LOGGER = logging.getLogger(__name__)

class LSGEvaluator:
    """Evaluator with pattern learning and health monitoring."""
    
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._learning_state: Dict[str, Dict] = {}
        self._unsubscribe = None
        self._storage = None
        
    async def async_setup(self) -> None:
        """Initialize evaluator and load learning state."""
        self._storage = self._hass.data[DOMAIN].get("storage")
        if self._storage:
            stored = await self._storage.async_get("learning_state")
            if stored:
                self._learning_state = stored
                _LOGGER.info("Loaded learning state for %d entities", len(stored))
        
        # Subscribe to state changes
        @callback
        def state_changed_listener(event):
            """Handle state changes for tracked entities."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            
            if new_state and entity_id:
                self._hass.async_create_task(
                    self._async_update_entity_learning(entity_id, new_state)
                )
        
        self._unsubscribe = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            state_changed_listener
        )
        _LOGGER.info("Evaluator initialized")
    
    async def _async_update_entity_learning(
        self, entity_id: str, state: State
    ) -> None:
        """Update learning state when entity changes."""
        now = time.time()
        
        # Get or create learning state
        if entity_id not in self._learning_state:
            self._learning_state[entity_id] = {
                "last_event": now,
                "interval_ewma": None,
                "interval_variance": 0.0,
                "event_count": 0,
                "threshold": None,
                "last_health": HEALTH_UNKNOWN,
                "history": []
            }
        
        entity_state = self._learning_state[entity_id]
        
        # Calculate interval
        if entity_state["last_event"] is not None:
            interval = now - entity_state["last_event"]
            
            # Update EWMA
            old_ewma = entity_state.get("interval_ewma")
            alpha = 0.3  # Smoothing factor
            if old_ewma is None:
                entity_state["interval_ewma"] = interval
            else:
                entity_state["interval_ewma"] = (
                    (1 - alpha) * old_ewma + alpha * interval
                )
            
            # Update threshold (2.5x mean)
            entity_state["threshold"] = entity_state["interval_ewma"] * 2.5
            
            # Store in history (keep last 100)
            entity_state["history"].append({
                "timestamp": now,
                "interval": interval,
                "state": state.state
            })
            if len(entity_state["history"]) > 100:
                entity_state["history"] = entity_state["history"][-100:]
        
        entity_state["last_event"] = now
        entity_state["event_count"] += 1
        
        # Evaluate health
        health = self._evaluate_health(entity_id)
        entity_state["last_health"] = health
        
        # Persist every 10 events or when health changes
        if entity_state["event_count"] % 10 == 0:
            await self._async_save_learning_state()
    
    def _evaluate_health(self, entity_id: str) -> str:
        """Evaluate health status based on learning."""
        state = self._learning_state.get(entity_id)
        
        if not state or state.get("event_count", 0) < 2:
            return HEALTH_UNKNOWN
        
        now = time.time()
        last_event = state.get("last_event", now)
        interval = now - last_event
        threshold = state.get("threshold")
        
        if threshold is None or threshold <= 0:
            return HEALTH_UNKNOWN
        
        # Health classification
        if interval < threshold * 1.1:
            return HEALTH_OK
        elif interval < threshold * 2.0:
            return HEALTH_LATE
        else:
            return HEALTH_STALE
    
    async def async_run_evaluation(self) -> Dict[str, str]:
        """Run full evaluation of all tracked entities."""
        results = {}
        now = time.time()
        
        for entity_id, state in self._learning_state.items():
            health = self._evaluate_health(entity_id)
            results[entity_id] = health
            
            # Update last_health
            state["last_health"] = health
        
        _LOGGER.debug("Evaluation complete: %d entities", len(results))
        return results
    
    async def _async_save_learning_state(self) -> None:
        """Persist learning state to storage."""
        if self._storage:
            try:
                await self._storage.async_set("learning_state", self._learning_state)
            except Exception as e:
                _LOGGER.exception("Error saving learning state: %s", e)
    
    def get_entity_health(self, entity_id: str) -> str:
        """Get current health status for entity."""
        return self._evaluate_health(entity_id)
    
    def get_entity_stats(self, entity_id: str) -> Optional[Dict]:
        """Get learning statistics for entity."""
        return self._learning_state.get(entity_id)
    
    def get_all_health_states(self) -> Dict[str, str]:
        """Get health states for all entities."""
        return {
            eid: self._evaluate_health(eid)
            for eid in self._learning_state.keys()
        }
    
    async def async_unload(self) -> None:
        """Cleanup and save state."""
        await self._async_save_learning_state()
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None