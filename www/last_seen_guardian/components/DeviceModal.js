// www/last_seen_guardian/components/DeviceModal.js

/**
 * Device/Entity Detail Modal - Shows comprehensive diagnostics
 * 
 * Features:
 * - Entity metadata (domain, area, labels)
 * - Learning statistics (EWMA, threshold, event count)
 * - Health timeline (last 10 events)
 * - Automatic diagnostics (battery, network, pattern)
 * - Technical context (v0.7): Battery, LQI, RSSI
 * 
 * @param {Object} entity - Entity data with health and stats
 * @param {Object} hass - Home Assistant instance
 * @returns {HTMLElement} Modal overlay element
 */
export default function DeviceModal(entity, hass = null) {
    // Create modal overlay
    const overlay = document.createElement("div");
    overlay.className = "lsg-modal-overlay";
    
    // Create modal container
    const modal = document.createElement("div");
    modal.className = "lsg-modal";
    
    const stats = entity.stats || {};
    const health = entity.health || 'unknown';
    const history = stats.history || [];
    const diagnosis = stats.diagnosis || {};
    const technicalContext = stats.technical_context || {};
    
    // Modal content
    modal.innerHTML = `
        <div class="lsg-modal-header">
            <div class="lsg-modal-title">
                <ha-icon icon="${_getEntityIcon(entity.domain)}"></ha-icon>
                <div>
                    <h2>Entity Details</h2>
                    <code>${entity.entity_id}</code>
                </div>
            </div>
            <button class="lsg-modal-close" aria-label="Close">
                <ha-icon icon="mdi:close"></ha-icon>
            </button>
        </div>
        
        <div class="lsg-modal-body">
            <!-- Health Status Section -->
            <section class="lsg-modal-section">
                <h3>
                    <ha-icon icon="mdi:heart-pulse"></ha-icon>
                    Health Status
                </h3>
                <div class="lsg-health-status-large">
                    <span class="lsg-health-badge lsg-health-${health}">
                        <ha-icon icon="${_getHealthIcon(health)}"></ha-icon>
                        ${health.toUpperCase()}
                    </span>
                    ${diagnosis.health ? `
                        <p class="lsg-diagnostic-message">
                            ${_getHealthMessage(diagnosis.health)}
                        </p>
                    ` : ''}
                </div>
            </section>
            
            <!-- Technical Context Section (v0.7) -->
            ${_renderTechnicalContext(technicalContext)}
            
            <!-- Metadata Section -->
            <section class="lsg-modal-section">
                <h3>
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    Metadata
                </h3>
                <div class="lsg-metadata-grid">
                    <div class="lsg-metadata-item">
                        <span class="lsg-metadata-label">Domain</span>
                        <span class="lsg-metadata-value">${entity.domain}</span>
                    </div>
                    <div class="lsg-metadata-item">
                        <span class="lsg-metadata-label">Platform</span>
                        <span class="lsg-metadata-value">${entity.platform || 'N/A'}</span>
                    </div>
                    <div class="lsg-metadata-item">
                        <span class="lsg-metadata-label">Area</span>
                        <span class="lsg-metadata-value">${entity.area_id || 'No area'}</span>
                    </div>
                    <div class="lsg-metadata-item">
                        <span class="lsg-metadata-label">Device ID</span>
                        <span class="lsg-metadata-value">${entity.device_id || 'N/A'}</span>
                    </div>
                    ${entity.labels && entity.labels.length > 0 ? `
                        <div class="lsg-metadata-item lsg-metadata-full">
                            <span class="lsg-metadata-label">Labels</span>
                            <div class="lsg-metadata-value">
                                ${entity.labels.map(l => `<span class="lsg-label-badge">${l}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </section>
            
            <!-- Learning Statistics Section -->
            <section class="lsg-modal-section">
                <h3>
                    <ha-icon icon="mdi:brain"></ha-icon>
                    Learning Statistics
                </h3>
                <div class="lsg-stats-grid">
                    <div class="lsg-stat-card">
                        <ha-icon icon="mdi:clock-outline"></ha-icon>
                        <div>
                            <span class="lsg-stat-label">Last Event</span>
                            <span class="lsg-stat-value">
                                ${stats.last_event ? _formatRelativeTime(stats.last_event) : 'Never'}
                            </span>
                        </div>
                    </div>
                    <div class="lsg-stat-card">
                        <ha-icon icon="mdi:chart-line"></ha-icon>
                        <div>
                            <span class="lsg-stat-label">EWMA Interval</span>
                            <span class="lsg-stat-value">
                                ${stats.interval_ewma ? _formatInterval(stats.interval_ewma) : 'Learning...'}
                            </span>
                        </div>
                    </div>
                    <div class="lsg-stat-card">
                        <ha-icon icon="mdi:alarm"></ha-icon>
                        <div>
                            <span class="lsg-stat-label">Alert Threshold</span>
                            <span class="lsg-stat-value">
                                ${stats.threshold ? _formatInterval(stats.threshold) : 'Learning...'}
                            </span>
                        </div>
                    </div>
                    <div class="lsg-stat-card">
                        <ha-icon icon="mdi:counter"></ha-icon>
                        <div>
                            <span class="lsg-stat-label">Event Count</span>
                            <span class="lsg-stat-value">${stats.event_count || 0}</span>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- Diagnostics Section -->
            ${diagnosis.potential_causes && diagnosis.potential_causes.length > 0 ? `
                <section class="lsg-modal-section">
                    <h3>
                        <ha-icon icon="mdi:stethoscope"></ha-icon>
                        Automatic Diagnostics
                    </h3>
                    <div class="lsg-diagnostics-list">
                        ${_renderDiagnostics(diagnosis)}
                    </div>
                </section>
            ` : ''}
            
            <!-- History Timeline Section -->
            ${history.length > 0 ? `
                <section class="lsg-modal-section">
                    <h3>
                        <ha-icon icon="mdi:timeline-clock"></ha-icon>
                        Recent Activity (Last ${Math.min(history.length, 10)} events)
                    </h3>
                    <div class="lsg-history-timeline">
                        ${history.slice(-10).reverse().map((event, idx) => `
                            <div class="lsg-history-item">
                                <span class="lsg-history-time">
                                    ${_formatRelativeTime(event.timestamp)}
                                </span>
                                <div class="lsg-history-dot"></div>
                                <div class="lsg-history-details">
                                    <span class="lsg-history-state">${event.state}</span>
                                    <span class="lsg-history-interval">
                                        Δ ${_formatInterval(event.interval)}
                                    </span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </section>
            ` : ''}
        </div>
        
        <div class="lsg-modal-footer">
            <button class="lsg-btn lsg-btn-secondary" data-action="view-entity">
                <ha-icon icon="mdi:open-in-new"></ha-icon>
                View in HA
            </button>
            <button class="lsg-btn lsg-btn-secondary" data-action="export" title="Export diagnostics">
                <ha-icon icon="mdi:download"></ha-icon>
                Export
            </button>
            <button class="lsg-btn lsg-btn-primary" data-action="close">
                Close
            </button>
        </div>
    `;
    
    overlay.appendChild(modal);
    
    // Event listeners
    const closeBtn = modal.querySelector('.lsg-modal-close');
    const closeFooterBtn = modal.querySelector('[data-action="close"]');
    const viewEntityBtn = modal.querySelector('[data-action="view-entity"]');
    const exportBtn = modal.querySelector('[data-action="export"]');
    
    const closeModal = () => {
        overlay.classList.add('lsg-modal-closing');
        setTimeout(() => overlay.remove(), 300);
    };
    
    closeBtn.addEventListener('click', closeModal);
    closeFooterBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    
    // View entity in HA (opens more-info dialog)
    if (viewEntityBtn && hass) {
        viewEntityBtn.addEventListener('click', () => {
            const event = new CustomEvent('hass-more-info', {
                detail: { entityId: entity.entity_id },
                bubbles: true,
                composed: true
            });
            overlay.dispatchEvent(event);
        });
    }
    
    // Export diagnostics (v0.8)
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            try {
                const diagnosticsData = {
                    entity_id: entity.entity_id,
                    timestamp: new Date().toISOString(),
                    health: health,
                    stats: stats,
                    diagnosis: diagnosis,
                    technical_context: technicalContext,
                    metadata: {
                        domain: entity.domain,
                        platform: entity.platform,
                        area_id: entity.area_id,
                        device_id: entity.device_id,
                        labels: entity.labels
                    }
                };
                
                const blob = new Blob(
                    [JSON.stringify(diagnosticsData, null, 2)],
                    { type: 'application/json' }
                );
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `lsg_diagnostics_${entity.entity_id.replace('.', '_')}_${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                console.log('LSG: Diagnostics exported successfully');
            } catch (error) {
                console.error('LSG: Error exporting diagnostics:', error);
            }
        });
    }
    
    // Animate in
    setTimeout(() => overlay.classList.add('lsg-modal-open'), 10);
    
    return overlay;
}

/**
 * Render technical context section (v0.7)
 * @private
 */
function _renderTechnicalContext(context) {
    if (!context || Object.keys(context).length === 0) {
        return '';
    }
    
    const items = [];
    
    // Battery
    if ('battery_level' in context) {
        const batteryLevel = context.battery_level;
        const batteryStatus = context.battery_status || 'unknown';
        const statusClass = batteryStatus === 'critical' ? 'error' : 
                           batteryStatus === 'low' ? 'warning' : '';
        
        items.push(`
            <div class="lsg-context-card ${statusClass ? 'lsg-context-' + statusClass : ''}">
                <ha-icon class="lsg-context-icon" icon="mdi:battery"></ha-icon>
                <div>
                    <span class="lsg-context-label">Battery Level</span>
                    <span class="lsg-context-value">${batteryLevel.toFixed(0)}%</span>
                </div>
            </div>
        `);
    }
    
    // LQI (Zigbee)
    if ('lqi' in context) {
        const lqi = context.lqi;
        const lqiStatus = context.lqi_status || 'ok';
        const statusClass = lqiStatus === 'low' ? 'warning' : '';
        
        items.push(`
            <div class="lsg-context-card ${statusClass ? 'lsg-context-' + statusClass : ''}">
                <ha-icon class="lsg-context-icon" icon="mdi:wifi"></ha-icon>
                <div>
                    <span class="lsg-context-label">Link Quality (LQI)</span>
                    <span class="lsg-context-value">${lqi}</span>
                </div>
            </div>
        `);
    }
    
    // RSSI (WiFi/BLE)
    if ('rssi' in context) {
        const rssi = context.rssi;
        const rssiStatus = context.rssi_status || 'ok';
        const statusClass = rssiStatus === 'low' ? 'warning' : '';
        
        items.push(`
            <div class="lsg-context-card ${statusClass ? 'lsg-context-' + statusClass : ''}">
                <ha-icon class="lsg-context-icon" icon="mdi:signal"></ha-icon>
                <div>
                    <span class="lsg-context-label">Signal Strength (RSSI)</span>
                    <span class="lsg-context-value">${rssi} dBm</span>
                </div>
            </div>
        `);
    }
    
    if (items.length === 0) {
        return '';
    }
    
    return `
        <section class="lsg-modal-section">
            <h3>
                <ha-icon icon="mdi:chip"></ha-icon>
                Technical Context
            </h3>
            <div class="lsg-technical-context">
                ${items.join('')}
            </div>
        </section>
    `;
}

/**
 * Render diagnostics list
 * @private
 */
function _renderDiagnostics(diagnosis) {
    const causes = diagnosis.potential_causes || [];
    const recommendations = diagnosis.recommendations || [];
    
    const items = [];
    
    // Map causes to diagnostic items
    causes.forEach((cause, index) => {
        const recommendation = recommendations[index] || '';
        let severity = 'info';
        let icon = 'mdi:information';
        
        if (cause.includes('critical') || cause.includes('offline')) {
            severity = 'error';
            icon = 'mdi:alert-circle';
        } else if (cause.includes('low') || cause.includes('poor')) {
            severity = 'warning';
            icon = 'mdi:alert';
        }
        
        const title = cause.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        items.push(`
            <div class="lsg-diagnostic-item lsg-diagnostic-${severity}">
                <ha-icon icon="${icon}"></ha-icon>
                <div>
                    <strong>${title}</strong>
                    ${recommendation ? `<p>${recommendation}</p>` : ''}
                </div>
            </div>
        `);
    });
    
    return items.join('');
}

/**
 * Get health message
 * @private
 */
function _getHealthMessage(health) {
    const messages = {
        'ok': '✓ Entity is operating normally within expected patterns.',
        'late': '⚠ Entity is delayed but may recover. Continue monitoring.',
        'stale': '✗ Entity appears offline or unresponsive. Investigation needed.',
        'unknown': 'ℹ Insufficient data to determine health status.'
    };
    return messages[health] || messages.unknown;
}

/**
 * Get icon for entity domain
 * @private
 */
function _getEntityIcon(domain) {
    const icons = {
        'sensor': 'mdi:gauge',
        'binary_sensor': 'mdi:checkbox-marked-circle',
        'light': 'mdi:lightbulb',
        'switch': 'mdi:toggle-switch',
        'climate': 'mdi:thermostat',
        'cover': 'mdi:window-shutter',
        'lock': 'mdi:lock',
        'camera': 'mdi:camera',
        'media_player': 'mdi:speaker'
    };
    return icons[domain] || 'mdi:help-circle';
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

/**
 * Format timestamp as relative time
 * @private
 */
function _formatRelativeTime(timestamp) {
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return `${Math.floor(diff / 86400)} days ago`;
}

/**
 * Format interval in seconds to human-readable
 * @private
 */
function _formatInterval(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
    return `${(seconds / 86400).toFixed(1)}d`;
}