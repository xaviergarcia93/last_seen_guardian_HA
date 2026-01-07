// www/last_seen_guardian/panel.test.js
import SensorsTab from './components/SensorsTab.js';

test('SensorsTab renders entities', () => {
    const entities = [
        { entity_id: "sensor.abc", status: "ok" },
        { entity_id: "sensor.def", status: "late" }
    ];
    const el = SensorsTab(entities);
    expect(el.innerHTML).toContain("sensor.abc");
    expect(el.innerHTML).toContain("ok");
});