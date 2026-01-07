"""Constants for Last Seen Guardian."""

DOMAIN = "last_seen_guardian"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_store"

# Configuration defaults - SAFE STARTUP VALUES
DEFAULT_CHECK_INTERVAL = 60  # minutes
DEFAULT_THRESHOLD_MULTIPLIER = 5.0  # INCREASED for fewer false positives

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

# Mode configurations - SAFE DEFAULTS
MODE_CONFIGS = {
    "normal": {
        "threshold_multiplier": 5.0,  # INCREASED FROM 2.5
        "alert_enabled": False,  # DISABLED BY DEFAULT
        "ignore_variable": False,
        "silent_alerts": False,
    },
    "vacation": {
        "threshold_multiplier": 8.0,  # INCREASED FROM 4.0
        "alert_enabled": False,
        "ignore_variable": True,
        "silent_alerts": False,
    },
    "night": {
        "threshold_multiplier": 4.0,  # INCREASED FROM 2.0
        "alert_enabled": False,  # DISABLED BY DEFAULT
        "ignore_variable": False,
        "silent_alerts": True,
    },
}

# Platforms
PLATFORMS = ["sensor"]

# Rate limiting (v0.6)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window

# Data validation (v0.6) - SAFE LIMITS
MAX_LEARNING_STATE_SIZE = 1000  # REDUCED FROM 10000
MAX_HISTORY_PER_ENTITY = 50  # REDUCED FROM 100
MAX_HISTORY_AGE_DAYS = 30  # REDUCED FROM 90

# Startup protection - CRITICAL
STARTUP_GRACE_PERIOD_SECONDS = 600  # 10 minutes
MAX_ENTITIES_PER_EVALUATION = 500  # Process max 500 per cycle
MIN_EVENTS_FOR_NOTIFICATION = 20  # INCREASED FROM 10

# Notifications (v0.6) - SAFE DELAYS
DEFAULT_NOTIFY_SERVICE = "notify.notify"
NOTIFICATION_THROTTLE_SECONDS = 7200  # 2 hours - INCREASED
NOTIFICATION_COOLDOWN_SECONDS = 300  # 5 minutes - INCREASED

# Battery monitoring (v0.7)
BATTERY_LOW_THRESHOLD = 15  # percent - REDUCED to alert only critical
BATTERY_CRITICAL_THRESHOLD = 5  # percent
BATTERY_DOMAINS = ["sensor"]

# Signal quality (v0.7)
LQI_DOMAINS = ["sensor", "binary_sensor"]
LQI_LOW_THRESHOLD = 50  # REDUCED - only alert very poor signal
RSSI_LOW_THRESHOLD = -90  # REDUCED - only alert very poor signal

# History & Analytics (v0.8)
HISTORY_RETENTION_DAYS = 30
HISTORY_COMPRESSION_ENABLED = True
TREND_ANALYSIS_MIN_EVENTS = 20

# Device info
DEVICE_MANUFACTURER = "Last Seen Guardian"
DEVICE_MODEL = "LSG Monitor"
DEVICE_SW_VERSION = "0.8.0"

# Version
VERSION = "0.8.0"