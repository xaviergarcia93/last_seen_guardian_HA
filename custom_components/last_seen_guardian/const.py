"""Constants for Last Seen Guardian."""

DOMAIN = "last_seen_guardian"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_store"

# Configuration defaults
DEFAULT_CHECK_INTERVAL = 15  # minutes
DEFAULT_THRESHOLD_MULTIPLIER = 2.5

# Panel configuration
PANEL_URL_PATH = "last_seen_guardian"
PANEL_TITLE = "Last Seen Guardian"
PANEL_ICON = "mdi:shield-check"

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

# Mode configurations
MODE_CONFIGS = {
    "normal": {
        "threshold_multiplier": 2.5,
        "alert_enabled": True,
        "ignore_variable": False,
        "silent_alerts": False,
    },
    "vacation": {
        "threshold_multiplier": 4.0,
        "alert_enabled": False,
        "ignore_variable": True,
        "silent_alerts": False,
    },
    "night": {
        "threshold_multiplier": 2.0,
        "alert_enabled": True,
        "ignore_variable": False,
        "silent_alerts": True,
    },
}

# Platforms
PLATFORMS = ["sensor"]

# Version
VERSION = "0.5.2"