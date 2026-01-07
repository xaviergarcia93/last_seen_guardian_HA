"""Constants for Last Seen Guardian."""
DOMAIN = "last_seen_guardian"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_store"

# Health states
HEALTH_OK = "ok"
HEALTH_LATE = "late"
HEALTH_STALE = "stale"
HEALTH_UNKNOWN = "unknown"

# HA Areas & Tags
LSG_LABELS = ["zigbee", "wifi", "ble", "critical"]
LSG_TAGS = ["door", "humidity", "soil_moisture", "water_leak"]

# Operation Modes
LSG_MODES = ["normal", "vacation", "night"]

PLATFORMS = []