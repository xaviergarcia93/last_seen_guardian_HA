export default function ModesTab() {
    const container = document.createElement("div");
    container.className = "lsg-modes-tab";
    container.innerHTML = `
        <h3>Operation Modes</h3>
        <ul>
            <li>Normal</li>
            <li>Vacation</li>
            <li>Night</li>
        </ul>
    `;
    return container;
}