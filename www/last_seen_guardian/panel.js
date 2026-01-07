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

class LastSeenGuardianPanel extends HTMLElement {
    constructor() {
        super();
        this.activeTab = "sensors";
        this.entities = [];
        this.config = {};
        this.hass = null;
        this._subscriptionId = null;
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
                    <button class="lsg-refresh-btn" title="Refresh">
                        <ha-icon icon="mdi:refresh"></ha-icon>
                    </button>
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
            refreshBtn.addEventListener("click", () => this._loadData());
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
            this.entities = entitiesResponse.entities || [];
            
            // Load configuration
            const configResponse = await this.hass.callWS({
                type: "last_seen_guardian/get_config"
            });
            this.config = configResponse.config || {};
            
            this._renderActiveTab();
        } catch (error) {
            console.error("LSG: Error loading data:", error);
            this._showError("Failed to load data. Check logs.");
        }
    }

    _setupSubscriptions() {
        // Subscribe to state changes (if needed)
        if (!this.hass) return;
        
        // Auto-refresh every 30 seconds
        this._subscriptionId = setInterval(() => {
            this._loadData();
        }, 30000);
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
        if (this._subscriptionId) {
            clearInterval(this._subscriptionId);
        }
    }
}

customElements.define('last-seen-guardian-panel', LastSeenGuardianPanel);