"""LSG: Core evaluator - Data pattern learning & state evaluation."""
import asyncio
import logging
import time
from typing import Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    DOMAIN,
    HEALTH_OK,
    HEALTH_LATE,
    HEALTH_STALE,
    HEALTH_UNKNOWN,
    MODE_CONFIGS,
    BATTERY_LOW_THRESHOLD,
    BATTERY_CRITICAL_THRESHOLD,
    LQI_LOW_THRESHOLD,
    RSSI_LOW_THRESHOLD,
)
from .data_validator import DataValidator

_LOGGER = logging.getLogger(__name__)

# Configuration for debounced persistence
SAVE_DEBOUNCE_SECONDS = 30
SAVE_MAX_WAIT_SECONDS = 300


class LSGEvaluator:
    """Evaluator with pattern learning, health monitoring, and technical context."""
    
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
                # Validate and clean loaded state
                is_valid, message, cleaned_state = DataValidator.validate_learning_state(stored)
                if is_valid:
                    self._learning_state = cleaned_state
                    _LOGGER.info("Loaded learning state for %d entities: %s", 
                                len(cleaned_state), message)
                else:
                    _LOGGER.warning("Invalid learning state: %s", message)
        
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
        
        _LOGGER.info("Evaluator initialized with debounced persistence and technical monitoring")
    
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
                "history": [],
                "technical_context": {}  # v0.7
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
            
            # MODE-AWARE: Get threshold multiplier from current mode
            threshold_multiplier = await self._get_current_threshold_multiplier()
            entity_state["threshold"] = entity_state["interval_ewma"] * threshold_multiplier
            
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
        
        # v0.7: Extract technical context (battery, LQI, RSSI)
        await self._extract_technical_context(entity_id, state, entity_state)
        
        # Evaluate health
        old_health = entity_state.get("last_health")
        new_health = self._evaluate_health(entity_id)
        entity_state["last_health"] = new_health
        
        # Track changed entity
        self._entities_changed.add(entity_id)
        
        # Trigger save with priority if health degraded
        if old_health != new_health and new_health in (HEALTH_STALE, HEALTH_LATE):
            _LOGGER.debug(
                "Entity %s health changed to %s, triggering priority save",
                entity_id,
                new_health
            )
            await self._async_schedule_save(priority=True)
        else:
            await self._async_schedule_save(priority=False)
    
    async def _get_current_threshold_multiplier(self) -> float:
        """Get threshold multiplier based on current mode (MODE-AWARE)."""
        try:
            config = await self._storage.async_get("config")
            current_mode = config.get("modes", {}).get("current", "normal")
            mode_config = MODE_CONFIGS.get(current_mode, MODE_CONFIGS["normal"])
            return mode_config["threshold_multiplier"]
        except Exception as e:
            _LOGGER.warning("Could not get mode config: %s, using default", e)
            return 2.5
    
    async def _extract_technical_context(
        self, entity_id: str, state: State, entity_state: Dict
    ) -> None:
        """
        Extract technical context from entity state (v0.7).
        
        Monitors:
        - Battery level
        - LQI (Zigbee Link Quality Indicator)
        - RSSI (WiFi/BLE Received Signal Strength Indicator)
        """
        context = entity_state.setdefault("technical_context", {})
        
        # Battery monitoring
        battery_level = None
        if hasattr(state, "attributes"):
            # Try common battery attributes
            battery_level = (
                state.attributes.get("battery_level") or
                state.attributes.get("battery") or
                state.attributes.get("battery_percent")
            )
            
            # If entity_id contains 'battery', use state value
            if battery_level is None and "battery" in entity_id.lower():
                try:
                    battery_level = float(state.state)
                except (ValueError, TypeError):
                    pass
        
        if battery_level is not None:
            try:
                battery_level = float(battery_level)
                context["battery_level"] = battery_level
                context["battery_timestamp"] = time.time()
                
                # Classify battery status
                if battery_level <= BATTERY_CRITICAL_THRESHOLD:
                    context["battery_status"] = "critical"
                elif battery_level <= BATTERY_LOW_THRESHOLD:
                    context["battery_status"] = "low"
                else:
                    context["battery_status"] = "ok"
            except (ValueError, TypeError):
                pass
        
        # LQI monitoring (Zigbee)
        if hasattr(state, "attributes"):
            lqi = state.attributes.get("lqi") or state.attributes.get("linkquality")
            if lqi is not None:
                try:
                    lqi = int(lqi)
                    context["lqi"] = lqi
                    context["lqi_timestamp"] = time.time()
                    context["lqi_status"] = "low" if lqi < LQI_LOW_THRESHOLD else "ok"
                except (ValueError, TypeError):
                    pass
        
        # RSSI monitoring (WiFi/BLE)
        if hasattr(state, "attributes"):
            rssi = state.attributes.get("rssi") or state.attributes.get("signal_strength")
            if rssi is not None:
                try:
                    rssi = int(rssi)
                    context["rssi"] = rssi
                    context["rssi_timestamp"] = time.time()
                    context["rssi_status"] = "low" if rssi < RSSI_LOW_THRESHOLD else "ok"
                except (ValueError, TypeError):
                    pass
    
    async def _async_schedule_save(self, priority: bool = False) -> None:
        """Schedule a debounced save operation."""
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
        """Periodic forced save (called every SAVE_MAX_WAIT_SECONDS)."""
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
        
        # Health classification (mode-aware threshold already applied)
        if interval < threshold * 1.1:
            return HEALTH_OK
        elif interval < threshold * 2.0:
            return HEALTH_LATE
        else:
            return HEALTH_STALE
    
    def get_diagnostic_context(self, entity_id: str) -> Dict[str, any]:
        """
        Get diagnostic context for an entity (v0.7).
        
        Returns heuristic analysis of potential issues.
        """
        state = self._learning_state.get(entity_id)
        if not state:
            return {"diagnosis": "no_data"}
        
        context = state.get("technical_context", {})
        health = self._evaluate_health(entity_id)
        
        diagnosis = {
            "health": health,
            "potential_causes": [],
            "recommendations": []
        }
        
        # Battery-related issues
        if "battery_level" in context:
            battery_status = context.get("battery_status")
            if battery_status == "critical":
                diagnosis["potential_causes"].append("battery_critical")
                diagnosis["recommendations"].append("Replace battery immediately")
            elif battery_status == "low":
                diagnosis["potential_causes"].append("battery_low")
                diagnosis["recommendations"].append("Battery needs replacement soon")
        
        # Network-related issues
        if "lqi" in context and context.get("lqi_status") == "low":
            diagnosis["potential_causes"].append("poor_zigbee_signal")
            diagnosis["recommendations"].append("Move device closer to coordinator or add router")
        
        if "rssi" in context and context.get("rssi_status") == "low":
            diagnosis["potential_causes"].append("poor_wifi_signal")
            diagnosis["recommendations"].append("Improve WiFi coverage in this area")
        
        # Pattern-based diagnosis
        if health == HEALTH_STALE and not diagnosis["potential_causes"]:
            # No technical context, likely device offline
            diagnosis["potential_causes"].append("device_offline")
            diagnosis["recommendations"].append("Check device power and network connectivity")
        
        return diagnosis
    
    async def async_run_evaluation(self) -> Dict[str, str]:
        """Run full evaluation of all tracked entities."""
        results = {}
        now = time.time()
        
        for entity_id, state in self._learning_state.items():
            health = self._evaluate_health(entity_id)
            results[entity_id] = health
            state["last_health"] = health
        
        _LOGGER.debug("Evaluation complete: %d entities", len(results))
        return results
    
    async def _async_save_learning_state(self) -> None:
        """Persist learning state to storage with validation."""
        if not self._storage:
            return
        
        try:
            # Validate before saving
            is_valid, message, cleaned_state = DataValidator.validate_learning_state(
                self._learning_state
            )
            
            if not is_valid:
                _LOGGER.error("Learning state validation failed: %s", message)
                return
            
            # Update in-memory state with cleaned version
            self._learning_state = cleaned_state
            
            # Save to storage
            await self._storage.async_set("learning_state", self._learning_state)
            
            # Update tracking
            self._last_save_time = time.time()
            changed_count = len(self._entities_changed)
            self._entities_changed.clear()
            self._pending_save = False
            
            _LOGGER.debug(
                "Learning state saved successfully (%d entities changed): %s",
                changed_count,
                message
            )
            
        except Exception as e:
            _LOGGER.exception("Error saving learning state: %s", e)
    
    def get_entity_health(self, entity_id: str) -> str:
        """Get current health status for entity."""
        return self._evaluate_health(entity_id)
    
    def get_entity_stats(self, entity_id: str) -> Optional[Dict]:
        """Get learning statistics for entity."""
        state = self._learning_state.get(entity_id)
        if not state:
            return None
        
        # Include diagnostic context (v0.7)
        stats = dict(state)
        stats["diagnosis"] = self.get_diagnostic_context(entity_id)
        
        return stats
    
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