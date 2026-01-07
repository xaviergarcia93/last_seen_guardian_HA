// www/last_seen_guardian/components/ModesTab.js

/**
 * Modes Tab - Operation mode selector with configuration per mode
 * 
 * Modes:
 * - normal: Standard monitoring
 * - vacation: Relaxed thresholds, ignore variable sensors
 * - night: Prioritize critical sensors, silent alerts
 * 
 * @param {Object} config - Current configuration object
 * @param {Object} hass - Home Assistant instance
 * @param {Function} onModeChange - Callback when mode changes
 * @returns {HTMLElement} Container element
 */
export default function ModesTab(config = {}, hass = null, onModeChange = null) {
    const container = document.createElement("div");
    container.className = "lsg-modes-tab";
    
    const modes = config?.modes || {};
    const currentMode = modes.current || "normal";
    const availableModes = [
        {
            id: "normal",
            name: "Normal",
            icon: "mdi:home",
            description: "Standard monitoring with regular thresholds",
            settings: {
                threshold_multiplier: 2.5,
                alert_enabled: true,
                ignore_variable: false
            }
        },
        {
            id: "vacation",
            name: "Vacation",
            icon: "mdi:beach",
            description: "Relaxed monitoring, ignore variable sensors (motion, doors)",
            settings: {
                threshold_multiplier: 4.0,
                alert_enabled: false,
                ignore_variable: true
            }
        },
        {
            id: "night",
            name: "Night",
            icon: "mdi:weather-night",
            description: "Prioritize critical sensors, silent alerts",
            settings: {
                threshold_multiplier: 2.0,
                alert_enabled: true,
                ignore_variable: false,
                silent_alerts: true
            }
        }
    ];
    
    // Header
    const header = document.createElement("div");
    header.className = "lsg-modes-header";
    header.innerHTML = `
        <h2>Operation Modes</h2>
        <p class="lsg-subtitle">Adjust monitoring behavior based on your activity</p>
    `;
    container.appendChild(header);
    
    // Current mode banner
    const currentModeData = availableModes.find(m => m.id === currentMode);
    const banner = document.createElement("div");
    banner.className = "lsg-current-mode-banner";
    banner.innerHTML = `
        <ha-icon icon="${currentModeData?.icon || 'mdi:help-circle'}"></ha-icon>
        <div>
            <strong>Current Mode:</strong> ${currentModeData?.name || 'Unknown'}
            <p>${currentModeData?.description || ''}</p>
        </div>
    `;
    container.appendChild(banner);
    
    // Mode cards
    const modesGrid = document.createElement("div");
    modesGrid.className = "lsg-modes-grid";
    
    availableModes.forEach(mode => {
        const isActive = mode.id === currentMode;
        
        const card = document.createElement("div");
        card.className = `lsg-mode-card ${isActive ? 'lsg-mode-active' : ''}`;
        card.dataset.mode = mode.id;
        
        card.innerHTML = `
            <div class="lsg-mode-icon">
                <ha-icon icon="${mode.icon}"></ha-icon>
            </div>
            <div class="lsg-mode-content">
                <h3>${mode.name}</h3>
                <p>${mode.description}</p>
                <div class="lsg-mode-settings">
                    <div class="lsg-mode-setting">
                        <ha-icon icon="mdi:tune"></ha-icon>
                        <span>Threshold: ${mode.settings.threshold_multiplier}x</span>
                    </div>
                    <div class="lsg-mode-setting">
                        <ha-icon icon="mdi:${mode.settings.alert_enabled ? 'bell' : 'bell-off'}"></ha-icon>
                        <span>Alerts: ${mode.settings.alert_enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    ${mode.settings.ignore_variable ? `
                        <div class="lsg-mode-setting">
                            <ha-icon icon="mdi:eye-off"></ha-icon>
                            <span>Ignore variable sensors</span>
                        </div>
                    ` : ''}
                    ${mode.settings.silent_alerts ? `
                        <div class="lsg-mode-setting">
                            <ha-icon icon="mdi:bell-sleep"></ha-icon>
                            <span>Silent alerts</span>
                        </div>
                    ` : ''}
                </div>
            </div>
            ${isActive ? `
                <div class="lsg-mode-active-badge">
                    <ha-icon icon="mdi:check-circle"></ha-icon>
                    <span>Active</span>
                </div>
            ` : `
                <button class="lsg-btn-activate" data-mode="${mode.id}">
                    Activate
                </button>
            `}
        `;
        
        modesGrid.appendChild(card);
    });
    
    container.appendChild(modesGrid);
    
    // Advanced settings section
    const advancedSection = document.createElement("div");
    advancedSection.className = "lsg-advanced-settings";
    advancedSection.innerHTML = `
        <details>
            <summary>
                <ha-icon icon="mdi:cog"></ha-icon>
                <span>Advanced Mode Settings</span>
            </summary>
            <div class="lsg-advanced-content">
                <p class="lsg-hint">
                    <ha-icon icon="mdi:information"></ha-icon>
                    Mode-specific settings will be configurable here in future versions.
                    Currently, modes use preset configurations.
                </p>
                <div class="lsg-form-group">
                    <label>
                        <input type="checkbox" disabled>
                        Custom threshold per mode
                    </label>
                    <label>
                        <input type="checkbox" disabled>
                        Per-area mode overrides
                    </label>
                    <label>
                        <input type="checkbox" disabled>
                        Schedule automatic mode changes
                    </label>
                </div>
            </div>
        </details>
    `;
    container.appendChild(advancedSection);
    
    // Attach event listeners
    if (onModeChange && typeof onModeChange === 'function') {
        container.querySelectorAll('.lsg-btn-activate').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const modeId = e.currentTarget.dataset.mode;
                
                // Disable button during change
                e.currentTarget.disabled = true;
                e.currentTarget.textContent = 'Activating...';
                
                try {
                    await onModeChange(modeId);
                    // Success feedback is handled by parent (panel.js)
                } catch (error) {
                    console.error('LSG: Error changing mode:', error);
                    e.currentTarget.disabled = false;
                    e.currentTarget.textContent = 'Activate';
                }
            });
        });
    }
    
    return container;
}