# 🛡️ Last Seen Guardian (LSG)

**Advanced entity health monitoring for Home Assistant with automatic pattern learning and zero false alarms.**

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-0.5.2-blue.svg)](https://github.com/yourusername/ha_lsg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 **Overview**

Last Seen Guardian (LSG) is a custom Home Assistant integration that intelligently monitors the health and activity of all your devices and entities. It automatically learns behavioral patterns, adapts to both fixed and variable sensors, and provides centralized management through a modern, intuitive UI.

### **Key Features**

✅ **Automatic Pattern Learning** - Uses EWMA (Exponential Weighted Moving Average) to learn normal reporting intervals  
✅ **Zero False Alarms** - Intelligent thresholds prevent unnecessary notifications  
✅ **Protocol Independent** - Works with Zigbee, WiFi, BLE, Z-Wave, and more  
✅ **Operation Modes** - Normal, Vacation, and Night modes with different behaviors  
✅ **Real-time Diagnostics** - Automatic detection of battery, network, and pattern issues  
✅ **Health States** - Clear classification: OK, Late, Stale, Unknown  
✅ **Native Sensors** - Expose health status to automations and dashboards  
✅ **Modern UI** - Beautiful panel with tabs, filters, and detailed diagnostics  

---

## 🚀 **Installation**

### **Option 1: HACS (Recommended)**

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click "..." → "Custom repositories"
4. Add repository: `https://github.com/yourusername/ha_lsg`
5. Category: Integration
6. Click "Install"
7. Restart Home Assistant

### **Option 2: Manual Installation**

1. Download the latest release from [Releases](https://github.com/yourusername/ha_lsg/releases)
2. Extract to `config/custom_components/last_seen_guardian/`
3. Restart Home Assistant

---

## ⚙️ **Configuration**

### **Setup via UI**

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Last Seen Guardian"**
4. Follow the setup wizard

### **Default Settings**

| Setting | Default | Description |
|---------|---------|-------------|
| Check Interval | 15 minutes | How often to evaluate entity health |
| Threshold Multiplier | 2.5x | Alert when interval exceeds EWMA × multiplier |
| Mode | Normal | Current operation mode |

---

## 📊 **How It Works**

### **Learning Phase**

LSG observes entity state changes and calculates:

- **Interval EWMA**: Average time between events using exponential smoothing
- **Threshold**: Dynamic alert threshold (EWMA × multiplier)
- **Event Count**: Number of observations (minimum 2 for classification)

### **Health Classification**
OK → Last event within threshold × 1.1
LATE → Last event within threshold × 2.0
STALE → Last event exceeds threshold × 2.0
UNKNOWN → Insufficient data (< 2 events)

### **Example**

A motion sensor reports every **30 seconds** on average:

- **EWMA**: 30s
- **Threshold**: 75s (30s × 2.5)
- **OK**: Last event < 83s ago
- **LATE**: Last event 83s - 150s ago
- **STALE**: Last event > 150s ago

---

## 🎛️ **Operation Modes**

### **Normal Mode** 🏠
- Standard monitoring
- Threshold: 2.5x EWMA
- Alerts enabled
- All sensors monitored

### **Vacation Mode** 🏖️
- Relaxed monitoring
- Threshold: 4.0x EWMA
- Alerts disabled
- Ignores variable sensors (motion, doors)

### **Night Mode** 🌙
- Strict monitoring
- Threshold: 2.0x EWMA
- Silent alerts
- Prioritizes critical sensors

---

## 📈 **Built-in Sensors**

LSG creates the following sensor entities:

| Entity | Type | Description |
|--------|------|-------------|
| `binary_sensor.lsg_any_problem` | Binary Sensor | ON if any entity has problems |
| `sensor.lsg_failed_entities` | Sensor | Count of stale entities |
| `sensor.lsg_healthy_entities` | Sensor | Count of OK entities |
| `sensor.lsg_late_entities` | Sensor | Count of late entities |
| `sensor.lsg_stale_entities` | Sensor | Count of stale entities |
| `sensor.lsg_unknown_entities` | Sensor | Count of unknown entities |

### **Example Automation**
automation:
  - alias: "LSG: Alert on failed entities"
    trigger:
      - platform: state
        entity_id: binary_sensor.lsg_any_problem
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "LSG Alert"
          message: "{{ states('sensor.lsg_failed_entities') }} entities are not responding"

🖥️ User Interface
Panel Overview
Access the LSG panel from the Home Assistant sidebar:


Sensors Tab
Entity health table with color-coded badges

Filterable by area, domain, health status

Click any entity for detailed diagnostics

Modes Tab
Switch between Normal, Vacation, Night modes

Visual mode cards with settings preview

One-click mode activation

General Tab
Configure check interval

Adjust threshold multiplier

Enable/disable notifications

Export learning data (coming soon)

Entity Detail Modal

Click any entity to see:

Health Status: Current health with diagnostic message

Metadata: Domain, platform, area, labels

Learning Statistics: EWMA, threshold, event count

Automatic Diagnostics: Battery, network, pattern issues

Activity Timeline: Last 10 events with timestamps

🔧 Advanced Configuration
Per-Mode Overrides (Coming in v0.6)

# custom_components/last_seen_guardian/config.yaml
modes:
  vacation:
    threshold_multiplier: 5.0
    ignore_domains:
      - binary_sensor
      - motion
Area-Specific Settings (Coming in v0.7)

areas:
  garage:
    threshold_multiplier: 3.0
    priority: low
  bedroom:
    threshold_multiplier: 2.0
    priority: critical

🛠️ Troubleshooting
Entities not appearing
Check that entities are not disabled in Home Assistant

Ensure entities report state changes (not just attributes)

Wait 5-10 minutes for initial learning

False "stale" alerts
Entity may have infrequent updates (daily battery sensors, etc.)

Increase threshold_multiplier in General settings

Switch to Vacation mode temporarily

High resource usage
Increase check_interval to 30-60 minutes

Disable entities you don't want monitored

Check logs for errors

Debug Logging
Enable debug logging in configuration.yaml:

logger:
  default: info
  logs:
    custom_components.last_seen_guardian: debug
📚 Roadmap
v0.6: Smart Alerts (In Progress)

Configurable notifications


Multi-channel notify support


Throttling and debouncing


Mode-aware alerts

v0.7: Technical Context

Battery level monitoring


LQI/RSSI tracking


Network diagnostics


Heuristic cause detection

v0.8: History & Analytics

Entity health history


Trend analysis


Export diagnostics (JSON)


Health map visualization

v1.0: Production Ready

Full test coverage


HACS official repository


Multi-language support


Mobile app integration

🤝 Contributing
Contributions are welcome! Please:


Fork the repository

Create a feature branch

Write tests for new features

Submit a pull request

Development Setup
# Clone repository
git clone https://github.com/yourusername/ha_lsg.git
cd ha_lsg

# Install dependencies
pip install -r requirements_dev.txt

# Run tests
pytest tests/

# Run linters
pylint custom_components/last_seen_guardian/
black custom_components/last_seen_guardian/
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.


💬 Support
Issues: GitHub Issues

Discussions: GitHub Discussions

Community: Home Assistant Forum

🙏 Acknowledgments
Home Assistant community for inspiration

EWMA algorithm from Wikipedia

UI design inspired by Alarmo and Mushroom cards

Made with ❤️ for the Home Assistant community