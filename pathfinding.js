function runBenchmark() {
    let algorithm = document.getElementById("algorithm").value;
    fetch(`http://localhost:8000/benchmark?algorithm=${algorithm}&endpoints=10&runs=100`)
        .then(response => response.json())
        .then(data => {
            console.log("Benchmark results:", data);
        });
}

function initializeMap() {
    // 1. Initialize Leaflet Map (Centered on faroe islands for this example)
    var map = L.map('map').setView([58.389924722868, 13.84619267947129], 18);

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

            if(data.error) {
                alert(data.error);
                // Clear the markers for the next attempt
                drawnLayers.forEach(layer => map.removeLayer(layer));
                drawnLayers = [];
                clicks = [];
                return;
            }

            // 1. ANIMATE THE SEARCH HISTORY
            // We draw the roads the algorithm checked in a light red color
            let sleepcounter = 0;
            let sleeptimer = 1;
            if (algorithm === "biDijkstra") {
                console.log("Drawing search history for bidirectional search:", data.search_history);
                for (let roadCoords of data.search_history["search1"]) {
                    sleepcounter++;
                    let line = `${roadCoords[0][0]},${roadCoords[0][1]} ${roadCoords[1][0]},${roadCoords[1][1]}`.split(" ").map(coord => coord.split(",").map(Number));
                    let searchLine = L.polyline(line).addTo(map);
                    searchLine.setStyle({ color: '#ff0000', weight: 5, opacity: 1 });
                    drawnLayers.push(searchLine);

                    /*let searchLine = L.polyline(roadCoords, {
                        color: '#ff7800', 
                        weight: 2, 
                        opacity: 0.5
                    }).addTo(map);*/

                    // Pause for 5 milliseconds before drawing the next road.
                    // (Decrease this number if the animation is too slow!)
                    if (sleepcounter > sleeptimer) {
                        await sleep(200);
                        sleepcounter = 0;
                        //sleeptimer = sleeptimer * 1.05;
                    }
                }
                sleepcounter = 0;
                sleeptimer = 100;
                for (let roadCoords of data.search_history["search2"]) {
                    sleepcounter++;
                    let line = `${roadCoords[0][0]},${roadCoords[0][1]} ${roadCoords[1][0]},${roadCoords[1][1]}`.split(" ").map(coord => coord.split(",").map(Number));
                    let searchLine = L.polyline(line).addTo(map);
                    searchLine.setStyle({ color: '#00ddff', weight: 5, opacity: 1 });
                    drawnLayers.push(searchLine);

                    /*let searchLine = L.polyline(roadCoords, {
                        color: '#ff7800', 
                        weight: 2, 
                        opacity: 0.5
                    }).addTo(map);*/

                    // Pause for 5 milliseconds before drawing the next road.
                    // (Decrease this number if the animation is too slow!)
                    if (sleepcounter > sleeptimer) {
                        await sleep(200);
                        sleepcounter = 0;
                        //sleeptimer = sleeptimer * 1.05;
                    }
                } 
            }else { 
                for (let roadCoords of data.search_history) {
                    sleepcounter++;
                    let line = `${roadCoords[0][0]},${roadCoords[0][1]} ${roadCoords[1][0]},${roadCoords[1][1]}`.split(" ").map(coord => coord.split(",").map(Number));
                    let searchLine = L.polyline(line).addTo(map);
                    searchLine.setStyle({ color: '#ff0000', weight: 5, opacity: 1 });
                    drawnLayers.push(searchLine); 

                    /*let searchLine = L.polyline(roadCoords, {
                        color: '#ff7800', 
                        weight: 2, 
                        opacity: 0.5
                    }).addTo(map);*/

                    // Pause for 5 milliseconds before drawing the next road.
                    // (Decrease this number if the animation is too slow!)
                    if (sleepcounter > sleeptimer) {
                        await sleep(0.5);
                        sleepcounter = 0;
                        //sleeptimer = sleeptimer * 1.05; // Gradually increase the sleep time to slow down the animation as it progresses
                    }
                };
            }

            // 2. DRAW THE FINAL ROUTE
            // Once the animation is done, draw the winning path in thick blue
            console.log("Drawing final route:", data.final_route);
            let finalRouteLayer = L.geoJSON(data.final_route, { 
                style: { color: 'blue', weight: 6, opacity: 1 } 
            }).addTo(map);
            
            drawnLayers.push(finalRouteLayer);

            if (data.checkpoints) {
                for (let roadCoords of data.checkpoints) {
                    let checkpointMarker = L.circleMarker(roadCoords, {
                        color: 'green',
                        radius: 8,
                    }).addTo(map);
                    drawnLayers.push(checkpointMarker);
                } 
            } 
            // Reset clicks for the next attempt
            clicks = []; 
        }
    });
}

// Initialize the map when the page loads
window.onload = initializeMap;