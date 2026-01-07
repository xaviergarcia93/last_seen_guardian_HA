// www/last_seen_guardian/components/SensorsTab.js

/**
 * Renders the "Sensors" tab with device/entity summaries.
 * 
 * @param {Array} entities - List of entities with health data
 * @param {Object} hass - Home Assistant instance
 * @param {Function} onEntityClick - Callback when entity is clicked
 * @returns {HTMLElement} Container element with entity table
 */
export default function SensorsTab(entities = [], hass = null, onEntityClick = null) {
    const container = document.createElement("div");
    container.className = "lsg-sensors-tab";
    
    // Empty state
    if (!entities.length) {
        container.innerHTML = `
            <div class="lsg-empty-state">
                <ha-icon icon="mdi:information-outline"></ha-icon>
                <p>No devices found or still learning patterns.</p>
                <p class="lsg-hint">Devices will appear here after they report state changes.</p>
            </div>
        `;
        return container;
    }

    // Group entities by health status for statistics
    const healthStats = {
        ok: entities.filter(e => e.health === 'ok').length,
        late: entities.filter(e => e.health === 'late').length,
        stale: entities.filter(e => e.health === 'stale').length,
        unknown: entities.filter(e => !e.health || e.health === 'unknown').length
    };

    // Stats summary
    const statsBar = document.createElement("div");
    statsBar.className = "lsg-stats-bar";
    statsBar.innerHTML = `
        <div class="lsg-stat lsg-stat-ok">
            <ha-icon icon="mdi:check-circle"></ha-icon>
            <span>${healthStats.ok} OK</span>
        </div>
        <div class="lsg-stat lsg-stat-late">
            <ha-icon icon="mdi:clock-alert"></ha-icon>
            <span>${healthStats.late} Late</span>
        </div>
        <div class="lsg-stat lsg-stat-stale">
            <ha-icon icon="mdi:alert-circle"></ha-icon>
            <span>${healthStats.stale} Stale</span>
        </div>
        <div class="lsg-stat lsg-stat-unknown">
            <ha-icon icon="mdi:help-circle"></ha-icon>
            <span>${healthStats.unknown} Unknown</span>
        </div>
    `;
    container.appendChild(statsBar);

    // Create table
    const table = document.createElement("table");
    table.className = "lsg-entities-table";
    
    const thead = document.createElement("thead");
    thead.innerHTML = `
        <tr>
            <th>Entity ID</th>
            <th>Domain</th>
            <th>Area</th>
            <th>Health Status</th>
            <th>Last Update</th>
            <th>EWMA Interval</th>
            <th>Actions</th>
        </tr>
    `;
    table.appendChild(thead);
    
    const tbody = document.createElement("tbody");
    
    entities.forEach(entity => {
        // FIXED: Use 'health' instead of 'status' (ISSUE #3)
        const health = entity.health || 'unknown';
        const healthClass = `lsg-health-${health}`;
        
        // Format last update timestamp
        const lastUpdate = entity.stats?.last_event 
            ? new Date(entity.stats.last_event * 1000).toLocaleString()
            : '<span class="lsg-no-data">Never</span>';
        
        // Format EWMA interval
        const ewmaInterval = entity.stats?.interval_ewma
            ? `${(entity.stats.interval_ewma / 60).toFixed(1)} min`
            : '<span class="lsg-no-data">Learning...</span>';
        
        // Format area
        const areaName = entity.area_id || '<span class="lsg-no-area">No area</span>';
        
        const row = document.createElement("tr");
        row.className = "lsg-entity-row";
        row.dataset.entityId = entity.entity_id;
        
        row.innerHTML = `
            <td class="lsg-entity-id">
                <code>${entity.entity_id}</code>
            </td>
            <td>
                <span class="lsg-domain-badge">${entity.domain}</span>
            </td>
            <td>${areaName}</td>
            <td>
                <span class="lsg-health-badge ${healthClass}">
                    <ha-icon icon="${_getHealthIcon(health)}"></ha-icon>
                    ${health.toUpperCase()}
                </span>
            </td>
            <td class="lsg-timestamp">${lastUpdate}</td>
            <td class="lsg-interval">${ewmaInterval}</td>
            <td>
                <button 
                    class="lsg-btn-details" 
                    data-entity-id="${entity.entity_id}"
                    title="View details">
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    container.appendChild(table);
    
    // FIXED: Attach click handlers with proper callback (ISSUE #4)
    if (onEntityClick && typeof onEntityClick === 'function') {
        container.querySelectorAll('.lsg-btn-details').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const entityId = e.currentTarget.dataset.entityId;
                const entity = entities.find(ent => ent.entity_id === entityId);
                
                if (entity) {
                    onEntityClick(entity);
                } else {
                    console.warn(`LSG: Entity ${entityId} not found`);
                }
            });
        });
        
        // Optional: Click on row to view details
        container.querySelectorAll('.lsg-entity-row').forEach(row => {
            row.addEventListener('click', (e) => {
                // Don't trigger if clicking the button
                if (e.target.closest('.lsg-btn-details')) return;
                
                const entityId = row.dataset.entityId;
                const entity = entities.find(ent => ent.entity_id === entityId);
                
                if (entity) {
                    onEntityClick(entity);
                }
            });
        });
    }
    
    return container;
}

/**
 * Get icon for health status
 * @private
 */
function _getHealthIcon(health) {
    const icons = {
        'ok': 'mdi:check-circle',
        'late': 'mdi:clock-alert',
        'stale': 'mdi:alert-circle',
        'unknown': 'mdi:help-circle'
    };
    return icons[health] || icons.unknown;
}