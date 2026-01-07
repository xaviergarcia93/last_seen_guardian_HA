// Renders the "Sensors" tab with device/entity summaries.
export default function SensorsTab(entities=[]) {
    const container = document.createElement("div");
    container.className = "lsg-sensors-tab";
    if (!entities.length) {
        container.innerHTML = "<p>No devices found.</p>";
        return container;
    }
    const grid = document.createElement("table");
    grid.innerHTML = `
      <tr>
        <th>Entity ID</th><th>Status</th>
      </tr>
      ${entities.map(e => `
        <tr>
          <td>${e.entity_id}</td>
          <td>
            <span class="lsg-health-${e.status}">${e.status}</span>
          </td>
        </tr>
      `).join("")}
    `;
    container.appendChild(grid);
    return container;
}