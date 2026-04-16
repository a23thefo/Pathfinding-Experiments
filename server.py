import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmium
import networkx as nx
import math
import heapq
import requests
from scipy.spatial import KDTree

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

def dijkstra(graph, startNode, goalNode):
    searching = True
    unsearched = getNeighbors(graph, startNode)
    searched = [{"weight":0,"parent":None,"node":startNode}]
    searchHistory = []
    path=[]
    while searching: ## While searching is true
        if unsearched == []: ## if unsearched is empty there is no path
            print("No path found")
            return []
        currentNode = heapq.heappop(unsearched) ## get the node with the lowest weight
        if currentNode[2] == goalNode:          ## if the current node is the goal we are done
            searching = False
            currentNode = {"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]}
            print("Found the goal node!")
            while currentNode["node"] != startNode: ## backtrack the path by getting the parent nodes.
                path.append(currentNode["node"])
                currentNode = [s for s in searched if s["node"] == currentNode["parent"]][0]
            print("found path")
            return path, searchHistory
        else:
            searched.append({"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]}) ## put away the searched node
            neighbors = getNeighbors(graph, currentNode[2], currentNode[0], None, "dijkstra") ## get the neighbors of the current node
            for n in searched:
                for neighbor in neighbors:
                    if neighbor[2] == n["node"] and neighbor[0] >= n["weight"]: ## if the neighbor is in searched and has a higher weight than the searched node we can ignore it
                        neighbors.remove(neighbor)
            for n in neighbors: ## for each neighbor
                currentNode = heapq.heappush(unsearched,n)
                lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                searchHistory.append([[lat1, lon1], [lat2, lon2]])

def biDijkstra(graph, startNode, goalNode):
    searching = True
    unsearchedSearch1 = getNeighbors(graph, startNode)
    unsearchedSearch2 = getNeighbors(graph, goalNode)
    searched1 = [{"weight":0,"parent":None,"node":startNode}]
    searched1Visited = dict()
    searched2Visited = dict()
    searched2 = [{"weight":0,"parent":None,"node":goalNode}]
    bestPath = float("inf")
    bestPathNode = None
    pathsFound = 0
    searchHistory = {"search1": [], "search2": []}
    while searching: ## While searching is true
        if unsearchedSearch1 == [] or unsearchedSearch2 == []: ## if unsearched is empty there is no path
            print("No path found")
            searching = False
            return [], searchHistory
        currentNodeSearch1 = heapq.heappop(unsearchedSearch1) ## get the node with the lowest weight
        currentNodeSearch2 = heapq.heappop(unsearchedSearch2) ## get the node with the lowest weight
        neighbor1, neighbor2 = None, None

        searched1Visited[currentNodeSearch1[2]] = currentNodeSearch1[0]   
        searched1.append({"weight":currentNodeSearch1[0],"parent":currentNodeSearch1[1],"node":currentNodeSearch1[2]}) ## put away the searched node
        neighbor1 = getNeighbors(graph, currentNodeSearch1[2], currentNodeSearch1[0], None, "dijkstra")
        searched1, bestPath, bestPathFound, bestPathNode, pathsFound = pathfinderBiDjikstra(searched2Visited.get(currentNodeSearch1[2]), currentNodeSearch1, searched1, bestPath, bestPathNode, pathsFound)
        if bestPathFound:
            searching = False
            print("Found the goal node!")
            return pathRenderBiDjikstra(searched1, searched2, bestPathNode, startNode, goalNode), searchHistory
        tempNeighbor1 = neighbor1.copy() if neighbor1 else None
        if(neighbor1):
            for neighbor in neighbor1:
                if searched1Visited.get(neighbor[2]) is not None and neighbor[0] >= searched1Visited.get(neighbor[2]):
                    tempNeighbor1.remove(neighbor)
        if(tempNeighbor1):
            for n in tempNeighbor1: ## for each neighbor                    
                heapq.heappush(unsearchedSearch1,n)
                lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                searchHistory["search1"].append([[lat1, lon1], [lat2, lon2]])
        
        searched2.append({"weight":currentNodeSearch2[0],"parent":currentNodeSearch2[1],"node":currentNodeSearch2[2]}) ## put away the searched node
        searched2Visited[currentNodeSearch2[2]] = currentNodeSearch2[0]   
        neighbor2 = getNeighbors(graph, currentNodeSearch2[2], currentNodeSearch2[0], None, "dijkstra") ## get the neighbors of the current node    
        searched2, bestPath, bestPathFound, bestPathNode, pathsFound = pathfinderBiDjikstra(searched1Visited.get(currentNodeSearch2[2]), currentNodeSearch2, searched2, bestPath, bestPathNode, pathsFound)
        if bestPathFound:
            searching = False
            print("Found the goal node!")
            return pathRenderBiDjikstra(searched1, searched2, bestPathNode, startNode, goalNode), searchHistory
        tempNeighbor2 = neighbor2.copy() if neighbor2 else None
        if(neighbor2):
            for neighbor in neighbor2:
                if searched2Visited.get(neighbor[2]) is not None and neighbor[0] >= searched2Visited[neighbor[2]]: ## if the neighbor is in searched and has a higher weight than the searched node we can ignore it
                    tempNeighbor2.remove(neighbor)
                    continue
                for n in unsearchedSearch2:
                    if neighbor[2] == n[2] and neighbor[0] >= n[0]: ## if the neighbor is in unsearched and has a higher weight than the unsearched node we can ignore it
                        tempNeighbor2.remove(neighbor)
                        break
        if(tempNeighbor2):
            for n in tempNeighbor2: ## for each neighbor         
                print("adding neighbor: ", n)        
                heapq.heappush(unsearchedSearch2,n)
                lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                searchHistory["search2"].append([[lat1, lon1], [lat2, lon2]])

def pathfinderBiDjikstra(node, currentNode, searchedList, bestPath, bestPathNode, pathsFound=0):
    bestPathFound = False
    print("current node: ", currentNode, "node in other search: ", node)
    if node: ## if the current node is in the other search we have found a path
        ##os.system('clear')
        pathsFound += 1
        print("Paths found so far: ", pathsFound, "Current best path: ", bestPath, "km")
        if node + currentNode[0] < bestPath: ## if the path we have found is better than the best path we have found so far we update the best path
            searchedList.append({"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]})
            bestPath = node + currentNode[0]
            bestPathNode = currentNode
        elif node + currentNode[0] > bestPath: ## if the path we have found is equal to the best path we have found so far we can choose either one as the best path
            bestPathFound = True
    return searchedList, bestPath, bestPathFound, bestPathNode, pathsFound

def pathRenderBiDjikstra(searched1, searched2, bestPathNode, startNode, goalNode):
    path = []
    currentNode1, currentNode2 = None, None
    for s in searched1:
        if bestPathNode[2] == s["node"]:
            currentNode1 = s
    for s in searched2:
        if bestPathNode[2] == s["node"]:
            currentNode2 = s
    print(currentNode1, currentNode2)
    while currentNode1["node"] != startNode: ## backtrack the path by getting the parent nodes.
        path.append(currentNode1["node"])
        currentNode1 = [s for s in searched1 if s["node"] == currentNode1["parent"]][0]
    path.reverse()
    while currentNode2["node"] != goalNode: ## backtrack the path by getting the parent nodes.
        path.append(currentNode2["node"])
        currentNode2 = [s for s in searched2 if s["node"] == currentNode2["parent"]][0]
    print("found path")
    return path 



def aStar(graph, startNode, goalNode):
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
            neighbors = getNeighbors(graph, currentNode[2], currentNode[0], goalNode, "aStar") ## get the neighbors of the current node
            for n in searched:
                for neighbor in neighbors:
                    if neighbor[2] == n["node"] and neighbor[0] >= n["weight"]: ## if the neighbor is in searched and has a higher weight than the searched node we can ignore it
                        neighbors.remove(neighbor)
            for n in neighbors: ## for each neighbor                    
                    currentNode = heapq.heappush(unsearched,n)
                    lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    searchHistory.append([[lat1, lon1], [lat2, lon2]])

def greedBestFirst(graph, startNode, goalNode):
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
            neighbors = getNeighbors(graph, currentNode[2], 0, goalNode, "aStar") ## get the neighbors of the current node
            for n in searched:
                for neighbor in neighbors:
                    if neighbor[2] == n["node"] and neighbor[0] >= n["weight"]: ## if the neighbor is in searched and has a higher weight than the searched node we can ignore it
                        neighbors.remove(neighbor)
            for n in neighbors: ## for each neighbor                    
                    currentNode = heapq.heappush(unsearched,n)
                    lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                    searchHistory.append([[lat1, lon1], [lat2, lon2]])

async def LLMAStar(graph, startNode, goalNode):
    print("we in")
    url = "http://127.0.0.1:1234/api/v1/chat"
    data = {
        "model": "llama-2-13b-chat", "input": f"Using these nodes for routing {graph.nodes} find a path from {startNode} to {goalNode}", "context_length": 16000
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer sk-lm-NiFOETAj:og35tLR1RpwDZdHaB52p"}
    response = requests.post(url, json=data, headers=headers)
    print("LLM response:", response.json())
    # This is a placeholder for the LLM-augmented A* algorithm. You can implement it similarly to the regular A* but with an additional heuristic component that queries an LLM for guidance.
    return [], []

def getNeighbors(graph, parent, currentCost=0, goalNode=None, heuristic=None):
    neighbors = []
    weight = 0
    for n in graph.neighbors(parent):
        if heuristic != "bestFirst":
            weight = calculate_distance(graph.nodes[n]['lat'], graph.nodes[n]['lon'], graph.nodes[parent]['lat'], graph.nodes[parent]['lon'])
        else:
            weight = calculate_distance(graph.nodes[n]['lat'], graph.nodes[n]['lon'], graph.nodes[goalNode]['lat'], graph.nodes[goalNode]['lon'])
        if heuristic == "aStar":  
            weight += calculate_distance(graph.nodes[n]['lat'], graph.nodes[n]['lon'], graph.nodes[goalNode]['lat'], graph.nodes[goalNode]['lon'])
        heapq.heappush(neighbors,(weight+currentCost,parent,n))
    return neighbors

# --- HELPER: CALCULATE REAL-WORLD DISTANCE ---
def calculate_distance(y1, x1, y2, x2): # Latitude = y | Longitude = x
    # Calculates the distance in meters between two coordinates using the Haversine formula
    Equator = 6371000 # Earth radius in meters
    radiantsY1, radiantsY2 = math.radians(y1), math.radians(y2)
    distanceLatitude, distanceLongitude = math.radians(y2 - y1), math.radians(x2 - x1)
    a = math.sin(distanceLatitude/2)**2 + math.cos(radiantsY1)*math.cos(radiantsY2)*math.sin(distanceLongitude/2)**2
    return (Equator * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))))/1000 # Return distance in kilometers

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

# Build a KD-Tree so we can quickly snap map clicks to the nearest valid road node
node_ids = list(graph.nodes)
# Scipy KDTree expects a list of [latitude, longitude] pairs
coordinates = []
for n in node_ids:
    coordinates.append([graph.nodes[n]['lat'], graph.nodes[n]['lon']])
kdtree = KDTree(coordinates)
print("Spatial index (KD-Tree) ready!")
# --- 3. THE ROUTING ENDPOINT ---
@app.get("/route")
async def calculate_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, algorithm: str = "aStar"):
    all_variables = dir()

    # Iterate over the whole list where dir( )
    # is stored.
    for name in all_variables:
        # Print the item if it doesn't start with '__'
        if not name.startswith('__'):
            myvalue = eval(name)
            print(name, "is", type(myvalue), "and is equal to ", myvalue)
    # 1. Snap the user's clicks to the nearest actual nodes in our graph
    _, start_idx = kdtree.query([start_lat, start_lon])
    _, end_idx = kdtree.query([end_lat, end_lon])
    
    start_node = node_ids[start_idx]
    end_node = node_ids[end_idx]
    # Unpack the two returned variables
    if(algorithm == "LLMAStar"):
        path_node_ids, search_history = await LLMAStar(graph, start_node, end_node)
    else:
        path_node_ids, search_history = eval(algorithm)(graph, start_node, end_node)

    if path_node_ids == []:
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

