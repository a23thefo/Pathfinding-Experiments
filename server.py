from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmium
import networkx as nx
import math
import heapq
from scipy.spatial import KDTree

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

def dijkstra(graph, startNode, goalNode):
    searching = True
    unsearched = getNeighbors(graph, startNode)
    searched = []
    print(heapq.heappop(unsearched))
    while searching:
        searching = False
        
def getNeighbors(graph, parent):
    neighbors = []
    for n in graph.neighbors(parent):
        weight = graph[parent][n]["weight"]
        heapq.heappush(neighbors,(weight,parent,n))
    return neighbors

# --- HELPER: CALCULATE REAL-WORLD DISTANCE ---
def calculate_distance(y1, x1, y2, x2): # Latitude = y | Longitude = x
    # Calculates the distance in meters between two coordinates using the Haversine formula
    Equator = 6371000 # Earth radius in meters
    radiantsY1, radiantsY2 = math.radians(y1), math.radians(y2)
    distanceLatitude, distanceLongitude = math.radians(y2 - y1), math.radians(x2 - x1)
    a = math.sin(distanceLatitude/2)**2 + math.cos(radiantsY1)*math.cos(radiantsY2)*math.sin(distanceLongitude/2)**2
    return Equator * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# --- 1. THE OSMIUM HANDLER ---
class RoutingGraphHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.graph = nx.Graph()

    def way(self, w):
        # Only process ways (lines) that are marked as a 'highway' (OSM's tag for any road/path)
        if 'highway' in w.tags:
            # Skip things cars can't drive on (you can adjust this list later)
            if w.tags['highway'] in ['pedestrian', 'footway', 'steps', 'path']:
                return

            # A 'way' is made of multiple nodes. We connect them as edges in our graph.
            nodes = w.nodes
            for i in range(len(nodes) - 1):
                node1, node2 = nodes[i], nodes[i+1]
                
                try:
                    # Grab coordinates (requires locations=True when applying the handler)
                    y1, x1 = node1.location.lat, node1.location.lon
                    y2, x2 = node2.location.lat, node2.location.lon
                    
                    # Add nodes to graph with their coordinates
                    self.graph.add_node(node1.ref, lat=y1, lon=x1)
                    self.graph.add_node(node2.ref, lat=y2, lon=x2)
                    
                    # Calculate physical distance to use as the "weight" (cost) of the road
                    dist = calculate_distance(y1, x1, y2, x2)
                    self.graph.add_edge(node1.ref, node2.ref, weight=dist)
                except osmium.InvalidLocationError:
                    continue # Skip if node location is missing

# --- 2. BUILD THE GRAPH & KD-TREE ON STARTUP ---
print("Parsing OSM data and building graph... (This takes a moment)")
handler = RoutingGraphHandler()
# locations=True tells osmium to cache node coordinates so ways can access them
handler.apply_file("faroe-islands.osm.pbf", locations=True)
graph = handler.graph

print(f"Graph ready! Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

# Build a KD-Tree so we can quickly snap map clicks to the nearest valid road node
node_ids = list(graph.nodes)
# Scipy KDTree expects a list of [latitude, longitude] pairs
coordinates = []
for n in node_ids:
    coordinates.append([graph.nodes[n]['lat'], graph.nodes[n]['lon']])
kdtree = KDTree(coordinates)
print("Spatial index (KD-Tree) ready!")
dijkstra(graph,list(graph.nodes)[0],list(graph.nodes)[1])
# --- 3. THE ROUTING ENDPOINT ---
@app.get("/route")
def calculate_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    # 1. Snap the user's clicks to the nearest actual nodes in our graph
    _, start_idx = kdtree.query([start_lat, start_lon])
    _, end_idx = kdtree.query([end_lat, end_lon])
    
    start_node = node_ids[start_idx]
    end_node = node_ids[end_idx]

    try:
        # 2. Run NetworkX's built-in Dijkstra's shortest path algorithm
        path_node_ids = nx.shortest_path(graph, source=start_node, target=end_node, weight='weight')
        
        # 3. Convert the list of node IDs back into Lat/Lon coordinates for GeoJSON
        # Note: GeoJSON strictly expects format [longitude, latitude]
        route_coords = []
        for n in path_node_ids:
            route_coords.append([graph.nodes[n]['lon'], graph.nodes[n]['lat']])
        print(route_coords)
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            }
        }
    except nx.NetworkXNoPath:
        return {"type": "error", "message": "No route found between the selected points."}

