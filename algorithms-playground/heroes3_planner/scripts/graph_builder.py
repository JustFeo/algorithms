"""
This script takes the JSON map data exported from VCMI and converts it
into a NetworkX graph. It will also attach rewards and movement costs.
"""
import json
import networkx as nx
import os

INPUT_JSON_FILE = os.path.join("..", "data", "map_data.json")
OUTPUT_GRAPH_FILE = os.path.join("..", "data", "map_graph.gpickle") # Using gpickle for NetworkX

# Placeholder for movement costs (terrain_type: cost)
# Basic costs, not accounting for roads, diagonal, skills, artifacts yet.
# These values are just illustrative. Actual values from heroes.thelazy.net
# Dirt, Grass, Lava, Subterranean, Water, Highlands: 100
# Rough, Wasteland: 125
# Sand, Snow: 150
# Swamp: 175
# Roads reduce cost.
TERRAIN_MOVEMENT_COSTS = {
    "grass": 100,
    "dirt": 100,
    "lava": 100,
    "subterranean": 100,
    "water": 100, # Base for walking on water (e.g. water walk spell)
    "highlands": 100, # HoTA
    "rough": 125,
    "wasteland": 125, # HoTA
    "sand": 150,
    "snow": 150,
    "swamp": 175,
    "road_dirt": 75,
    "road_gravel": 65,
    "road_cobblestone": 50,
    # Add more terrain types as needed
}

# Diagonal movement factor
DIAGONAL_FACTOR = 1.414 # sqrt(2)

def get_tile_movement_cost(tile_data):
    """
    Calculates the base movement cost for a tile.
    This is a simplified version. Actual implementation will need to consider
    roads, native terrain bonuses, pathfinding skill, artifacts etc.
    """
    terrain_type = tile_data.get("terrain_type", "grass") # Default to grass
    has_road = tile_data.get("has_road", False)
    road_type = tile_data.get("road_type", None) # e.g., "dirt", "gravel", "cobblestone"

    if has_road and road_type:
        return TERRAIN_MOVEMENT_COSTS.get(f"road_{road_type}", TERRAIN_MOVEMENT_COSTS["grass"])
    return TERRAIN_MOVEMENT_COSTS.get(terrain_type, 1000) # High cost for unknown

def build_graph_from_json(json_file_path: str, output_graph_path: str):
    """
    Builds a NetworkX graph from the exported JSON map data.

    Args:
        json_file_path (str): Path to the JSON map data file.
        output_graph_path (str): Path to save the NetworkX graph.
    """
    if not os.path.exists(json_file_path):
        print(f"Error: JSON map data file not found at {json_file_path}")
        print("Please run map_exporter.py first to generate map_data.json (even if simulated).")
        # Create a dummy json_file_path for the script to run without error
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
        with open(json_file_path, 'w') as f:
            json.dump({
                "map_name": "dummy_map",
                "width": 10,
                "height": 10,
                "tiles": [{"x": i, "y": j, "terrain_type": "grass", "objects": [], "reward": 0} for i in range(10) for j in range(10)],
                "objects": []
            }, f, indent=4)
        print(f"Created dummy {json_file_path} to allow script execution.")

    with open(json_file_path, 'r') as f:
        map_data = json.load(f)

    graph = nx.Graph() # Or nx.DiGraph if actions are directed (e.g. one-way portals)

    width = map_data["width"]
    height = map_data["height"]
    tiles_data = map_data.get("tiles", []) # Assuming tiles is a list of dicts

    # Create nodes for each tile
    # Assuming tiles_data is a flat list, need to map to (x,y) or have (x,y) in tile_data
    # For simulation, let's assume tiles_data contains x,y
    tile_dict = {(tile["x"], tile["y"]): tile for tile in tiles_data}

    for y in range(height):
        for x in range(width):
            node_id = (x, y)
            tile_info = tile_dict.get(node_id, {"terrain_type": "unknown", "reward": 0, "objects": []})

            graph.add_node(
                node_id,
                terrain_type=tile_info.get("terrain_type"),
                objects=tile_info.get("objects", []), # List of objects on the tile
                reward=tile_info.get("reward", 0) # Resources, artifacts, etc.
            )

            # Add edges to neighbors (8 directions for H3 movement)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue # Skip self

                    nx_coord, ny_coord = x + dx, y + dy

                    if 0 <= nx_coord < width and 0 <= ny_coord < height:
                        neighbor_node_id = (nx_coord, ny_coord)
                        neighbor_tile_info = tile_dict.get(neighbor_node_id, {"terrain_type": "unknown"})

                        # Calculate movement cost
                        # Cost is associated with moving *from* node_id *to* neighbor_node_id
                        # So, cost depends on the terrain of the *target* tile (neighbor_node_id)
                        # and whether the move is diagonal.

                        # The problem description implies cost is per tile moved, depending on terrain.
                        # "points are consumed per tile moved, with costs depending on terrain, roads and diagonal moves"
                        # The lazy wiki: "If a hero moves from one terrain to another, the movement points
                        # consumption will depend on: Terrain ⇄ Terrain move - starting tile"
                        # This suggests the cost is based on the tile being *entered*. Let's use target tile for now.

                        # For now, let's use cost of entering the *neighbor* tile
                        base_cost_target = get_tile_movement_cost(neighbor_tile_info)

                        # Alternative from wiki: "Terrain ⇄ Terrain move - starting tile;"
                        # base_cost_start = get_tile_movement_cost(tile_info)

                        cost = base_cost_target # Using target tile's cost for now

                        if abs(dx) == 1 and abs(dy) == 1: # Diagonal move
                            cost *= DIAGONAL_FACTOR

                        # Ensure cost is an integer, as per H3 mechanics
                        cost = int(round(cost))

                        # Add edge with weight as movement cost
                        # And also consider objects on the target tile that might affect cost (e.g., guards)
                        guard_strength = 0
                        for obj in neighbor_tile_info.get("objects", []):
                            if obj.get("type") == "neutral_guard" or obj.get("type") == "monster":
                                guard_strength += obj.get("strength", 0)

                        graph.add_edge(node_id, neighbor_node_id, weight=cost, guard_strength=guard_strength)

    print(f"Graph built with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")

    os.makedirs(os.path.dirname(output_graph_path), exist_ok=True)
    nx.write_gpickle(graph, output_graph_path)
    print(f"Graph saved to {output_graph_path}")

if __name__ == "__main__":
    # Ensure the dummy JSON exists if map_exporter hasn't created a real one
    if not os.path.exists(INPUT_JSON_FILE):
        print(f"Warning: {INPUT_JSON_FILE} not found. Creating a dummy file for graph_builder to run.")
        dummy_map_data = {
            "map_name": "dummy_map_for_graph_builder",
            "width": 5, # Small map for quick test
            "height": 5,
            "tiles": [
                {"x": r, "y": c, "terrain_type": "grass", "objects": [], "reward": r*c % 5}
                for r in range(5) for c in range(5)
            ],
            "objects": [
                {"type": "resource_pile", "resource": "gold", "amount": 100, "x": 1, "y": 1, "reward": 100},
                {"type": "neutral_guard", "name": "Pikemen", "strength": 50, "x": 2, "y": 2}
            ]
        }
        # Update tile data with objects
        for obj in dummy_map_data["objects"]:
            for tile in dummy_map_data["tiles"]:
                if tile["x"] == obj["x"] and tile["y"] == obj["y"]:
                    tile["objects"].append(obj)
                    if "reward" in obj: # Add object reward to tile reward
                        tile["reward"] = tile.get("reward",0) + obj["reward"]


        os.makedirs(os.path.dirname(INPUT_JSON_FILE), exist_ok=True)
        with open(INPUT_JSON_FILE, 'w') as f:
            json.dump(dummy_map_data, f, indent=4)
        print(f"Created dummy {INPUT_JSON_FILE}")

    build_graph_from_json(INPUT_JSON_FILE, OUTPUT_GRAPH_FILE)

    # Optional: Load and verify graph
    if os.path.exists(OUTPUT_GRAPH_FILE):
        print(f"Verifying graph file {OUTPUT_GRAPH_FILE}...")
        g = nx.read_gpickle(OUTPUT_GRAPH_FILE)
        print(f"Loaded graph with {g.number_of_nodes()} nodes and {g.number_of_edges()} edges.")
        if (0,0) in g and (0,1) in g:
            if g.has_edge((0,0),(0,1)):
                 print(f"Edge (0,0)-(0,1) cost: {g[(0,0)][(0,1)]['weight']}")
            else:
                print("Edge (0,0)-(0,1) not found, check logic if map size > 0x0")

    else:
        print(f"Failed to create {OUTPUT_GRAPH_FILE}")
