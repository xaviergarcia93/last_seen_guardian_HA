// www/last_seen_guardian/components/GeneralTab.js

/**
 * General Settings Tab - Global configuration
 * 
 * @param {Object} config - Current configuration object
 * @param {Object} hass - Home Assistant instance
 * @param {Function} onConfigChange - Callback when config changes
 * @returns {HTMLElement} Container element
 */
export default function GeneralTab(config = {}, hass = null, onConfigChange = null) {
    const container = document.createElement("div");
    container.className = "lsg-general-tab";
    
    const globalConfig = config?.global || {};
    const checkInterval = globalConfig.check_every_minutes || 15;
    const thresholdMultiplier = globalConfig.alert_threshold_multiplier || 2.5;
    const enableNotifications = globalConfig.enable_notifications !== false;
    const notifyTarget = globalConfig.notify_target || "notify.notify";
    
    // Header
    const header = document.createElement("div");
    header.className = "lsg-general-header";
    header.innerHTML = `
        <h2>General Settings</h2>
        <p class="lsg-subtitle">Configure global monitoring behavior</p>
    `;
    container.appendChild(header);
    
    // Configuration form
    const form = document.createElement("form");
    form.className = "lsg-config-form";
    form.innerHTML = `
        <section class="lsg-config-section">
            <h3>
                <ha-icon icon="mdi:clock-outline"></ha-icon>
                Monitoring Intervals
            </h3>
            
            <div class="lsg-form-group">
                <label for="check_interval">
                    Evaluation Interval
                    <span class="lsg-label-hint">How often to check entity health</span>
                </label>
                <div class="lsg-input-with-unit">
                    <input 
                        type="number" 
                        id="check_interval" 
                        name="check_interval"
                        min="5" 
                        max="60" 
                        step="5"
                        value="${checkInterval}">
                    <span class="lsg-unit">minutes</span>
                </div>
                <p class="lsg-help-text">
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    Recommended: 15 minutes. Lower values increase resource usage.
                </p>
            </div>
        </section>
        
        <section class="lsg-config-section">
            <h3>
                <ha-icon icon="mdi:chart-bell-curve"></ha-icon>
                Learning & Thresholds
            </h3>
            
            <div class="lsg-form-group">
                <label for="threshold_multiplier">
                    Alert Threshold Multiplier
                    <span class="lsg-label-hint">How much deviation before alerting</span>
                </label>
                <div class="lsg-input-with-unit">
                    <input 
                        type="number" 
                        id="threshold_multiplier" 
                        name="threshold_multiplier"
                        min="1.5" 
                        max="5.0" 
                        step="0.1"
                        value="${thresholdMultiplier}">
                    <span class="lsg-unit">× EWMA</span>
                </div>
                <p class="lsg-help-text">
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    Default: 2.5x. Higher = fewer alerts but slower detection.
                </p>
            </div>
            
            <div class="lsg-form-group">
                <label>
                    <input 
                        type="checkbox" 
                        id="auto_learn"
                        name="auto_learn"
                        checked
                        disabled>
                    Automatic Pattern Learning
                    <span class="lsg-badge lsg-badge-success">Always On</span>
                </label>
                <p class="lsg-help-text">
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    LSG continuously learns from entity behavior using EWMA.
                </p>
            </div>
        </section>
        
        <section class="lsg-config-section">
            <h3>
                <ha-icon icon="mdi:bell-outline"></ha-icon>
                Notifications
            </h3>
            
            <div class="lsg-form-group">
                <label>
                    <input 
                        type="checkbox" 
                        id="enable_notifications"
                        name="enable_notifications"
                        ${enableNotifications ? 'checked' : ''}>
                    Enable Alert Notifications
                </label>
                <p class="lsg-help-text">
                    <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
                    Coming in v0.6: Smart notifications with throttling and mode awareness.
                </p>
            </div>
            
            <div class="lsg-form-group">
                <label for="notify_target">
                    Notification Service
                    <span class="lsg-label-hint">Home Assistant notify service</span>
                </label>
                <input 
                    type="text" 
                    id="notify_target" 
                    name="notify_target"
                    value="${notifyTarget}"
                    placeholder="notify.notify"
                    disabled>
                <p class="lsg-help-text">
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    Feature coming soon. Currently using persistent notifications.
                </p>
            </div>
        </section>
        
        <section class="lsg-config-section">
            <h3>
                <ha-icon icon="mdi:database-outline"></ha-icon>
                Data Management
            </h3>
            
            <div class="lsg-form-group">
                <label>Learning State Status</label>
                <div class="lsg-info-box">
                    <ha-icon icon="mdi:brain"></ha-icon>
                    <div>
                        <strong>Active Learning</strong>
                        <p>System is continuously learning entity patterns.</p>
                    </div>
                </div>
            </div>
            
            <div class="lsg-form-group lsg-form-actions">
                <button type="button" class="lsg-btn lsg-btn-secondary" id="btn_export_data" disabled>
                    <ha-icon icon="mdi:download"></ha-icon>
                    Export Learning Data
                </button>
                <button type="button" class="lsg-btn lsg-btn-danger" id="btn_reset_learning" disabled>
                    <ha-icon icon="mdi:restore"></ha-icon>
                    Reset All Learning
                </button>
            </div>
            <p class="lsg-help-text">
                <ha-icon icon="mdi:clock-outline"></ha-icon>
                Export and reset features coming in v0.8.
            </p>
        </section>
        
        <div class="lsg-form-actions lsg-form-actions-main">
            <button type="submit" class="lsg-btn lsg-btn-primary">
                <ha-icon icon="mdi:content-save"></ha-icon>
                Save Settings
            </button>
            <button type="button" class="lsg-btn lsg-btn-secondary" id="btn_cancel">
                <ha-icon icon="mdi:close"></ha-icon>
                Cancel
            </button>
        </div>
    `;
    
    container.appendChild(form);
    
    // Attach event listeners
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!onConfigChange || typeof onConfigChange !== 'function') {
            console.warn('LSG: No config change handler provided');
            return;
        }
        
        const formData = new FormData(form);
        const newConfig = {
            global: {
                check_every_minutes: parseInt(formData.get('check_interval'), 10),
                alert_threshold_multiplier: parseFloat(formData.get('threshold_multiplier')),
                enable_notifications: formData.get('enable_notifications') === 'on',
                notify_target: formData.get('notify_target') || 'notify.notify'
            }
        };
        
        // Disable submit button during save
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<ha-icon icon="mdi:loading"></ha-icon> Saving...';
        
        try {
            await onConfigChange(newConfig);
            submitBtn.innerHTML = '<ha-icon icon="mdi:check"></ha-icon> Saved!';
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 2000);
        } catch (error) {
            console.error('LSG: Error saving config:', error);
            submitBtn.innerHTML = '<ha-icon icon="mdi:alert"></ha-icon> Error';
            submitBtn.disabled = false;
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
            }, 3000);
        }
    });
    
    // Cancel button
    const cancelBtn = form.querySelector('#btn_cancel');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            form.reset();
        });
    }
    
    return container;
}