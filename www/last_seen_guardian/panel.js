// www/last_seen_guardian/panel.js
import './assets/lsg.css';
import SensorsTab from './components/SensorsTab.js';
import ModesTab from './components/ModesTab.js';
import GeneralTab from './components/GeneralTab.js';
import DeviceModal from './components/DeviceModal.js';

const TABS = [
    {id: "sensors", name: "Sensors", icon: "mdi:radar"},
    {id: "modes", name: "Modes", icon: "mdi:tune"},
    {id: "general", name: "General", icon: "mdi:cog"},
];

// FIXED: Configurable refresh interval (WARNING #2)
const AUTO_REFRESH_INTERVAL_MS = 120000; // 2 minutes (was 30 seconds)
const ENABLE_AUTO_REFRESH = true; // Can be disabled via config

class LastSeenGuardianPanel extends HTMLElement {
    constructor() {
        super();
        this.activeTab = "sensors";
        this.entities = [];
        this.config = {};
        this.hass = null;
        this._subscriptionId = null;
        this._stateSubscription = null;
        this._lastRefresh = 0;
    }

    set panel(panel) {
        this.hass = panel.hass;
        this._initialize();
    }

    async _initialize() {
        this._render();
        this._attachEventListeners();
        await this._loadData();
        this._setupSubscriptions();
    }

    _render() {
        this.innerHTML = `
            <div class="lsg-panel">
                <div class="lsg-header">
                    <h1>Last Seen Guardian</h1>
                    <div class="lsg-header-actions">
                        <span class="lsg-last-refresh" id="lsg-last-refresh">
                            Last refresh: Never
                        </span>
                        <button class="lsg-refresh-btn" title="Refresh">
                            <ha-icon icon="mdi:refresh"></ha-icon>
                        </button>
                    </div>
                </div>
                
                <nav class="lsg-tabs">
                    ${TABS.map(tab => `
                        <button 
                            class="lsg-tab ${this.activeTab === tab.id ? 'lsg-tab-active' : ''}" 
                            data-tab="${tab.id}">
                            <ha-icon icon="${tab.icon}"></ha-icon>
                            <span>${tab.name}</span>
                        </button>
                    `).join("")}
                </nav>
                
                <div id="lsg-content" class="lsg-content">
                    <div class="lsg-loading">
                        <ha-circular-progress active></ha-circular-progress>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
        `;
    }

    _attachEventListeners() {
        // Tab switching
        this.querySelectorAll(".lsg-tab").forEach(btn =>
            btn.addEventListener("click", () => {
                this.activeTab = btn.dataset.tab;
                this.querySelectorAll(".lsg-tab").forEach(b => 
                    b.classList.remove("lsg-tab-active")
                );
                btn.classList.add("lsg-tab-active");
                this._renderActiveTab();
            })
        );
        
        // Refresh button
        const refreshBtn = this.querySelector(".lsg-refresh-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", async () => {
                refreshBtn.disabled = true;
                await this._loadData();
                refreshBtn.disabled = false;
            });
        }
    }

    async _loadData() {
        if (!this.hass) {
            console.error("LSG: hass not available");
            return;
        }

        try {
            // Load entities with health status
            const entitiesResponse = await this.hass.callWS({
                type: "last_seen_guardian/get_entities"
            });
        
            // Validate response
            if (!entitiesResponse || !Array.isArray(entitiesResponse.entities)) {
                console.error("LSG: Invalid entities response:", entitiesResponse);
                this._showError("Invalid data received from server");
                return;
            }
        
            this.entities = entitiesResponse.entities;
        
            // Load configuration
            const configResponse = await this.hass.callWS({
                type: "last_seen_guardian/get_config"
            });
        
            // Validate config response
            if (!configResponse || !configResponse.config) {
                console.error("LSG: Invalid config response:", configResponse);
                this.config = {}; // Use empty config as fallback
            } else {
                this.config = configResponse.config;
            }
        
            // Update last refresh timestamp
            this._lastRefresh = Date.now();
            this._updateRefreshTimestamp();
        
            console.log(`LSG: Loaded ${this.entities.length} entities`);
            this._renderActiveTab();
        
        } catch (error) {
            console.error("LSG: Error loading data:", error);
            this._showError(`Failed to load data: ${error.message || error}`);
        }
    }

    _setupSubscriptions() {
        if (!this.hass) return;
        
        // FIXED: Use event-based updates when possible (WARNING #2)
        // Subscribe to LSG-specific events (if implemented in backend)
        this._subscribeToEvents();
        
        // FIXED: Longer auto-refresh interval (WARNING #2)
        if (ENABLE_AUTO_REFRESH) {
            this._subscriptionId = setInterval(() => {
                // Only refresh if panel is visible
                if (document.visibilityState === 'visible') {
                    console.debug('LSG: Auto-refresh triggered');
                    this._loadData();
                } else {
                    console.debug('LSG: Skipping auto-refresh (page not visible)');
                }
            }, AUTO_REFRESH_INTERVAL_MS);
            
            console.log(`LSG: Auto-refresh enabled (every ${AUTO_REFRESH_INTERVAL_MS / 1000}s)`);
        }
        
        // Refresh when page becomes visible again
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                const timeSinceLastRefresh = Date.now() - this._lastRefresh;
                
                // Refresh if more than 60 seconds since last refresh
                if (timeSinceLastRefresh > 60000) {
                    console.debug('LSG: Page visible again, refreshing data');
                    this._loadData();
                }
            }
        });
    }

    _subscribeToEvents() {
        // Subscribe to Home Assistant state changes for tracked entities
        // This is more efficient than polling
        try {
            // Note: This requires entity_ids to be known upfront
            // Alternative: Subscribe to all state changes and filter
            
            if (this.hass.connection && this.hass.connection.subscribeEvents) {
                this._stateSubscription = this.hass.connection.subscribeEvents(
                    (event) => {
                        // Only refresh if an entity we're tracking changed
                        const changedEntity = event.data.entity_id;
                        const isTracked = this.entities.some(e => e.entity_id === changedEntity);
                        
                        if (isTracked) {
                            console.debug(`LSG: Tracked entity ${changedEntity} changed, refreshing`);
                            this._loadData();
                        }
                    },
                    'state_changed'
                );
                
                console.log('LSG: Subscribed to state_changed events');
            }
        } catch (error) {
            console.warn('LSG: Could not subscribe to events, falling back to polling', error);
        }
    }

    _updateRefreshTimestamp() {
        const el = this.querySelector('#lsg-last-refresh');
        if (el && this._lastRefresh) {
            const date = new Date(this._lastRefresh);
            el.textContent = `Last refresh: ${date.toLocaleTimeString()}`;
        }
    }

    _renderActiveTab() {
        const contentEl = this.querySelector("#lsg-content");
        if (!contentEl) return;
        
        contentEl.innerHTML = "";
        
        switch (this.activeTab) {
            case "sensors":
                contentEl.appendChild(
                    SensorsTab(this.entities, this.hass, this._onEntityClick.bind(this))
                );
                break;
            case "modes":
                contentEl.appendChild(
                    ModesTab(this.config, this.hass, this._onModeChange.bind(this))
                );
                break;
            case "general":
                contentEl.appendChild(
                    GeneralTab(this.config, this.hass, this._onConfigChange.bind(this))
                );
                break;
        }
    }

    _onEntityClick(entity) {
        // Open modal with entity details
        const modal = DeviceModal(entity, this.hass);
        this.appendChild(modal);
    }

    async _onModeChange(mode) {
        try {
            await this.hass.callWS({
                type: "last_seen_guardian/set_mode",
                mode: mode
            });
            this._showToast(`Mode changed to: ${mode}`);
            await this._loadData();
        } catch (error) {
            console.error("LSG: Error changing mode:", error);
            this._showError("Failed to change mode");
        }
    }

    async _onConfigChange(config) {
        try {
            await this.hass.callWS({
                type: "last_seen_guardian/set_config",
                config: config
            });
            this._showToast("Configuration saved");
            await this._loadData();
        } catch (error) {
            console.error("LSG: Error saving config:", error);
            this._showError("Failed to save configuration");
        }
    }

    _showError(message) {
        const contentEl = this.querySelector("#lsg-content");
        if (contentEl) {
            contentEl.innerHTML = `
                <div class="lsg-error">
                    <ha-icon icon="mdi:alert-circle"></ha-icon>
                    <p>${message}</p>
                </div>
            `;
        }
    }

    _showToast(message) {
        if (this.hass && this.hass.callService) {
            this.hass.callService("persistent_notification", "create", {
                message: message,
                title: "Last Seen Guardian"
            });
        }
    }

    disconnectedCallback() {
        // Cancel auto-refresh timer
        if (this._subscriptionId) {
            clearInterval(this._subscriptionId);
            this._subscriptionId = null;
        }
        
        // Unsubscribe from events
        if (this._stateSubscription) {
            this._stateSubscription.then(unsub => unsub());
            this._stateSubscription = null;
        }
    }
}

customElements.define('last-seen-guardian-panel', LastSeenGuardianPanel);