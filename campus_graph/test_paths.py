import unittest
import networkx as nx
import osmnx as ox # For graph creation utilities if needed, and heuristic
from campus_graph.paths import dijkstra, a_star, bidirectional_bfs, heuristic_distance

class TestPathfinding(unittest.TestCase):

    def setUp(self):
        # Simple graph for basic tests
        self.simple_graph = nx.MultiDiGraph()
        self.simple_graph.add_node(1, x=0, y=0)
        self.simple_graph.add_node(2, x=1, y=1)
        self.simple_graph.add_node(3, x=2, y=0)
        self.simple_graph.add_node(4, x=1, y=-1)
        self.simple_graph.add_node(5, x=3, y=1) # Unreachable

        self.simple_graph.add_edge(1, 2, travel_time=10, length=10)
        self.simple_graph.add_edge(1, 4, travel_time=5, length=5)
        self.simple_graph.add_edge(2, 3, travel_time=8, length=8)
        self.simple_graph.add_edge(4, 3, travel_time=7, length=7)
        self.simple_graph.add_edge(1, 3, travel_time=20, length=20) # Direct, but longer than 1-4-3 or 1-2-3

        # Graph with multiple edges between nodes
        self.multi_edge_graph = nx.MultiDiGraph()
        self.multi_edge_graph.add_node('A', x=0, y=0)
        self.multi_edge_graph.add_node('B', x=1, y=0)
        self.multi_edge_graph.add_edge('A', 'B', key='short_walk', travel_time=5, length=5)
        self.multi_edge_graph.add_edge('A', 'B', key='long_drive', travel_time=2, length=10) # Faster but longer
        self.multi_edge_graph.add_edge('A', 'B', key='scenic_route', travel_time=10, length=3) # Shortest but slower

        # Graph with no path
        self.no_path_graph = nx.MultiDiGraph()
        self.no_path_graph.add_node(1, x=0, y=0)
        self.no_path_graph.add_node(2, x=1, y=0)
        self.no_path_graph.add_node(3, x=2, y=0) # Disconnected
        self.no_path_graph.add_edge(1,2, travel_time=1)


    def test_dijkstra_simple(self):
        # Path 1-4-3 with travel_time = 5+7=12
        path, cost = dijkstra(self.simple_graph, 1, 3, weight='travel_time')
        self.assertEqual(path, [1, 4, 3])
        self.assertEqual(cost, 12)

        # Path 1-4-3 with length = 5+7=12
        path_l, cost_l = dijkstra(self.simple_graph, 1, 3, weight='length')
        self.assertEqual(path_l, [1, 4, 3])
        self.assertEqual(cost_l, 12)

        # Start = End
        path_se, cost_se = dijkstra(self.simple_graph, 1, 1, weight='travel_time')
        self.assertEqual(path_se, [1])
        self.assertEqual(cost_se, 0)

    def test_dijkstra_no_path(self):
        path, cost = dijkstra(self.simple_graph, 1, 5, weight='travel_time')
        self.assertIsNone(path)
        self.assertEqual(cost, float('inf'))

        path_np, cost_np = dijkstra(self.no_path_graph, 1, 3, weight='travel_time')
        self.assertIsNone(path_np)
        self.assertEqual(cost_np, float('inf'))


    def test_dijkstra_multi_edge(self):
        # Should pick 'long_drive' for travel_time (cost 2)
        path, cost = dijkstra(self.multi_edge_graph, 'A', 'B', weight='travel_time')
        self.assertEqual(path, ['A', 'B'])
        self.assertEqual(cost, 2)

        # Should pick 'scenic_route' for length (cost 3)
        path_l, cost_l = dijkstra(self.multi_edge_graph, 'A', 'B', weight='length')
        self.assertEqual(path_l, ['A', 'B'])
        self.assertEqual(cost_l, 3)

    def test_a_star_simple(self):
        # Path 1-4-3 with travel_time = 5+7=12
        path, cost = a_star(self.simple_graph, 1, 3, weight='travel_time', heuristic_func=heuristic_distance)
        self.assertEqual(path, [1, 4, 3])
        self.assertEqual(cost, 12)

        # Path 1-4-3 with length = 5+7=12
        path_l, cost_l = a_star(self.simple_graph, 1, 3, weight='length', heuristic_func=heuristic_distance)
        self.assertEqual(path_l, [1, 4, 3])
        self.assertEqual(cost_l, 12)

        # Start = End
        path_se, cost_se = a_star(self.simple_graph, 1, 1, weight='travel_time')
        self.assertEqual(path_se, [1])
        self.assertEqual(cost_se, 0)

    def test_a_star_no_path(self):
        path, cost = a_star(self.simple_graph, 1, 5, weight='travel_time', heuristic_func=heuristic_distance)
        self.assertIsNone(path)
        self.assertEqual(cost, float('inf'))

        path_np, cost_np = a_star(self.no_path_graph, 1, 3, weight='travel_time')
        self.assertIsNone(path_np)
        self.assertEqual(cost_np, float('inf'))

    def test_a_star_multi_edge(self):
        # Should pick 'long_drive' for travel_time (cost 2)
        path, cost = a_star(self.multi_edge_graph, 'A', 'B', weight='travel_time', heuristic_func=heuristic_distance)
        self.assertEqual(path, ['A', 'B'])
        self.assertEqual(cost, 2)

        # Should pick 'scenic_route' for length (cost 3)
        path_l, cost_l = a_star(self.multi_edge_graph, 'A', 'B', weight='length', heuristic_func=heuristic_distance)
        self.assertEqual(path_l, ['A', 'B'])
        self.assertEqual(cost_l, 3)

    def test_bidirectional_bfs_simple(self):
        # Finds *a* path, not necessarily shortest by weight. Path can vary.
        path = bidirectional_bfs(self.simple_graph, 1, 3)
        self.assertIsNotNone(path)
        self.assertTrue(path[0] == 1 and path[-1] == 3)
        # Verify path is valid (all edges exist)
        for i in range(len(path) - 1):
            self.assertTrue(self.simple_graph.has_edge(path[i], path[i+1]))

        # Start = End
        path_se = bidirectional_bfs(self.simple_graph, 1, 1)
        self.assertEqual(path_se, [1])


    def test_bidirectional_bfs_no_path(self):
        path = bidirectional_bfs(self.simple_graph, 1, 5)
        self.assertIsNone(path)

        path_np = bidirectional_bfs(self.no_path_graph, 1, 3)
        self.assertIsNone(path_np)

    def test_heuristic_distance(self):
        # Simple graph nodes: 1 (0,0), 2 (1,1), 3 (2,0)
        # Distance 1 to 2 = sqrt((1-0)^2 + (1-0)^2) = sqrt(2)
        dist_1_2 = heuristic_distance(self.simple_graph, 1, 2)
        self.assertAlmostEqual(dist_1_2, 2**0.5)

        # Distance 1 to 3 = sqrt((2-0)^2 + (0-0)^2) = sqrt(4) = 2
        dist_1_3 = heuristic_distance(self.simple_graph, 1, 3)
        self.assertAlmostEqual(dist_1_3, 2.0)

        # Test with lat/lon if graph had them (mocking)
        mock_graph_latlon = nx.MultiDiGraph()
        mock_graph_latlon.add_node('A', lat=52.00, lon=4.37)
        mock_graph_latlon.add_node('B', lat=52.01, lon=4.38)
        # ox.distance.great_circle(52.00, 4.37, 52.01, 4.38) is approx 1300-1400m
        dist_ab_ll = heuristic_distance(mock_graph_latlon, 'A', 'B')
        self.assertTrue(1000 < dist_ab_ll < 2000) # Rough check for great circle

    # TODO: Add a test with the actual TU Delft graph if Aula and EEMCS are found.
    # This would require loading the graphml and json map.
    def test_on_real_graph(self):
        try:
            G_campus = ox.load_graphml("campus_graph/tudelft_campus_graph.graphml")
            import json
            with open("campus_graph/building_node_map.json", "r") as f:
                building_nodes = json.load(f)

            start_node_id = building_nodes.get("Aula")
            # EEMCS might not be in building_nodes if it wasn't found by build_graph.py
            # For a robust test, we pick a known existing node if EEMCS is not available.
            # Node 1410536806 was identified as near "BK City" (which was mistaken for EEMCS earlier)
            # This node should exist in the graph.
            target_node_id_candidate = building_nodes.get("EEMCS")

            if not target_node_id_candidate: # If EEMCS was not found
                print("EEMCS node not found in map, using a fallback test node if available.")
                # Pick a node that is known to exist from previous runs or a characteristic one
                # Example: A node from the graph, ensure it's not the start_node_id
                if G_campus.nodes:
                    potential_targets = [n for n in G_campus.nodes() if n != start_node_id]
                    if potential_targets:
                        # Let's try to pick a node that is somewhat distant to make the test meaningful.
                        # Heuristic distance can be used here.
                        # This is a simple way to find a somewhat distant node.
                        sorted_potential_targets = sorted(potential_targets, key=lambda n: heuristic_distance(G_campus, start_node_id, n), reverse=True)
                        if sorted_potential_targets:
                             target_node_id_candidate = sorted_potential_targets[len(sorted_potential_targets)//10] # e.g. 10th percentile of farness
                        else: # only one other node
                             target_node_id_candidate = potential_targets[0]


            if start_node_id and target_node_id_candidate and target_node_id_candidate in G_campus.nodes():
                target_node_id = target_node_id_candidate
                print(f"\nTesting on real graph: Start='Aula'(Node {start_node_id}) -> Target=(Node {target_node_id})")

                path_d, cost_d = dijkstra(G_campus, start_node_id, target_node_id, weight='travel_time')
                self.assertIsNotNone(path_d, f"Dijkstra failed on real graph from {start_node_id} to {target_node_id}")
                self.assertTrue(cost_d < float('inf'), f"Dijkstra cost is infinite for {start_node_id} to {target_node_id}")
                print(f"Real graph Dijkstra: Path length {len(path_d)}, Cost {cost_d:.2f}")

                path_a, cost_a = a_star(G_campus, start_node_id, target_node_id, weight='travel_time')
                self.assertIsNotNone(path_a, f"A* failed on real graph from {start_node_id} to {target_node_id}")
                self.assertTrue(cost_a < float('inf'), f"A* cost is infinite for {start_node_id} to {target_node_id}")
                self.assertAlmostEqual(cost_a, cost_d, places=5, msg=f"A* and Dijkstra costs differ significantly for {start_node_id} to {target_node_id}")
                print(f"Real graph A*: Path length {len(path_a)}, Cost {cost_a:.2f}")

                path_bfs = bidirectional_bfs(G_campus, start_node_id, target_node_id)
                self.assertIsNotNone(path_bfs, f"Bidirectional BFS failed on real graph from {start_node_id} to {target_node_id}")
                print(f"Real graph BiBFS: Path length {len(path_bfs)}")

            else:
                missing_info = []
                if not start_node_id: missing_info.append("Aula node ID")
                if not target_node_id_candidate: missing_info.append("target node ID (EEMCS or fallback)")
                elif target_node_id_candidate not in G_campus.nodes(): missing_info.append(f"target node ID {target_node_id_candidate} not in graph")
                self.skipTest(f"Could not find a suitable pair of connected nodes for real graph test. Missing: {', '.join(missing_info)}.")
        except FileNotFoundError:
            self.skipTest("Graph files not found (tudelft_campus_graph.graphml or building_node_map.json). Run build_graph.py first.")
        except Exception as e:
            self.fail(f"Real graph test failed with an unexpected error: {e}")


if __name__ == '__main__':
    unittest.main()
