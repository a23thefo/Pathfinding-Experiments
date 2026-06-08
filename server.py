from datetime import datetime
import os
from random import random, seed

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import osmium
import networkx as nx
import math
import heapq
import requests
import time
import psutil
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
            return [], searchHistory, len(searched1Visited)+len(searched2Visited)
        currentNodeSearch1 = heapq.heappop(unsearchedSearch1) ## get the node with the lowest weight
        currentNodeSearch2 = heapq.heappop(unsearchedSearch2) ## get the node with the lowest weight
        neighbor1, neighbor2 = None, None

        searched1Visited[currentNodeSearch1[2]] = currentNodeSearch1[0]   
        searched1.append({"weight":currentNodeSearch1[0],"parent":currentNodeSearch1[1],"node":currentNodeSearch1[2]}) ## put away the searched node
        neighbor1 = getNeighbors(graph, currentNodeSearch1[2], currentNodeSearch1[0], None, "dijkstra")
        searched1, bestPath, bestPathFound, bestPathNode, pathsFound = pathfinderBiDjikstra(searched2Visited.get(currentNodeSearch1[2]), currentNodeSearch1, searched1, bestPath, bestPathNode, pathsFound)
        if bestPathFound:
            searching = False
            return pathRenderBiDjikstra(searched1, searched2, bestPathNode, startNode, goalNode), searchHistory, len(searched1Visited)+len(searched2Visited)
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
            return pathRenderBiDjikstra(searched1, searched2, bestPathNode, startNode, goalNode), searchHistory, len(searched1Visited)+len(searched2Visited)
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
                heapq.heappush(unsearchedSearch2,n)
                lat1, lon1 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                lat2, lon2 = graph.nodes[n[2]]['lat'], graph.nodes[n[2]]['lon']
                searchHistory["search2"].append([[lat1, lon1], [lat2, lon2]])

def pathfinderBiDjikstra(node, currentNode, searchedList, bestPath, bestPathNode, pathsFound=0):
    bestPathFound = False
    if node: ## if the current node is in the other search we have found a path
        ##os.system('clear')
        pathsFound += 1
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
    while currentNode1["node"] != startNode: ## backtrack the path by getting the parent nodes.
        path.append(currentNode1["node"])
        currentNode1 = [s for s in searched1 if s["node"] == currentNode1["parent"]][0]
    path.reverse()
    while currentNode2["node"] != goalNode: ## backtrack the path by getting the parent nodes.
        path.append(currentNode2["node"])
        currentNode2 = [s for s in searched2 if s["node"] == currentNode2["parent"]][0]
    return path 



def aStar(graph, startNode, goalNode):
    searching = True
    unsearched = getNeighbors(graph, startNode)
    searched = [{"weight":0,"parent":None,"node":startNode}]
    visited = dict()
    searchHistory = []
    path=[]
    while searching:
        if unsearched == []:
            print("No path found")
            return [], searchHistory ,len(searched)
        currentNode = heapq.heappop(unsearched)
        if currentNode[2] == goalNode:
            searching = False
            currentNode = {"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]}
            searchHistory.append([[graph.nodes[currentNode["node"]]['lat'], graph.nodes[currentNode["node"]]['lon']], [graph.nodes[currentNode["parent"]]['lat'], graph.nodes[currentNode["parent"]]['lon']]])
            searched.append(currentNode)
            while currentNode["node"] != startNode:
                path.append(currentNode["node"])
                currentNode = [s for s in searched if s["node"] == currentNode["parent"]][0]
            return path[::-1], searchHistory, len(searched)
        else:
            searched.append({"weight":currentNode[0],"parent":currentNode[1],"node":currentNode[2]})
            visited[currentNode[2]] = currentNode[0]
            neighbors = getNeighbors(graph, currentNode[2], currentNode[0], goalNode, "aStar") ## get the neighbors of the current node
            tempNeighbors = neighbors.copy()
            for neighbor in tempNeighbors:
                if visited.get(neighbor[2]) is not None and neighbor[0] >= visited[neighbor[2]]: ## if the neighbor is in searched and has a higher weight than the searched node we can ignore it
                    neighbors.remove(neighbor)
            for n in neighbors: ## for each neighbor                    
                    heapq.heappush(unsearched,n)
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
            return [], searchHistory, len(searched)
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

async def LLMAStar(graph, startNode, goalNode, nodes, edges, key, removedFromSimplified):
    invalidCheckpoints = 0
    nodes.append(graph.nodes[startNode])
    nodes.append(graph.nodes[goalNode])
    key[startNode] = len(nodes)-2
    key[goalNode] = len(nodes)-1
    if startNode in removedFromSimplified:
        removedFromSimplified.remove(startNode)
    if goalNode in removedFromSimplified:
        removedFromSimplified.remove(goalNode)
    for n in getNeighbors(graph, startNode):
        if(n[2] in removedFromSimplified):
            newEdge = compress_edge(startNode, n[2], removedFromSimplified, graph, key)
            if newEdge:
                edges.append(newEdge)
        else:
            edges.append([key.get(startNode), key.get(n[2])])
    for n in getNeighbors(graph, goalNode):
        if(n[2] in removedFromSimplified):
            newEdge = compress_edge(goalNode, n[2], removedFromSimplified, graph, key)
            if newEdge:
                edges.append(newEdge)
        else:
            edges.append([key.get(goalNode), key.get(n[2])])

    url = "http://127.0.0.1:1234/api/v1/chat"
    data = {
        "model": "meta-llama-3.1-8b-instruct", 
        "input": f"""
        You are an expert pathfinding AI. Your task is to find a list of nodes that 100% are apart of the shortest path between two nodes. Like a list of checkpoints.
        Data Context: Here is the graph data you will use.
        * Nodes: This list contains the coordinates for each node. The index of the coordinate in this list represents the Node ID (starting at 0).
        * Paths: This list contains pairs of connected Node IDs. You can ONLY travel between nodes if their IDs appear together in one of these pairs.
        Nodes: {nodes}
        Paths: {edges}
        Task: Find a list of checkpoints from {key.get(startNode)} to {key.get(goalNode)}.
        Instructions:
        1. Think Step-by-Step: First, look at the starting node. Search the Paths list for any pairs containing that node to see your available next steps.
        2. Explain Your Reasoning: Describe your search process and how you arrive at each conclusion before giving the final answer.
        3. Final Output Format: At the very end of your response, output the final path as a strict Python list of Node IDs in order.
        4. Examples of Output format: 
            * Example 1: Path from node 10 to node 34 = [10, 1, 2, 34]
            * Example 2: Path from node 2 to node 81 = [2, 1, 10, 9, 62, 81]
            * Example 3: Path from node 55 to node 54 = [] Beacause there is no path between these two nodes.
            * Example 4: Path from node 3 to node 1 = [3, 4, 5, 6, 51, 2, 1]
            * Example 5: Path from node 67 to node 69 = [67, 18, 28, 29, 69]
        """, "context_length": 4000
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer sk-lm-NiFOETAj:og35tLR1RpwDZdHaB52p"}
    response = requests.post(url, json=data, headers=headers)
    try:
        if response.json().get("error"):
            print("LLM Error: ", response.json().get("error").get("message"))
            return [], [], 0, []
    except:
        pass
    check = response.json().get("output")[0].get("content").split("[")[-1].split("]")[0].rsplit(",")
    checkpoints = [int(x.strip()) for x in check if x.strip().isdigit()]
    checks = []
    checkpointCords = []

    for c in checkpoints:
        if c not in key.values():
            print("Invalid checkpoint from LLM, not in graph: ", c)
            invalidCheckpoints += 1
            continue
        for idNode in key:
            if key[idNode] == c and idNode not in [startNode, goalNode]:
                checks.append(idNode)
    for c in checks:
        checkpointCords.append([graph.nodes[c]['lat'], graph.nodes[c]['lon']])
    checks.append(goalNode)
    path = [startNode]
    history = []
    searched = 0
    for c in checks:
        if c == goalNode:
            pathTemp, historyTemp, searchedTemp = aStar(graph, path[-1], goalNode)
            if pathTemp == []:
                print("LLM Checkpoint is not actually on the path: ", c)
                invalidCheckpoints += 1
                return [], [], searched+searchedTemp, checkpointCords
            for h in pathTemp:
                path.append(h)
            for h in historyTemp:
                history.append(h)
            searched += searchedTemp
        else:
            pathTemp, historyTemp, searchedTemp = aStar(graph, path[-1], c)
            if pathTemp == []:
                print("LLM Checkpoint is not actually on the path: ", c)
                invalidCheckpoints += 1
                return [], [], searched+searchedTemp, checkpointCords
            for h in pathTemp:
                path.append(h)
            for h in historyTemp:
                history.append(h)
            searched += searchedTemp
    return path, history, searched, checkpointCords

def getNeighbors(graph, parent, currentCost=0, goalNode=None, heuristic=None):
    neighbors = []
    weight = 0
    for n in graph.neighbors(parent):
        if heuristic != "bestFirst":
            weight = calculate_distance(graph.nodes[n]['lat'], graph.nodes[n]['lon'], graph.nodes[parent]['lat'], graph.nodes[parent]['lon'])
        if goalNode is not None:
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

def compress_data(graph, nodes, edges):
    simplified_nodes = []
    removed_nodes = set()
    nodesKey = dict()
    simplified_edges = []
    newId = 0
    for n in nodes:
        neighbors = getNeighbors(graph, n)
        if len(neighbors) == 2: # If the node has exactly 2 neighbors, we can skip it and connect its neighbors directly
            removed_nodes.add(n)
            continue
        nodesKey[n] = newId
        simplified_nodes.append([round(nodes[n]['lat'], 3), round(nodes[n]['lon'], 3)])# Round to 5 decimal places (~1.1m precision)
        newId += 1
    for u in edges:
        if u[0] in removed_nodes or u[1] in removed_nodes:
            compressed_edge = compress_edge(u[0], u[1], removed_nodes, graph, nodesKey)
            if compressed_edge:
                simplified_edges.append(compressed_edge)
        else:
            simplified_edges.append([nodesKey.get(u[0]), nodesKey.get(u[1])])
    return simplified_nodes, simplified_edges, nodesKey, removed_nodes

def compress_edge(node1, node2, removed_nodes, graph, nodesKey):
    checked_nodes = []
    currentNode1, currentNode2 = node1, node2
    validNode1, validNode2 = None, None
    while validNode1 is None or validNode2 is None:
        checked_nodes.append(currentNode1)
        checked_nodes.append(currentNode2)  
        if currentNode1 in removed_nodes:
            n = getNeighbors(graph, currentNode1)
            old = currentNode1
            for neighbor in n:
                if neighbor[2] != currentNode1 and neighbor[2] not in checked_nodes:
                    currentNode1 = neighbor[2]
                    break
            if old == currentNode1: # If we looped back to the same node, it means we can't find a valid node in this direction
                print("Couldn't find valid node for edge: ", node1, node2)
                print("Checked nodes: ", checked_nodes)
                break
        else:
            validNode1 = currentNode1
        if currentNode2 in removed_nodes:
            n = getNeighbors(graph, currentNode2)
            old = currentNode2
            for neighbor in n:
                if neighbor[2] != currentNode2 and neighbor[2] not in checked_nodes:
                    currentNode2 = neighbor[2]
                    break
            if old == currentNode2: # If we looped back to the same node, it means we can't find a valid node in this direction
                print("Couldn't find valid node for edge: ", node1, node2)
                break
        else:
            validNode2 = currentNode2
    if validNode1 is not None and validNode2 is not None:
        return [nodesKey.get(validNode1), nodesKey.get(validNode2)]

# --- 2. BUILD THE GRAPH & KD-TREE ON STARTUP ---
print("Parsing OSM data and building graph... (This takes a moment)")
handler = RoutingGraphHandler()
# locations=True tells osmium to cache node coordinates so ways can access them
handler.apply_file("map.osm", locations=True)
graph = handler.graph

# Build a KD-Tree so we can quickly snap map clicks to the nearest valid road node
node_ids = list(graph.nodes)
# Scipy KDTree expects a list of [latitude, longitude] pairs
coordinates = []
for n in node_ids:
    coordinates.append([graph.nodes[n]['lat'], graph.nodes[n]['lon']])
kdtree = KDTree(coordinates)
print("Spatial index (KD-Tree) ready!")
simplified_nodes, simplified_edges, nodesKey, removedFromSimplified = compress_data(graph, graph.nodes, graph.edges)

@app.get("/benchmark")
async def benchmark(algorithm: str = "biDijkstra", endpoints: int = 1, runs: int = 1):
    data = ""
    print(f"Running benchmark for {algorithm} with {endpoints} endpoints and {runs} runs each...")
    for i in range(runs):
        seed(42)
        for _ in range(endpoints):
            start_idx = int(random() * len(node_ids))
            end_idx = int(random() * len(node_ids))
            start_node = node_ids[start_idx]
            end_node = node_ids[end_idx]
            checkpoints = []
            ram = psutil.virtual_memory()
            start_ram = ram.percent
            start_cpu = psutil.cpu_percent(interval=1)
            start_time = time.perf_counter()
            if algorithm == "LLMAStar":
                path_node_ids, search_history, visited_nodes, checkpoints = await LLMAStar(graph, start_node, end_node, simplified_nodes.copy(), simplified_edges.copy(), nodesKey, removedFromSimplified.copy())
            else:
                path_node_ids, search_history, visited_nodes = eval(algorithm)(graph, start_node, end_node)
            end_time = time.perf_counter()
            end_ram = ram.percent
            end_cpu = psutil.cpu_percent(interval=1)
            time_taken = end_time - start_time
            birdDistance = calculate_distance(graph.nodes[start_node]['lat'], graph.nodes[start_node]['lon'], graph.nodes[end_node]['lat'], graph.nodes[end_node]['lon'])  
            pathLength = 0
            for j in range(len(path_node_ids)-1):
                pathLength += calculate_distance(graph.nodes[path_node_ids[j]]['lat'], graph.nodes[path_node_ids[j]]['lon'], graph.nodes[path_node_ids[j+1]]['lat'], graph.nodes[path_node_ids[j+1]]['lon'])

            if (path_node_ids == []):
                data += f"{i+1}:{time_taken:.5f}:{visited_nodes}:{start_ram}:{end_ram}:{start_cpu}:{end_cpu}:{start_node}:{end_node}:{birdDistance}:{pathLength}:{checkpoints}:NoPath \n "
            else:
                data += f"{i+1}:{time_taken:.5f}:{visited_nodes}:{start_ram}:{end_ram}:{start_cpu}:{end_cpu}:{start_node}:{end_node}:{birdDistance}:{pathLength}:{checkpoints}:PathFound \n "
        print(f"Run {i+1}/{runs} for {algorithm} completed.")
    print(data)
    x = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    f = open(f"benchmark_results_{algorithm}_{x}.txt", "x")
    f.write(data)
    f.close()
    return {"message": "Benchmark endpoint", "data": data}

# --- 3. THE ROUTING ENDPOINT ---
@app.get("/route")
async def calculate_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, algorithm: str = "aStar"):
    # 1. Snap the user's clicks to the nearest actual nodes in our graph
    _, start_idx = kdtree.query([start_lat, start_lon])
    _, end_idx = kdtree.query([end_lat, end_lon])
    
    start_node = node_ids[start_idx]
    end_node = node_ids[end_idx]

    visited_nodes = 0

    start_time = time.perf_counter()
    checkpoints = []

    # Unpack the two returned variables
    if(algorithm == "LLMAStar"):
        path_node_ids, search_history, visited_nodes, checkpoints = await LLMAStar(graph, start_node, end_node, simplified_nodes.copy(), simplified_edges.copy(), nodesKey, removedFromSimplified.copy())
    else:
        path_node_ids, search_history, visited_nodes = eval(algorithm)(graph, start_node, end_node)
    
    end_time = time.perf_counter()

    if ((end_time - start_time) > 60 ):
        print((end_time - start_time)/60,"minutes ,", visited_nodes)
    else:
        print(end_time - start_time, ",", visited_nodes)

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
        "search_history": search_history, # Send the history to the frontend!
        "checkpoints": checkpoints
    }

