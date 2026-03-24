function initializeMap() {
    // 1. Initialize Leaflet Map (Centered on Sweden for this example)
    var map = L.map('map').setView([53.33992508225579, -6.292003782101079], 13);

    // 2. Add a basic visual base layer (Raster tiles for simplicity during setup)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
    }).addTo(map);

    let clicks = [];
    let routeLayer = null;

    // 3. Listen for clicks to set Start and End points
    map.on('click', async function(e) {
    clicks.push(e.latlng);
    L.marker(e.latlng).addTo(map);

    if (clicks.length === 2) {
        let start = clicks[0];
        let end = clicks[1];

        // 4. Ask your Python Backend for the Route
        let response = await fetch(`http://127.0.0.1:8000/route?start_lat=${start.lat}&start_lon=${start.lng}&end_lat=${end.lat}&end_lon=${end.lng}`);
        let geojsonData = await response.json();

        // 5. Draw the Route on Leaflet
        if (routeLayer) map.removeLayer(routeLayer); // Clear old route
        routeLayer = L.geoJSON(geojsonData, { style: { color: 'blue', weight: 5 } }).addTo(map);
        
        clicks = []; // Reset for next route
    }
    });
}

// Initialize the map when the page loads
window.onload = initializeMap;