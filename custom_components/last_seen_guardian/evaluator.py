"""LSG: Core evaluator - Data pattern learning & state evaluation."""
import time
from homeassistant.core import HomeAssistant
from .const import DOMAIN, HEALTH_OK, HEALTH_LATE, HEALTH_STALE, HEALTH_UNKNOWN

def ewma(prior, value, alpha=0.3):
    """Exponential Weighted Moving Average update."""
    if prior is None:
        return value
    return (1 - alpha) * prior + alpha * value

async def async_setup_evaluator(hass: HomeAssistant, entry):
    """Prepare any runtime state needed."""
    hass.data[DOMAIN].setdefault("learning_state", {})

def update_learning_state(hass: HomeAssistant, entity_id: str, last_event_ts: float) -> None:
    """Update EWMA and intervals, learn patterns."""
    # Access global learning state for entity
    state = hass.data[DOMAIN]["learning_state"].setdefault(entity_id, {
        "last_event": None,
        "interval_ewma": None,
        "interval_stddev": None,
        "event_count": 0,
        "threshold": None,
    })
    now = time.time()
    if state["last_event"] is not None:
        interval = now - state["last_event"]
        old_ewma = state.get("interval_ewma")
        ewma_val = ewma(old_ewma, interval) if old_ewma else interval
        state["interval_ewma"] = ewma_val
        # No stddev for simplicity; can be extended
        state["threshold"] = ewma_val * 2.5 # e.g.: 2.5x mean as threshold
    state["last_event"] = last_event_ts
    state["event_count"] += 1

def evaluate_entity_health(hass: HomeAssistant, entity_id: str, timestamp: float = None):
    """Return health state of entity based on learning state."""
    state = hass.data[DOMAIN]["learning_state"].get(entity_id, {})
    if state.get("event_count", 0) < 2:
        return HEALTH_UNKNOWN
    now = timestamp or time.time()
    interval = now - (state.get("last_event") or now)
    ewma_val = state.get("interval_ewma")
    threshold = state.get("threshold", ewma_val * 2.5 if ewma_val else None)
    if threshold is None:
        return HEALTH_UNKNOWN
    if interval < threshold * 1.1:
        return HEALTH_OK
    elif interval < threshold * 2.0:
        return HEALTH_LATE
    else:
        return HEALTH_STALE