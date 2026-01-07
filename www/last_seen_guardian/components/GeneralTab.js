export default function GeneralTab() {
    const c = document.createElement("div");
    c.className = "lsg-general-tab";
    c.innerHTML = `
        <h3>Last Seen Guardian Settings</h3>
        <p>Configure global settings here.</p>
    `;
    return c;
}