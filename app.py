import streamlit as st
import osmnx as ox
import networkx as nx
import json
from campus_graph.paths import dijkstra, a_star # Assuming paths.py is in campus_graph

# --- Configuration & Data Loading ---
GRAPH_FILE = "campus_graph/tudelft_campus_graph.graphml"
NODE_MAP_FILE = "campus_graph/building_node_map.json"

@st.cache_data # Cache graph loading
def load_graph_data():
    """Loads the campus graph and building node map."""
    try:
        graph = ox.load_graphml(GRAPH_FILE)
        with open(NODE_MAP_FILE, "r") as f:
            building_node_map = json.load(f)
        # Ensure node IDs in map are integers if they were saved as strings by json
        building_node_map = {name: int(node_id) for name, node_id in building_node_map.items()}
        return graph, building_node_map
    except FileNotFoundError:
        st.error(f"Error: Graph file ({GRAPH_FILE}) or node map ({NODE_MAP_FILE}) not found. Please run build_graph.py first.")
        return None, None
    except Exception as e:
        st.error(f"An error occurred while loading graph data: {e}")
        return None, None

# --- Main App Logic ---
st.title("TU Delft Campus Route Finder")

# Load data
G, building_nodes = load_graph_data()

if G and building_nodes:
    st.sidebar.header("Route Options")

    # Building selection
    # For now, Aula is likely found. EEMCS is problematic.
    # We'll default to Aula. For EEMCS, if not found, we might need a placeholder or let user pick from available.

    available_buildings = list(building_nodes.keys())
    if not available_buildings:
        st.warning("No building connection points found in the map. Cannot select start/end buildings.")
        st.stop()

    # Default to Aula if available, otherwise first in list
    default_start_building = "Aula" if "Aula" in available_buildings else available_buildings[0]

    # For EEMCS, if it's not in building_nodes (due to build_graph.py issues),
    # this demo will have a problem for the specific Aula -> EEMCS requirement.
    # We can either:
    # 1. Show an error if EEMCS is not available.
    # 2. Pick another available building as a stand-in for demo purposes.
    # 3. Allow user to select any two available points.

    # For this demo, let's try to stick to Aula -> EEMCS.
    # If EEMCS is not available in building_nodes, we'll show a message.

    start_building_name = st.sidebar.selectbox(
        "Start Building",
        options=available_buildings,
        index=available_buildings.index(default_start_building) if default_start_building in available_buildings else 0
    )

    # Check if EEMCS is an option. If not, the demo's specific requirement can't be met.
    # For now, let's assume we want to pick "EEMCS" if it was successfully mapped.
    # If not, this part needs adjustment.
    # Let's make the target EEMCS, but if it's not an option, we'll handle it.

    # For the demo, the task is Aula -> EEMCS.
    # We need to ensure "EEMCS" is a concept, even if not perfectly mapped by build_graph.py
    # For this iteration, I'll assume if "EEMCS" is not in `building_nodes`, we cannot fulfill the specific request.

    # Let's make the dropdowns flexible for now.
    # If "EEMCS" is not in available_buildings, the user won't be able to select it.
    # This highlights the dependency on build_graph.py's success for EEMCS.
    default_end_building = None
    if "EEMCS" in available_buildings:
        default_end_building = "EEMCS"
    elif len(available_buildings) > 1 and start_building_name != available_buildings[1]: # pick another building if EEMCS is not there
        default_end_building = available_buildings[1]
    elif len(available_buildings) > 0 and start_building_name != available_buildings[0] : # pick first if only one other option
         default_end_building = available_buildings[0]


    end_building_name = st.sidebar.selectbox(
        "End Building",
        options=available_buildings,
        index=available_buildings.index(default_end_building) if default_end_building and default_end_building in available_buildings else 0
    )

    # Pathfinding algorithm selection
    algorithm = st.sidebar.selectbox("Algorithm", ["A*", "Dijkstra"])
    weight_to_use = 'travel_time' # For timing

    if st.sidebar.button("Find Route"):
        if not start_building_name or not end_building_name:
            st.error("Please select both start and end buildings.")
        elif start_building_name == end_building_name:
            st.warning("Start and end buildings are the same.")
        else:
            start_node_id = building_nodes.get(start_building_name)
            end_node_id = building_nodes.get(end_building_name)

            if start_node_id is None or end_node_id is None:
                st.error("Could not find graph nodes for the selected buildings. Check build_graph.py output.")
            else:
                st.write(f"Finding route from {start_building_name} (Node {start_node_id}) to {end_building_name} (Node {end_node_id}) using {algorithm}...")

                path = None
                cost = float('inf')

                if algorithm == "A*":
                    path, cost = a_star(G, start_node_id, end_node_id, weight=weight_to_use)
                elif algorithm == "Dijkstra":
                    path, cost = dijkstra(G, start_node_id, end_node_id, weight=weight_to_use)

                if path:
                    st.success(f"Path found! Estimated travel time: {cost:.2f} seconds ({cost/60:.2f} minutes).")
                    st.write(f"Path (sequence of {len(path)} OSM node IDs):")
                    st.write(path) # Displaying raw node IDs for now

                    # Plot the route
                    try:
                        # ox.plot_graph_route requires the graph to not be projected if lat/lon are used for plotting,
                        # or pass node coordinates explicitly.
                        # Our G is projected. plot_graph_route can handle projected graphs.
                        fig, ax = ox.plot_graph_route(
                            G,
                            path,
                            route_color="r",
                            route_linewidth=4,
                            node_size=0, # Don't show nodes on the route plot itself
                            show=False,
                            close=False,
                            orig_dest_node_color='green', # Color for start/end nodes of the path
                            orig_dest_node_size=50
                        )
                        # Add building names to the plot if possible (more advanced)
                        # For now, just the route.
                        st.pyplot(fig)
                    except Exception as e:
                        st.warning(f"Could not plot the route: {e}")
                else:
                    st.error("No path found between the selected buildings.")
    else:
        st.info("Select start and end buildings and click 'Find Route'.")

elif G is None and building_nodes is None:
    # Error already shown by load_graph_data
    pass
else:
    st.error("Graph data or building node map is partially missing. Cannot run the app.")

st.sidebar.markdown("---")
st.sidebar.info("This demo uses pathfinding algorithms on a graph of TU Delft's walkable paths from OpenStreetMap.")
if G:
    st.sidebar.markdown(f"Graph loaded with {len(G.nodes())} nodes and {len(G.edges())} edges.")
if building_nodes:
     st.sidebar.markdown(f"Found {len(building_nodes)} mapped building entry points: {', '.join(building_nodes.keys())}")
     if "Aula" not in building_nodes:
         st.sidebar.warning("Note: 'Aula' not found in mapped buildings.")
     if "EEMCS" not in building_nodes:
         st.sidebar.warning("Note: 'EEMCS' not found in mapped buildings. The specific demo requirement Aula -> EEMCS cannot be fulfilled.")


# To run: streamlit run app.py
