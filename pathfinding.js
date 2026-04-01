function initializeMap() {
    // 1. Initialize Leaflet Map (Centered on faroe islands for this example)
    var map = L.map('map').setView([62.01231038198972, -6.7739696801750915], 13);

    // 2. Add a basic visual base layer (Raster tiles for simplicity during setup)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
    }).addTo(map);

    let clicks = [];
    let drawnLayers = []; // Keep track of everything we draw so we can clear it

    // A helper function to pause JavaScript (creates the animation effect)
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    map.on('click', async function(e) {
        clicks.push(e.latlng);
        let marker = L.marker(e.latlng).addTo(map);
        drawnLayers.push(marker);

        if (clicks.length === 2) {
            let start = clicks[0];
            let end = clicks[1];
            let algorithm = document.getElementById("algorithm").value; // Get selected algorithm

            // Fetch the data from your new endpoint
            let response = await fetch(`http://localhost:8000/route?start_lat=${start.lat}&start_lon=${start.lng}&end_lat=${end.lat}&end_lon=${end.lng}&algorithm=${algorithm}`);
            let data = await response.json();

            // 1. ANIMATE THE SEARCH HISTORY
            // We draw the roads the algorithm checked in a light red color
            for (let roadCoords of data.search_history) {
                console.log("Drawing search step:", roadCoords[0]);
                let searchLine = L.polyline(roadCoords, {style: { color: 'red', weight: 3, opacity: 1 }}).addTo(map);
                drawnLayers.push(searchLine); 

                /*let searchLine = L.polyline(roadCoords, {
                    color: '#ff7800', 
                    weight: 2, 
                    opacity: 0.5
                }).addTo(map);*/

                // Pause for 5 milliseconds before drawing the next road.
                // (Decrease this number if the animation is too slow!)
                
                await sleep(0.5);
            };

            // 2. DRAW THE FINAL ROUTE
            // Once the animation is done, draw the winning path in thick blue
            console.log("Drawing final route:", data.final_route);
            let finalRouteLayer = L.geoJSON(data.final_route, { 
                style: { color: 'blue', weight: 6, opacity: 1 } 
            }).addTo(map);
            
            drawnLayers.push(finalRouteLayer);
            
            // Reset clicks for the next attempt
            clicks = []; 
        }
    });
}

// Initialize the map when the page loads
window.onload = initializeMap;