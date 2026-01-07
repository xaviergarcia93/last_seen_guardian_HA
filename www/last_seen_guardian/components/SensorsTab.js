// www/last_seen_guardian/components/SensorsTab.js

/**
 * Renders the "Sensors" tab with device/entity summaries and filters.
 * @param {Array} entities - List of entities with health data
 * @param {Object} hass - Home Assistant instance
 * @param {Function} onEntityClick - Callback when entity is clicked
 * @returns {HTMLElement} Container element
 */
export default function SensorsTab(entities = [], hass = null, onEntityClick = null) {
    const container = document.createElement("div");
    container.className = "lsg-sensors-tab";
    
    // State for filters
    let filteredEntities = [...entities];
    let activeFilters = {
        area: 'all',
        domain: 'all',
        health: 'all',
        search: ''
    };
    
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

    // Extract unique values for filters
    const uniqueAreas = [...new Set(entities.map(e => e.area_id).filter(Boolean))].sort();
    const uniqueDomains = [...new Set(entities.map(e => e.domain))].sort();
    const healthStates = ['ok', 'late', 'stale', 'unknown'];

    // Build filters UI
    const filtersHtml = `
        <div class="lsg-filters-bar">
            <div class="lsg-filter-group">
                <label for="filter-area">
                    <ha-icon icon="mdi:map-marker"></ha-icon>
                    Area
                </label>
                <select id="filter-area" class="lsg-filter-select">
                    <option value="all">All Areas</option>
                    ${uniqueAreas.map(area => `
                        <option value="${area}">${area}</option>
                    `).join('')}
                </select>
            </div>
            
            <div class="lsg-filter-group">
                <label for="filter-domain">
                    <ha-icon icon="mdi:puzzle"></ha-icon>
                    Domain
                </label>
                <select id="filter-domain" class="lsg-filter-select">
                    <option value="all">All Domains</option>
                    ${uniqueDomains.map(domain => `
                        <option value="${domain}">${domain}</option>
                    `).join('')}
                </select>
            </div>
            
            <div class="lsg-filter-group">
                <label for="filter-health">
                    <ha-icon icon="mdi:heart-pulse"></ha-icon>
                    Health
                </label>
                <select id="filter-health" class="lsg-filter-select">
                    <option value="all">All States</option>
                    ${healthStates.map(health => `
                        <option value="${health}">${health.toUpperCase()}</option>
                    `).join('')}
                </select>
            </div>
            
            <div class="lsg-filter-group lsg-filter-search">
                <label for="filter-search">
                    <ha-icon icon="mdi:magnify"></ha-icon>
                    Search
                </label>
                <input 
                    type="search" 
                    id="filter-search" 
                    class="lsg-filter-input"
                    placeholder="Search entity ID..."
                />
            </div>
            
            <button class="lsg-btn lsg-btn-secondary lsg-btn-reset-filters" id="btn-reset-filters">
                <ha-icon icon="mdi:filter-off"></ha-icon>
                Reset
            </button>
        </div>
    `;

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

    // Add filters
    const filtersContainer = document.createElement("div");
    filtersContainer.innerHTML = filtersHtml;
    container.appendChild(filtersContainer);

    // Results counter
    const resultsCounter = document.createElement("div");
    resultsCounter.className = "lsg-results-counter";
    resultsCounter.innerHTML = `Showing ${entities.length} of ${entities.length} entities`;
    container.appendChild(resultsCounter);

    // Table container
    const tableContainer = document.createElement("div");
    tableContainer.className = "lsg-table-container";
    container.appendChild(tableContainer);

    // Function to apply filters
    function applyFilters() {
        filteredEntities = entities.filter(entity => {
            // Area filter
            if (activeFilters.area !== 'all' && entity.area_id !== activeFilters.area) {
                return false;
            }
            
            // Domain filter
            if (activeFilters.domain !== 'all' && entity.domain !== activeFilters.domain) {
                return false;
            }
            
            // Health filter
            if (activeFilters.health !== 'all' && entity.health !== activeFilters.health) {
                return false;
            }
            
            // Search filter
            if (activeFilters.search && !entity.entity_id.toLowerCase().includes(activeFilters.search.toLowerCase())) {
                return false;
            }
            
            return true;
        });
        
        // Update counter
        resultsCounter.innerHTML = `Showing ${filteredEntities.length} of ${entities.length} entities`;
        
        // Re-render table
        renderTable();
    }

    // Function to render table
    function renderTable() {
        if (filteredEntities.length === 0) {
            tableContainer.innerHTML = `
                <div class="lsg-empty-state">
                    <ha-icon icon="mdi:filter-remove"></ha-icon>
                    <p>No entities match the current filters.</p>
                    <p class="lsg-hint">Try adjusting or resetting the filters.</p>
                </div>
            `;
            return;
        }

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
        
        filteredEntities.forEach(entity => {
            const health = entity.health || 'unknown';
            const healthClass = `lsg-health-${health}`;
            
            const lastUpdate = entity.stats?.last_event 
                ? new Date(entity.stats.last_event * 1000).toLocaleString()
                : '<span class="lsg-no-data">Never</span>';
            
            const ewmaInterval = entity.stats?.interval_ewma
                ? `${(entity.stats.interval_ewma / 60).toFixed(1)} min`
                : '<span class="lsg-no-data">Learning...</span>';
            
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
        tableContainer.innerHTML = '';
        tableContainer.appendChild(table);
        
        // Attach click handlers
        if (onEntityClick && typeof onEntityClick === 'function') {
            tableContainer.querySelectorAll('.lsg-btn-details').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const entityId = e.currentTarget.dataset.entityId;
                    const entity = entities.find(ent => ent.entity_id === entityId);
                    
                    if (entity) {
                        onEntityClick(entity);
                    }
                });
            });
            
            // Click on row to view details
            tableContainer.querySelectorAll('.lsg-entity-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    if (e.target.closest('.lsg-btn-details')) return;
                    
                    const entityId = row.dataset.entityId;
                    const entity = entities.find(ent => ent.entity_id === entityId);
                    
                    if (entity) {
                        onEntityClick(entity);
                    }
                });
            });
        }
    }

    // Initial render
    renderTable();

    // Attach filter event listeners
    const areaSelect = container.querySelector('#filter-area');
    const domainSelect = container.querySelector('#filter-domain');
    const healthSelect = container.querySelector('#filter-health');
    const searchInput = container.querySelector('#filter-search');
    const resetBtn = container.querySelector('#btn-reset-filters');

    if (areaSelect) {
        areaSelect.addEventListener('change', (e) => {
            activeFilters.area = e.target.value;
            applyFilters();
        });
    }

    if (domainSelect) {
        domainSelect.addEventListener('change', (e) => {
            activeFilters.domain = e.target.value;
            applyFilters();
        });
    }

    if (healthSelect) {
        healthSelect.addEventListener('change', (e) => {
            activeFilters.health = e.target.value;
            applyFilters();
        });
    }

    if (searchInput) {
        // Debounce search input
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                activeFilters.search = e.target.value;
                applyFilters();
            }, 300);
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            activeFilters = {
                area: 'all',
                domain: 'all',
                health: 'all',
                search: ''
            };
            
            areaSelect.value = 'all';
            domainSelect.value = 'all';
            healthSelect.value = 'all';
            searchInput.value = '';
            
            applyFilters();
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