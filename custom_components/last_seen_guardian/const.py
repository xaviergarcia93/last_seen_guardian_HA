"""Constants for Last Seen Guardian."""

DOMAIN = "last_seen_guardian"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_store"

# Configuration defaults
DEFAULT_CHECK_INTERVAL = 60  # minutes
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

# Rate limiting (v0.6)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window

# Data validation (v0.6)
MAX_LEARNING_STATE_SIZE = 10000  # max entities to track
MAX_HISTORY_PER_ENTITY = 100  # max events per entity
MAX_HISTORY_AGE_DAYS = 90  # max age of history events

# Notifications (v0.6)
DEFAULT_NOTIFY_SERVICE = "notify.notify"
NOTIFICATION_THROTTLE_SECONDS = 3600  # 5 minutes between same alert
NOTIFICATION_COOLDOWN_SECONDS = 60  # 1 minute between different alerts

# Battery monitoring (v0.7)
BATTERY_LOW_THRESHOLD = 20  # percent
BATTERY_CRITICAL_THRESHOLD = 10  # percent
BATTERY_DOMAINS = ["sensor"]  # domains that may have battery attribute

# Signal quality (v0.7)
LQI_DOMAINS = ["sensor", "binary_sensor"]  # domains that may have lqi
LQI_LOW_THRESHOLD = 100  # Zigbee LQI threshold
RSSI_LOW_THRESHOLD = -80  # WiFi/BLE RSSI threshold (dBm)

# History & Analytics (v0.8)
HISTORY_RETENTION_DAYS = 30  # days to keep detailed history
HISTORY_COMPRESSION_ENABLED = True  # compress old history data
TREND_ANALYSIS_MIN_EVENTS = 20  # minimum events for trend analysis

# Device info
DEVICE_MANUFACTURER = "Last Seen Guardian"
DEVICE_MODEL = "LSG Monitor"
DEVICE_SW_VERSION = "0.8.0"

# Version
VERSION = "0.8.0"