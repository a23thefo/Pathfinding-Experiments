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
    searched = [{"weight":0,"parent":None,"node":startNode}]
    searchHistory = []
    path=[]
    while searching:
        if unsearched == []:
            print("No path found")
            return []
        currentNode = heapq.heappop(unsearched)
        if currentNode[2] == goalNode:
            searching = False
            currentNode = {"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]}
            print("Found the goal node!")
            while currentNode["node"] != startNode:
                path.append(currentNode["node"])
                currentNode = [s for s in searched if s["node"] == currentNode["parent"]][0]
            print("found path")
            return path, searchHistory
        else:
            searched.append({"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]})
            print("Searching neighbors of node", currentNode[2])
            for n in getNeighbors(graph, currentNode[2], currentNode[0]):
                if n[2] not in [s["node"] for s in searched] or n[0] < [s["weight"] for s in searched if s["node"] == n[2]][0]:
                    currentNode = heapq.heappush(unsearched,n)
                    lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    searchHistory.append([[lat1, lon1], [lat2, lon2]])
        
def getNeighbors(graph, parent, currentCost=0):
    neighbors = []
    for n in graph.neighbors(parent):
        weight = graph[parent][n]["weight"]
        heapq.heappush(neighbors,(weight+currentCost,parent,n))
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
print(list(dijkstra(graph,list(graph.nodes)[0],list(graph.nodes)[10])))
# --- 3. THE ROUTING ENDPOINT ---
@app.get("/route")
def calculate_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    # 1. Snap the user's clicks to the nearest actual nodes in our graph
    _, start_idx = kdtree.query([start_lat, start_lon])
    _, end_idx = kdtree.query([end_lat, end_lon])
    
    start_node = node_ids[start_idx]
    end_node = node_ids[end_idx]
    # Unpack the two returned variables
    path_node_ids, search_history = dijkstra(graph, start_node, end_node)
    
    if not path_node_ids:
        return {"error": "No path found"}

    route_coords = [[graph.nodes[n]['lon'], graph.nodes[n]['lat']] for n in path_node_ids]

    # Return a custom JSON object containing both pieces of data
    return {
        "final_route": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            }
        },
        "search_history": search_history # Send the history to the frontend!
    }

