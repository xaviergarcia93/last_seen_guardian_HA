// www/last_seen_guardian/panel.js
import './assets/lsg.css';
import SensorsTab from './components/SensorsTab.js';
import ModesTab from './components/ModesTab.js';
import GeneralTab from './components/GeneralTab.js';
import DeviceModal from './components/DeviceModal.js';

const TABS = [
    {id: "sensors", name: "Sensors"},
    {id: "modes", name: "Modes"},
    {id: "general", name: "General"},
];

class LastSeenGuardianPanel extends HTMLElement {
    constructor() {
        super();
        this.activeTab = "sensors";
        this.entities = [];
    }

    connectedCallback() {
        this.innerHTML = `
            <div class="lsg-panel">
                <nav class="lsg-tabs">
                    ${TABS.map(tab =>
                        `<button 
                          class="lsg-tab${this.activeTab===tab.id?" lsg-tab-active":""}" 
                          data-tab="${tab.id}">${tab.name}</button>`
                    ).join("")}
                </nav>
                <div id="lsg-content"></div>
            </div>
        `;
        this._attachEventListeners();
        this._loadEntities();
        this._renderActiveTab();
    }

    _attachEventListeners() {
        this.querySelectorAll(".lsg-tab").forEach(btn =>
            btn.addEventListener("click", (e) => {
                this.activeTab = btn.dataset.tab;
                this._renderActiveTab();
            })
        );
    }

    async _loadEntities() {
        // Basic: fetch from websocket
        // Here you should use ha.callWS or similar, depending on HA context
        if (window.hassConnection && window.hassConnection.socket) {
            window.hassConnection.socket.sendMessage({
                type: "last_seen_guardian/get_entities"
            });
            // Subscribe to updates, etc.
        } else {
            // Mock/demo: show test entities for local dev
            this.entities = [
                {entity_id: "sensor.door1", status: "ok"},
                {entity_id: "sensor.fridge1", status: "late"},
                {entity_id: "sensor.freezer1", status: "stale"}
            ];
        }
        this._renderActiveTab();
    }
    _renderActiveTab() {
        let el = this.querySelector("#lsg-content");
        el.innerHTML = "";
        switch (this.activeTab) {
            case "sensors":
                el.appendChild(SensorsTab(this.entities));
                break;
            case "modes":
                el.appendChild(ModesTab());
                break;
            case "general":
                el.appendChild(GeneralTab());
                break;
        }
    }
}
customElements.define('lsg-panel', LastSeenGuardianPanel);

// Mount the panel (used by HA)
document.currentScript &&
    document.currentScript.parentElement &&
    document.currentScript.parentElement.appendChild(document.createElement('lsg-panel'));