"""LSG: Core evaluator - Data pattern learning & state evaluation."""
import asyncio
import logging
import time
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, HEALTH_OK, HEALTH_LATE, HEALTH_STALE, HEALTH_UNKNOWN

_LOGGER = logging.getLogger(__name__)

# Configuration for debounced persistence
SAVE_DEBOUNCE_SECONDS = 30  # Wait 30s after last change before saving
SAVE_MAX_WAIT_SECONDS = 300  # Force save every 5 minutes regardless


class LSGEvaluator:
    """Evaluator with pattern learning and health monitoring."""
    
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._learning_state: Dict[str, Dict] = {}
        self._unsubscribe = None
        self._unsubscribe_timer = None
        self._storage = None
        
        # Debouncing state
        self._pending_save = False
        self._save_task: Optional[asyncio.Task] = None
        self._last_save_time = 0
        self._entities_changed: Set[str] = set()
        
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
        
        # Setup periodic forced save (every 5 minutes)
        self._unsubscribe_timer = async_track_time_interval(
            self._hass,
            self._async_periodic_save,
            timedelta(seconds=SAVE_MAX_WAIT_SECONDS)
        )
        
        _LOGGER.info("Evaluator initialized with debounced persistence")
    
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
        old_health = entity_state.get("last_health")
        new_health = self._evaluate_health(entity_id)
        entity_state["last_health"] = new_health
        
        # Track changed entity
        self._entities_changed.add(entity_id)
        
        # FIXED: Use debounced save instead of saving every 10 events (WARNING #1)
        # Only trigger immediate save if health changed to critical state
        if old_health != new_health and new_health in (HEALTH_STALE, HEALTH_LATE):
            _LOGGER.debug(
                "Entity %s health changed to %s, triggering priority save",
                entity_id,
                new_health
            )
            await self._async_schedule_save(priority=True)
        else:
            # Normal debounced save
            await self._async_schedule_save(priority=False)
    
    async def _async_schedule_save(self, priority: bool = False) -> None:
        """
        Schedule a debounced save operation.
        
        Args:
            priority: If True, reduces debounce delay for critical changes
        """
        # Cancel existing save task if any
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        
        # Determine delay
        if priority:
            delay = 5  # Priority saves happen in 5 seconds
        else:
            delay = SAVE_DEBOUNCE_SECONDS
        
        # Create new save task
        async def _delayed_save():
            try:
                await asyncio.sleep(delay)
                await self._async_save_learning_state()
            except asyncio.CancelledError:
                _LOGGER.debug("Save task cancelled (newer save scheduled)")
            except Exception as e:
                _LOGGER.exception("Error in delayed save: %s", e)
        
        self._save_task = self._hass.async_create_task(_delayed_save())
        self._pending_save = True
    
    async def _async_periodic_save(self, now=None) -> None:
        """
        Periodic forced save (called every SAVE_MAX_WAIT_SECONDS).
        
        This ensures data is persisted even if debounce keeps delaying.
        """
        elapsed = time.time() - self._last_save_time
        
        if self._entities_changed and elapsed >= SAVE_MAX_WAIT_SECONDS:
            _LOGGER.debug(
                "Forcing periodic save (%d entities changed in last %d seconds)",
                len(self._entities_changed),
                int(elapsed)
            )
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
        if not self._storage:
            return
        
        try:
            # Save to storage
            await self._storage.async_set("learning_state", self._learning_state)
            
            # Update tracking
            self._last_save_time = time.time()
            changed_count = len(self._entities_changed)
            self._entities_changed.clear()
            self._pending_save = False
            
            _LOGGER.debug(
                "Learning state saved successfully (%d entities changed)",
                changed_count
            )
            
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
        # Cancel any pending save task
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        
        # Force final save
        await self._async_save_learning_state()
        
        # Unsubscribe from events
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        
        if self._unsubscribe_timer:
            self._unsubscribe_timer()
            self._unsubscribe_timer = None
        
        _LOGGER.info("Evaluator unloaded, final state saved")