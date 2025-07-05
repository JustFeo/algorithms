import heapq
import networkx as nx
import osmnx as ox # For heuristic distance

# Heuristic function for A*
def heuristic_distance(graph, node1_id, node2_id):
    # Ensure nodes exist in graph before accessing them
    if node1_id not in graph.nodes or node2_id not in graph.nodes:
        # Or handle as an error, for now, return a non-informative heuristic
        return 0

    node1 = graph.nodes[node1_id]
    node2 = graph.nodes[node2_id]

    if 'x' in node1 and 'y' in node1 and 'x' in node2 and 'y' in node2:
        # Projected coordinates: use Euclidean distance
        return ((node1['x'] - node2['x'])**2 + (node1['y'] - node2['y'])**2)**0.5
    elif 'lon' in node1 and 'lat' in node1 and 'lon' in node2 and 'lat' in node2:
        # Geographic coordinates: use great-circle distance
        return ox.distance.great_circle(node1['lat'], node1['lon'], node2['lat'], node2['lon'])
    # Fallback if coordinates are not available
    return 0

def dijkstra(graph, start_node, end_node, weight='travel_time'):
    if start_node not in graph or end_node not in graph:
        # print(f"Error: Start node {start_node} or end node {end_node} not in graph.")
        return None, float('inf')

    # Priority queue: (cost, current_node, path_to_current_node)
    pq = [(0, start_node, [start_node])]

    visited_costs = {node: float('inf') for node in graph.nodes()}
    visited_costs[start_node] = 0

    while pq:
        current_cost, current_node, path = heapq.heappop(pq)

        if current_cost > visited_costs[current_node]:
            continue

        if current_node == end_node:
            return path, current_cost

        if current_node not in graph: continue # Should not happen if graph is well-formed

        for neighbor in graph.neighbors(current_node):
            min_edge_weight = float('inf')
            edge_datas = graph.get_edge_data(current_node, neighbor)
            if not edge_datas: continue

            for edge_key in edge_datas:
                edge_data = edge_datas[edge_key]
                # Ensure weight is present and numeric before using it
                if weight in edge_data and isinstance(edge_data[weight], (int, float)):
                    min_edge_weight = min(min_edge_weight, edge_data[weight])

            if min_edge_weight == float('inf'):
                # print(f"Warning: No valid edge with weight '{weight}' from {current_node} to {neighbor}")
                continue

            new_cost = current_cost + min_edge_weight
            if new_cost < visited_costs[neighbor]:
                visited_costs[neighbor] = new_cost
                new_path = path + [neighbor]
                heapq.heappush(pq, (new_cost, neighbor, new_path))

    return None, float('inf')

def a_star(graph, start_node, end_node, weight='travel_time', heuristic_func=heuristic_distance):
    if start_node not in graph or end_node not in graph:
        # print(f"Error: Start node {start_node} or end node {end_node} not in graph.")
        return None, float('inf')

    g_scores = {node: float('inf') for node in graph.nodes()}
    g_scores[start_node] = 0

    h_start = heuristic_func(graph, start_node, end_node)
    pq = [(g_scores[start_node] + h_start, g_scores[start_node], start_node, [start_node])]

    while pq:
        f_score_val, current_g_score, current_node, path = heapq.heappop(pq)

        if current_g_score > g_scores[current_node]: # Check if we found a shorter path already
            continue

        if current_node == end_node:
            return path, current_g_score

        if current_node not in graph: continue

        for neighbor in graph.neighbors(current_node):
            min_edge_weight = float('inf')
            edge_datas = graph.get_edge_data(current_node, neighbor)
            if not edge_datas: continue

            for edge_key in edge_datas:
                edge_data = edge_datas[edge_key]
                if weight in edge_data and isinstance(edge_data[weight], (int, float)):
                    min_edge_weight = min(min_edge_weight, edge_data[weight])

            if min_edge_weight == float('inf'): continue

            tentative_g_score = current_g_score + min_edge_weight
            if tentative_g_score < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g_score
                h_neighbor = heuristic_func(graph, neighbor, end_node)
                new_f_score = tentative_g_score + h_neighbor
                new_path = path + [neighbor]
                heapq.heappush(pq, (new_f_score, tentative_g_score, neighbor, new_path))

    return None, float('inf')


def bidirectional_bfs(graph, start_node, end_node):
    if start_node not in graph or end_node not in graph:
        return None
    if start_node == end_node:
        return [start_node]

    q_fwd = [(start_node, [start_node])]
    visited_fwd = {start_node: [start_node]}

    q_bwd = [(end_node, [end_node])]
    visited_bwd = {end_node: [end_node]}

    meeting_node = None

    while q_fwd and q_bwd:
        # Forward step
        if q_fwd: # Ensure queue is not empty
            curr_fwd, path_fwd = q_fwd.pop(0)
            for neighbor in graph.neighbors(curr_fwd):
                if neighbor not in visited_fwd:
                    new_path_fwd = path_fwd + [neighbor]
                    visited_fwd[neighbor] = new_path_fwd
                    q_fwd.append((neighbor, new_path_fwd))
                    if neighbor in visited_bwd:
                        meeting_node = neighbor
                        break
                # If already visited_fwd, but now also in visited_bwd (should be caught by neighbor in visited_bwd)
                # This case is implicitly handled if neighbor was already processed by backward search.
            if meeting_node: break

        # Backward step
        if q_bwd: # Ensure queue is not empty
            curr_bwd, path_bwd_rev = q_bwd.pop(0)
            # For DiGraph/MultiDiGraph, predecessors gives incoming neighbors
            for predecessor in graph.predecessors(curr_bwd):
                if predecessor not in visited_bwd:
                    new_path_bwd_rev = path_bwd_rev + [predecessor]
                    visited_bwd[predecessor] = new_path_bwd_rev
                    q_bwd.append((predecessor, new_path_bwd_rev))
                    if predecessor in visited_fwd:
                        meeting_node = predecessor
                        break
            if meeting_node: break

    if meeting_node:
        path1 = visited_fwd[meeting_node]
        path2_rev = visited_bwd[meeting_node] # This path is from end_node to meeting_node
        # path1 is start_node...meeting_node
        # path2_rev is end_node...meeting_node
        # So, path1 + path2_rev.reverse()[1:]
        return path1 + path2_rev[::-1][1:]

    return None


if __name__ == '__main__':
    print("Pathfinding algorithms implemented (Dijkstra, A*, Bidirectional BFS).")
    print("To test, load a graph (e.g., from tudelft_campus_graph.graphml) and building_node_map.json.")

    # Example test (requires files from build_graph.py to exist)
    # try:
    #     G_campus = ox.load_graphml("campus_graph/tudelft_campus_graph.graphml")
    #     import json
    #     with open("campus_graph/building_node_map.json", "r") as f:
    #         building_nodes = json.load(f)

    #     aula_node = building_nodes.get("Aula")
    #     # EEMCS might not be found. If so, pick another node for testing.
    #     eemcs_node = building_nodes.get("EEMCS")

    #     start_node_id = aula_node
    #     end_node_id = eemcs_node

    #     if not start_node_id:
    #         print("Aula node not found in map. Cannot run specific test.")
    #         if G_campus.nodes: start_node_id = list(G_campus.nodes())[0] # Fallback

    #     if not end_node_id:
    #         print("EEMCS node not found in map. Using an arbitrary graph node for testing pathfinding.")
    #         if G_campus.nodes and len(list(G_campus.nodes())) > 100:
    #             end_node_id = list(G_campus.nodes())[100]
    #         elif G_campus.nodes and len(list(G_campus.nodes())) > 1:
    #              end_node_id = list(G_campus.nodes())[1]
    #         else:
    #             end_node_id = None


    #     if start_node_id and end_node_id and start_node_id != end_node_id:
    #         print(f"\nTesting with Start: {start_node_id}, End: {end_node_id}")

    #         path_d, cost_d = dijkstra(G_campus, start_node_id, end_node_id, weight='travel_time')
    #         if path_d: print(f"Dijkstra: Path found with {len(path_d)} nodes, Cost={cost_d:.2f}")
    #         else: print(f"Dijkstra: No path found. Cost={cost_d}")

    #         path_a, cost_a = a_star(G_campus, start_node_id, end_node_id, weight='travel_time')
    #         if path_a: print(f"A*: Path found with {len(path_a)} nodes, Cost={cost_a:.2f}")
    #         else: print(f"A*: No path found. Cost={cost_a}")

    #         path_bfs = bidirectional_bfs(G_campus, start_node_id, end_node_id)
    #         if path_bfs: print(f"Bidirectional BFS: Path found with {len(path_bfs)} nodes.")
    #         else: print("Bidirectional BFS: No path found.")

    #     else:
    #         print("Could not get valid start/end nodes for testing pathfinding.")

    # except FileNotFoundError:
    #     print("Error: Graph file or building map not found. Run build_graph.py first.")
    # except Exception as e:
    #     print(f"An error occurred during example testing: {e}")
