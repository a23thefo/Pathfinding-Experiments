from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmium
import networkx as nx
import math
from scipy.spatial import KDTree

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

# --- HELPER: CALCULATE REAL-WORLD DISTANCE ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates the distance in meters between two coordinates using the Haversine formula."""
    R = 6371000 # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

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
                n1, n2 = nodes[i], nodes[i+1]
                
                try:
                    # Grab coordinates (requires locations=True when applying the handler)
                    lat1, lon1 = n1.location.lat, n1.location.lon
                    lat2, lon2 = n2.location.lat, n2.location.lon
                    
                    # Add nodes to graph with their coordinates
                    self.graph.add_node(n1.ref, lat=lat1, lon=lon1)
                    self.graph.add_node(n2.ref, lat=lat2, lon=lon2)
                    
                    # Calculate physical distance to use as the "weight" (cost) of the road
                    dist = calculate_distance(lat1, lon1, lat2, lon2)
                    self.graph.add_edge(n1.ref, n2.ref, weight=dist)
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
coordinates = [[graph.nodes[n]['lat'], graph.nodes[n]['lon']] for n in node_ids]
kdtree = KDTree(coordinates)
print("Spatial index (KD-Tree) ready!")


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
        route_coords = [[graph.nodes[n]['lon'], graph.nodes[n]['lat']] for n in path_node_ids]

        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            }
        }
    except nx.NetworkXNoPath:
        return {"error": "No path could be found between those points."}