import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

# TU Delft campus approximate center
LAT_TUD, LON_TUD = 52.0022, 4.3737
DISTANCE_M = 1700

TARGET_BUILDING_TAGS_COORDS = {
    "Aula": {
        "tags": {"name": "Aula Congrescentrum", "building": "yes"},
        "coords": (52.0020, 4.3730),
        "osm_id": 200733486
    },
    "EEMCS": {
        "tags": { # Be very specific with tags for EWI
            "name": "Faculteit Elektrotechniek, Wiskunde en Informatica",
            "building": "university"
        },
        "coords": (52.0052, 4.3720),
        "osm_id": 24978982
    }
}

def fetch_target_buildings_by_tags_at_coord(target_specs):
    print("\n--- Fetching Target Buildings by Specific Tags at Coordinates ---")
    target_buildings_data = {}

    for key, spec in target_specs.items():
        # Use a larger distance for the EEMCS query as it's been problematic
        fetch_dist = 250 if key == "EEMCS" else 150
        print(f"Attempting to fetch '{key}' with tags {spec['tags']} around {spec['coords']} (dist={fetch_dist}m), expecting OSM ID {spec['osm_id']}")
        gdf_initial_fetch = pd.DataFrame()
        try:
            gdf_initial_fetch = ox.features_from_point(spec['coords'], tags=spec['tags'], dist=fetch_dist)

            if not gdf_initial_fetch.empty:
                id_to_match = spec['osm_id']
                gdf_filtered_by_id = pd.DataFrame()

                if id_to_match in gdf_initial_fetch.index:
                    gdf_filtered_by_id = gdf_initial_fetch.loc[[id_to_match]]
                elif isinstance(gdf_initial_fetch.index, pd.MultiIndex) and ('way', id_to_match) in gdf_initial_fetch.index:
                    gdf_filtered_by_id = gdf_initial_fetch.loc[[('way', id_to_match)]]
                elif isinstance(gdf_initial_fetch.index, pd.MultiIndex) and ('relation', id_to_match) in gdf_initial_fetch.index:
                    gdf_filtered_by_id = gdf_initial_fetch.loc[[('relation', id_to_match)]]
                elif 'osmid' in gdf_initial_fetch.columns and id_to_match in gdf_initial_fetch['osmid'].values:
                     print(f"  Info: OSM ID {id_to_match} for '{key}' found via 'osmid' column.")
                     gdf_filtered_by_id = gdf_initial_fetch[gdf_initial_fetch['osmid'] == id_to_match]

                if not gdf_filtered_by_id.empty:
                    building_feature = gdf_filtered_by_id[gdf_filtered_by_id['geometry'].type.isin(['Polygon', 'MultiPolygon'])]
                    if not building_feature.empty:
                        target_buildings_data[key] = building_feature.iloc[[0]]
                        # Correctly get OSM ID from index (which might be simple or multi-index)
                        idx_val = target_buildings_data[key].index[0]
                        retrieved_osm_id = idx_val[1] if isinstance(idx_val, tuple) else idx_val

                        print(f"  Successfully fetched and ID-verified '{key}' as Polygon/MultiPolygon.")
                        print(f"    Name: {target_buildings_data[key]['name'].iloc[0] if 'name' in target_buildings_data[key].columns and pd.notna(target_buildings_data[key]['name'].iloc[0]) else 'N/A'}, OSM ID: {retrieved_osm_id}")
                        if retrieved_osm_id != id_to_match:
                             print(f"    CRITICAL WARNING: Retrieved OSM ID ({retrieved_osm_id}) for '{key}' does not match expected ID ({id_to_match}). This indicates an issue.")
                    else:
                        print(f"  OSM ID {id_to_match} for '{key}' found, but corresponding feature is not a Polygon/MultiPolygon.")
                        target_buildings_data[key] = None
                else:
                    print(f"  OSM ID {id_to_match} for '{key}' NOT found in results of tag query near coordinates.")
                    target_buildings_data[key] = None
            else:
                print(f"  No features found for '{key}' with tags {spec['tags']} near {spec['coords']}.")
                target_buildings_data[key] = None
        except Exception as e:
            print(f"  Error fetching '{key}' with specific tags: {e}")
            target_buildings_data[key] = None

    return target_buildings_data

# fetch_campus_data and main functions remain the same
def fetch_campus_data(lat, lon, distance, target_building_specs):
    print(f"Fetching walkable graph for point ({lat}, {lon}) with distance {distance}m...")
    G_walk = ox.graph_from_point((lat, lon), dist=distance, network_type="walk", simplify=True, retain_all=False)
    print(f"Fetched and simplified walkable graph with {len(G_walk.nodes)} nodes and {len(G_walk.edges)} edges.")
    G_walk_proj = ox.project_graph(G_walk)
    print("Projected graph to UTM.")

    all_building_tags = {"building": True}
    all_buildings_gdf = ox.features_from_point((lat, lon), tags=all_building_tags, dist=distance)
    print(f"Fetched {len(all_buildings_gdf)} general building features with tags {all_building_tags}.")

    target_buildings_data = fetch_target_buildings_by_tags_at_coord(target_building_specs)

    return G_walk_proj, all_buildings_gdf, target_buildings_data

def main():
    G_campus_proj, all_buildings_context_gdf, target_buildings_data = fetch_campus_data(
        LAT_TUD, LON_TUD, DISTANCE_M,
        TARGET_BUILDING_TAGS_COORDS
    )

    if not G_campus_proj:
        print("Failed to fetch or process the walkable graph. Exiting.")
        return

    if G_campus_proj.edges:
        G_campus_proj = ox.add_edge_speeds(G_campus_proj)
        G_campus_proj = ox.add_edge_travel_times(G_campus_proj)
        print(f"\nWalkable graph edges (sample with attributes): {list(G_campus_proj.edges(data=True))[:1]}")
    else:
        print("Graph has no edges. Skipping speed/time calculation.")

    print(f"\nAll general buildings fetched for context: {len(all_buildings_context_gdf)}")

    print("\nTarget Buildings Data & Graph Integration:")
    building_node_map = {}

    for name, building_gdf in target_buildings_data.items():
        if building_gdf is not None and not building_gdf.empty:
            print(f"Processing '{name}':")
            if 'geometry' not in building_gdf.columns or building_gdf['geometry'].iloc[0] is None:
                print(f"  Warning: No valid geometry for '{name}'. Skipping.")
                continue
            building_geom = building_gdf["geometry"].iloc[0]
            try:
                building_centroid_orig_crs = building_geom.centroid
            except Exception as e:
                print(f"  Warning: Could not get centroid for '{name}' geometry. Type: {building_geom.type}. Error: {e}. Skipping.")
                continue

            building_centroid_proj = ox.projection.project_geometry(building_centroid_orig_crs, to_crs=G_campus_proj.graph['crs'])[0]

            osm_id_val_from_index = building_gdf.index[0]
            actual_osm_id = osm_id_val_from_index[1] if isinstance(osm_id_val_from_index, tuple) else osm_id_val_from_index

            nearest_walk_node_id = ox.nearest_nodes(G_campus_proj, X=building_centroid_proj.x, Y=building_centroid_proj.y)
            building_name_display = building_gdf['name'].iloc[0] if 'name' in building_gdf.columns and pd.notna(building_gdf['name'].iloc[0]) else "N/A"

            print(f"  OSM ID (from index): {actual_osm_id}, Display Name: {building_name_display}")
            print(f"  Centroid (proj): ({building_centroid_proj.x:.2f}, {building_centroid_proj.y:.2f})")
            print(f"  Nearest walkable node ID in graph: {nearest_walk_node_id}")
            building_node_map[name] = int(nearest_walk_node_id)
        else:
            print(f"Data for '{name}': Not found or empty GDF from fetching attempts.")

    valid_building_node_map = building_node_map
    if G_campus_proj.nodes:
        valid_building_node_map = {name: node_id for name, node_id in building_node_map.items() if node_id in G_campus_proj.nodes}
        if len(valid_building_node_map) != len(building_node_map) and building_node_map:
             print("Warning: Some building connection nodes were not found in the graph (after validation) or buildings not found.")

        ox.save_graphml(G_campus_proj, filepath="campus_graph/tudelft_campus_graph.graphml")
        print("\nSaved campus graph to campus_graph/tudelft_campus_graph.graphml")

        import json
        with open("campus_graph/building_node_map.json", "w") as f:
            json.dump(valid_building_node_map, f)
        print("Saved building-to-node map to campus_graph/building_node_map.json")
    else:
        print("Graph has no nodes. Skipping saving graph and map.")

    # Plotting
    if G_campus_proj.nodes and (not all_buildings_context_gdf.empty or any(gdf is not None for gdf in target_buildings_data.values())):
        fig, ax = ox.plot_graph(G_campus_proj, show=False, close=False, bgcolor='w', node_color='gray', node_size=5, node_alpha=0.3, edge_color='#BCBABA', edge_linewidth=0.3, save=False)
        if not all_buildings_context_gdf.empty:
            all_buildings_context_gdf_proj = all_buildings_context_gdf.to_crs(G_campus_proj.graph['crs'])
            all_buildings_context_gdf_proj.plot(ax=ax, fc="lightgray", ec="gray", alpha=0.3, zorder=1)

        node_colors_plot = {}
        node_sizes_plot = {}
        any_target_building_plotted = False
        for building_key_name, building_data_gdf in target_buildings_data.items():
            if building_data_gdf is not None and not building_data_gdf.empty:
                building_data_gdf_proj = building_data_gdf.to_crs(G_campus_proj.graph['crs'])
                building_data_gdf_proj.plot(ax=ax, fc="red", ec="darkred", alpha=0.7, label=building_key_name, zorder=3)
                any_target_building_plotted = True
                if building_key_name in valid_building_node_map:
                    connected_node_id = valid_building_node_map[building_key_name]
                    node_colors_plot[connected_node_id] = 'red'
                    node_sizes_plot[connected_node_id] = 60

        if valid_building_node_map and any_target_building_plotted:
            nodes_gdf = ox.graph_to_gdfs(G_campus_proj, nodes=True, edges=False)
            nodes_to_plot_ids = [nid for nid in node_colors_plot.keys() if nid in nodes_gdf.index]
            if nodes_to_plot_ids:
                nodes_to_plot_gdf = nodes_gdf.loc[nodes_to_plot_ids]
                nodes_to_plot_gdf.plot(ax=ax,
                                   color=[node_colors_plot.get(idx, 'blue') for idx in nodes_to_plot_gdf.index],
                                   markersize=[node_sizes_plot.get(idx, 5) for idx in nodes_to_plot_gdf.index],
                                   zorder=4, label="Building Access Points")

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc='lower left', fontsize='small')
        print("Saving plot to campus_graph/tudelft_campus_map.png")
        plt.savefig("campus_graph/tudelft_campus_map.png", dpi=300, bbox_inches='tight')
        print("Plot saved. Check the image to verify.")
    elif not G_campus_proj.nodes:
        print("Graph has no nodes. Plotting skipped.")
    else:
        print("No general context buildings or target buildings to plot. Plotting skipped.")

if __name__ == "__main__":
    main()
