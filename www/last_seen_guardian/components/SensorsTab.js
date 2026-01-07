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
    
    // CRITICAL FIX: Validate entities parameter
    if (!Array.isArray(entities)) {
        console.error("LSG: entities parameter is not an array:", entities);
        container.innerHTML = `
            <div class="lsg-error">
                <ha-icon icon="mdi:alert-circle"></ha-icon>
                <p>Error loading entities data</p>
                <p class="lsg-hint">Check console for details</p>
            </div>
        `;
        return container;
    }
    
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

    // Extract unique values for filters with NULL SAFETY
    const uniqueAreas = [...new Set(
        entities
            .map(e => e.area_id)
            .filter(area => area && area !== null && area !== undefined)
    )].sort();
    
    const uniqueDomains = [...new Set(
        entities
            .map(e => e.domain)
            .filter(domain => domain && domain !== null && domain !== undefined)
    )].sort();
    
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

    // Group entities by health status for statistics with NULL SAFETY
    const healthStats = {
        ok: entities.filter(e => e && e.health === 'ok').length,
        late: entities.filter(e => e && e.health === 'late').length,
        stale: entities.filter(e => e && e.health === 'stale').length,
        unknown: entities.filter(e => !e || !e.health || e.health === 'unknown').length
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
        try {
            filteredEntities = entities.filter(entity => {
                // NULL SAFETY: Skip invalid entities
                if (!entity || !entity.entity_id) {
                    return false;
                }
                
                // Area filter
                if (activeFilters.area !== 'all' && entity.area_id !== activeFilters.area) {
                    return false;
                }
                
                // Domain filter
                if (activeFilters.domain !== 'all' && entity.domain !== activeFilters.domain) {
                    return false;
                }
                
                // Health filter
                const entityHealth = entity.health || 'unknown';
                if (activeFilters.health !== 'all' && entityHealth !== activeFilters.health) {
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
        } catch (error) {
            console.error("LSG: Error applying filters:", error);
        }
    }

    // Function to render table
    function renderTable() {
        try {
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
                // CRITICAL FIX: NULL SAFETY for all entity properties
                if (!entity || !entity.entity_id) {
                    console.warn("LSG: Skipping invalid entity:", entity);
                    return;
                }
                
                const health = entity.health || 'unknown';
                const healthClass = `lsg-health-${health}`;
                
                // NULL SAFETY: Check if stats exist
                const stats = entity.stats || {};
                const lastEvent = stats.last_event;
                const intervalEwma = stats.interval_ewma;
                const eventCount = stats.event_count || 0;
                
                // Format last update with NULL checks
                let lastUpdate = '<span class="lsg-no-data">Never</span>';
                if (lastEvent && typeof lastEvent === 'number') {
                    try {
                        lastUpdate = new Date(lastEvent * 1000).toLocaleString();
                    } catch (e) {
                        console.warn(`LSG: Invalid timestamp for ${entity.entity_id}:`, lastEvent);
                    }
                }
                
                // Format EWMA interval with NULL checks
                let ewmaInterval = '<span class="lsg-no-data">Learning...</span>';
                if (intervalEwma && typeof intervalEwma === 'number' && intervalEwma > 0) {
                    try {
                        ewmaInterval = `${(intervalEwma / 60).toFixed(1)} min`;
                    } catch (e) {
                        console.warn(`LSG: Invalid EWMA for ${entity.entity_id}:`, intervalEwma);
                    }
                }
                
                // Show learning status if insufficient data
                if (eventCount < 20) {
                    ewmaInterval = `<span class="lsg-no-data">Learning (${eventCount}/20)...</span>`;
                }
                
                // Format area with NULL check
                const areaName = entity.area_id && entity.area_id !== null
                    ? entity.area_id
                    : '<span class="lsg-no-area">No area</span>';
                
                // Format domain with NULL check
                const domain = entity.domain || 'unknown';
                
                const row = document.createElement("tr");
                row.className = "lsg-entity-row";
                row.dataset.entityId = entity.entity_id;
                
                row.innerHTML = `
                    <td class="lsg-entity-id">
                        <code>${entity.entity_id}</code>
                    </td>
                    <td>
                        <span class="lsg-domain-badge">${domain}</span>
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
            
            // Attach click handlers with NULL checks
            if (onEntityClick && typeof onEntityClick === 'function') {
                tableContainer.querySelectorAll('.lsg-btn-details').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        
                        try {
                            const entityId = e.currentTarget.dataset.entityId;
                            const entity = entities.find(ent => ent && ent.entity_id === entityId);
                            
                            if (entity) {
                                onEntityClick(entity);
                            } else {
                                console.warn(`LSG: Entity ${entityId} not found`);
                            }
                        } catch (error) {
                            console.error("LSG: Error in entity click handler:", error);
                        }
                    });
                });
                
                // Click on row to view details
                tableContainer.querySelectorAll('.lsg-entity-row').forEach(row => {
                    row.addEventListener('click', (e) => {
                        if (e.target.closest('.lsg-btn-details')) return;
                        
                        try {
                            const entityId = row.dataset.entityId;
                            const entity = entities.find(ent => ent && ent.entity_id === entityId);
                            
                            if (entity) {
                                onEntityClick(entity);
                            }
                        } catch (error) {
                            console.error("LSG: Error in row click handler:", error);
                        }
                    });
                });
            }
        } catch (error) {
            console.error("LSG: Error rendering table:", error);
            tableContainer.innerHTML = `
                <div class="lsg-error">
                    <ha-icon icon="mdi:alert-circle"></ha-icon>
                    <p>Error rendering entities table</p>
                    <p class="lsg-hint">${error.message}</p>
                </div>
            `;
        }
    }

    // Initial render
    renderTable();

    // Attach filter event listeners with NULL checks
    try {
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
                
                if (areaSelect) areaSelect.value = 'all';
                if (domainSelect) domainSelect.value = 'all';
                if (healthSelect) healthSelect.value = 'all';
                if (searchInput) searchInput.value = '';
                
                applyFilters();
            });
        }
    } catch (error) {
        console.error("LSG: Error attaching filter listeners:", error);
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