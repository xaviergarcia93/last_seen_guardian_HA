// www/last_seen_guardian/components/DeviceModal.js

/**
 * Device/Entity Detail Modal - Shows comprehensive diagnostics
 * 
 * Features:
 * - Entity metadata (domain, area, labels)
 * - Learning statistics (EWMA, threshold, event count)
 * - Health timeline (last 10 events)
 * - Automatic diagnostics (battery, network, pattern)
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
    
    // Calculate diagnostics
    const diagnostics = _generateDiagnostics(entity, stats);
    
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
                    ${diagnostics.message ? `
                        <p class="lsg-diagnostic-message">${diagnostics.message}</p>
                    ` : ''}
                </div>
            </section>
            
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
            ${diagnostics.issues.length > 0 ? `
                <section class="lsg-modal-section">
                    <h3>
                        <ha-icon icon="mdi:stethoscope"></ha-icon>
                        Automatic Diagnostics
                    </h3>
                    <div class="lsg-diagnostics-list">
                        ${diagnostics.issues.map(issue => `
                            <div class="lsg-diagnostic-item lsg-diagnostic-${issue.severity}">
                                <ha-icon icon="${issue.icon}"></ha-icon>
                                <div>
                                    <strong>${issue.title}</strong>
                                    <p>${issue.description}</p>
                                </div>
                            </div>
                        `).join('')}
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
            <button class="lsg-btn lsg-btn-secondary" data-action="reset-learning" disabled>
                <ha-icon icon="mdi:restore"></ha-icon>
                Reset Learning
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
    
    // Animate in
    setTimeout(() => overlay.classList.add('lsg-modal-open'), 10);
    
    return overlay;
}

/**
 * Generate automatic diagnostics based on entity data
 * @private
 */
function _generateDiagnostics(entity, stats) {
    const issues = [];
    const health = entity.health;
    
    // Health-based diagnostics
    if (health === 'stale') {
        const timeSinceLastEvent = Date.now() / 1000 - (stats.last_event || 0);
        issues.push({
            severity: 'error',
            icon: 'mdi:alert-circle',
            title: 'Entity Not Responding',
            description: `No activity for ${_formatInterval(timeSinceLastEvent)}. Possible causes: device offline, battery dead, network issue.`
        });
    } else if (health === 'late') {
        issues.push({
            severity: 'warning',
            icon: 'mdi:clock-alert',
            title: 'Delayed Reporting',
            description: 'Entity is reporting slower than expected. Monitor for potential issues.'
        });
    }
    
    // Event count diagnostics
    if (stats.event_count < 5) {
        issues.push({
            severity: 'info',
            icon: 'mdi:information',
            title: 'Learning Phase',
            description: `Only ${stats.event_count || 0} events recorded. System is still learning normal patterns.`
        });
    }
    
    // Pattern-based diagnostics
    if (stats.interval_ewma && stats.threshold) {
        const expectedMinutes = stats.interval_ewma / 60;
        const thresholdMinutes = stats.threshold / 60;
        
        if (expectedMinutes < 1) {
            issues.push({
                severity: 'info',
                icon: 'mdi:flash',
                title: 'High-Frequency Sensor',
                description: `Reports every ${_formatInterval(stats.interval_ewma)} on average. This is normal for motion/binary sensors.`
            });
        } else if (expectedMinutes > 1440) {
            issues.push({
                severity: 'info',
                icon: 'mdi:calendar-clock',
                title: 'Low-Frequency Sensor',
                description: `Reports every ${(expectedMinutes / 1440).toFixed(1)} days on average. This is normal for battery/update sensors.`
            });
        }
    }
    
    // Generate summary message
    let message = '';
    if (health === 'ok') {
        message = '✓ Entity is operating normally within expected patterns.';
    } else if (health === 'late') {
        message = '⚠ Entity is delayed but may recover. Continue monitoring.';
    } else if (health === 'stale') {
        message = '✗ Entity appears offline or unresponsive. Investigation needed.';
    } else {
        message = 'ℹ Insufficient data to determine health status.';
    }
    
    return { issues, message };
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