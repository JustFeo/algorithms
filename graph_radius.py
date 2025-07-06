from collections import deque

def eccentricity(graph, start):
    """
    Compute the eccentricity of a vertex in an unweighted, undirected graph.
    
    Args:
        graph: Dictionary representing adjacency list of the graph
        start: Starting vertex to compute eccentricity from
    
    Returns:
        int: The eccentricity of the vertex (maximum distance to any other vertex)
    """
    visited = {start}
    queue = deque([(start, 0)])
    max_dist = 0
    
    while queue:
        node, dist = queue.popleft()
        max_dist = max(max_dist, dist)
        
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    
    return max_dist

def radius(graph):
    """
    Compute the radius of an unweighted, undirected graph.
    
    The radius is the minimum eccentricity among all vertices in the graph.
    The eccentricity of a vertex is the greatest distance from that vertex 
    to any other vertex in the graph.
    
    Args:
        graph: Dictionary representing adjacency list of the graph
    
    Returns:
        int: The radius of the graph
    """
    if not graph:
        return 0
    
    return min(eccentricity(graph, v) for v in graph)

def print_graph_info(graph):
    """Helper function to print graph information and radius."""
    print("Graph (adjacency list):")
    for vertex, neighbors in graph.items():
        print(f"  {vertex}: {neighbors}")
    
    rad = radius(graph)
    print(f"\nRadius of the graph: {rad}")
    print("-" * 40)

if __name__ == "__main__":
    # Example 1: Simple connected graph
    print("Example 1:")
    G1 = {
        0: [1, 2],
        1: [0, 2],
        2: [0, 1, 3],
        3: [2]
    }
    print_graph_info(G1)
    
    # Example 2: Cycle graph
    print("Example 2:")
    G2 = {
        0: [1, 4],
        1: [0, 2],
        2: [1, 3],
        3: [2, 4],
        4: [0, 3]
    }
    print_graph_info(G2)
    
    # Example 3: Star graph
    print("Example 3:")
    G3 = {
        0: [1, 2, 3, 4],
        1: [0],
        2: [0],
        3: [0],
        4: [0]
    }
    print_graph_info(G3)
    
    # Example 4: Path graph
    print("Example 4:")
    G4 = {
        0: [1],
        1: [0, 2],
        2: [1, 3],
        3: [2, 4],
        4: [3]
    }
    print_graph_info(G4) 