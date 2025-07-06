import pytest
import networkx as nx
from heroes3_planner.simulator import Hero
from heroes3_planner.planners.greedy import best_move_greedy, get_node_reward, estimate_cost_to_fight

@pytest.fixture
def sample_graph_and_hero():
    graph = nx.Graph()
    hero_start_pos = (0,0)

    nodes_data = {
        hero_start_pos: {"terrain_type": "grass", "objects": [], "reward": 0},
        (0,1): {"terrain_type": "dirt", "objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}], "reward": 0}, # Base node reward 0, object gives 100
        (1,0): {"terrain_type": "swamp", "objects": [], "reward": 10}, # Direct node reward 10
        (1,1): {"terrain_type": "grass", "objects": [{"type": "monster", "name": "Goblins", "strength": 30}], "reward": 200, "guard_strength": 30}, # High reward, guarded
        (2,0): {"terrain_type": "sand", "objects": [{"type": "artifact", "id": "sword", "value": 150}], "reward": 0}, # Base node reward 0, artifact gives 150
        (2,1): {"terrain_type": "rough", "objects": [{"type": "mine", "mine_type": "ore_mine", "flag_reward": 250}], "reward": 0} # Base node reward 0, mine gives 250
    }
    for node, data in nodes_data.items():
        graph.add_node(node, **data)

    edges_data = [
        (hero_start_pos, (0,1), 100),
        (hero_start_pos, (1,0), 120),
        ((0,1), (1,1), 80),
        ((1,0), (1,1), 100),
        ((1,0), (2,0), 150), # Cost to (2,0) is 120+150 = 270
        ((1,1), (2,1), 90)  # Cost to (2,1) via (0,1)->(1,1) is 100+80+90 = 270
                            # Cost to (2,1) via (1,0)->(1,1) is 120+100+90 = 310
    ]
    for u, v, w in edges_data:
        graph.add_edge(u,v, weight=w)

    # Army strength 20*10 = 200. Combat rho = 1.5. Guard (30 str) needs 30*1.5 = 45 hero strength. Winnable.
    hero = Hero(hero_id="test_hero", pos=hero_start_pos, base_movement_points=1000, army={"pikemen": 20})
    combat_rho = 1.5
    return graph, hero, combat_rho

def test_get_node_reward(sample_graph_and_hero):
    graph, _, _ = sample_graph_and_hero
    assert get_node_reward(graph, (0,0)) == 0
    assert get_node_reward(graph, (0,1)) == 100 # Gold pile
    assert get_node_reward(graph, (1,0)) == 10 # Direct reward
    assert get_node_reward(graph, (1,1)) == 200 # Base reward, guard doesn't affect node reward func
    assert get_node_reward(graph, (2,0)) == 150 # Artifact value
    assert get_node_reward(graph, (2,1)) == 250 # Mine flag_reward

def test_estimate_cost_to_fight(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero

    # No guards
    assert estimate_cost_to_fight(hero, graph, (0,1), combat_rho) == 0.0

    # Winnable fight
    assert hero.get_army_strength() == 200
    # Guard strength at (1,1) is 30. 200 >= 1.5 * 30 (45.0) -> True
    assert estimate_cost_to_fight(hero, graph, (1,1), combat_rho) == 0.0

    # Unwinnable fight
    weak_hero = Hero("weak_hero", (0,0), 100, army={"peasant":1}) # Strength 10
    assert estimate_cost_to_fight(weak_hero, graph, (1,1), combat_rho) == float('inf')

def test_best_move_greedy_targets_highest_score(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero

    # Scores:
    # (0,1): Reward=100, CostReach=100, CostFight=0. Score = 100/100 = 1.0. Path: [(0,0),(0,1)]
    # (1,0): Reward=10, CostReach=120, CostFight=0. Score = 10/120 approx 0.083. Path: [(0,0),(1,0)]
    # (1,1): Reward=200, CostReach=(0,0)->(0,1)->(1,1) = 100+80=180. CostFight=0. Score = 200/180 approx 1.11. Path: [(0,0),(0,1),(1,1)]
    #        CostReach=(0,0)->(1,0)->(1,1) = 120+100=220. Score = 200/220 approx 0.909
    # (2,0): Reward=150, CostReach=(0,0)->(1,0)->(2,0) = 120+150=270. CostFight=0. Score = 150/270 approx 0.55. Path: [(0,0),(1,0),(2,0)]
    # (2,1): Reward=250, CostReach=(0,0)->(0,1)->(1,1)->(2,1) = 100+80+90=270. CostFight=0. Score = 250/270 approx 0.925. Path: [(0,0),(0,1),(1,1),(2,1)]

    # Expected best is (1,1) via (0,1)
    expected_path = [(0,0), (0,1), (1,1)]
    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path == expected_path

def test_best_move_greedy_movement_limited(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero
    hero.current_movement_points = 100 # Can only reach (0,1)

    # (0,1): Reward=100, CostReach=100. Score=1.0
    # All other paths cost > 100.
    expected_path = [(0,0), (0,1)]
    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path == expected_path

def test_best_move_greedy_cannot_defeat_guards(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero
    hero.army = {"peasant": 1} # Strength 10, cannot beat guards at (1,1)
    hero.recalculate_army_strength()

    # Now (1,1) is not an option.
    # Scores without (1,1):
    # (0,1): Reward=100, CostReach=100, CostFight=0. Score = 1.0
    # (1,0): Reward=10, CostReach=120, CostFight=0. Score = 10/120 approx 0.083
    # (2,0): Reward=150, CostReach=270, CostFight=0. Score = 150/270 approx 0.55
    # (2,1): Reward=250. Path via (0,1)->(1,1) is blocked due to fight.
    #        Path via (1,0)->(1,1) is also blocked.
    #        The greedy planner uses shortest_path, which doesn't consider if intermediate nodes are fightable.
    #        This is a limitation of simple greedy; it finds path to target, then checks target.
    #        For this test, we assume (2,1) is unreachable if (1,1) is blocked.
    #        Let's re-evaluate reachable targets without (1,1) if it's guarded.
    #        The current `best_move_greedy` calculates all shortest paths first, then prunes.
    #        So, it will find a path to (2,1), then estimate_cost_to_fight for (2,1) (which is 0).
    #        This is fine.

    # Re-evaluating scores with weak hero (cannot fight at (1,1)):
    # (0,1): Reward=100, CostReach=100, CostFight=0. Score = 1.0. Path: [(0,0),(0,1)]
    # (1,0): Reward=10, CostReach=120, CostFight=0. Score = 10/120 approx 0.083. Path: [(0,0),(1,0)]
    # (1,1): CostFight=inf. Not considered.
    # (2,0): Reward=150, CostReach=270, CostFight=0. Score = 150/270 approx 0.55. Path: [(0,0),(1,0),(2,0)]
    # (2,1): Reward=250, CostReach=270 (via (0,0)->(0,1)->(1,1)->(2,1) - but (1,1) is guarded and hero is weak).
    #        The cost_fight is for the *target_node* (2,1), which is 0.
    #        This highlights a potential issue: The path to (2,1) might go *through* (1,1).
    #        The current `best_move_greedy` does not evaluate fights along the path, only at the destination.
    #        This is a known simplification for a baseline greedy.
    #        Given this, (0,1) should be chosen.

    expected_path = [(0,0), (0,1)] # (0,1) has score 1.0. (2,0) has score 0.55.
    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path == expected_path

def test_best_move_greedy_no_beneficial_move(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero
    # Modify graph to have no rewards or only negative/zero scores
    for node in graph.nodes():
        graph.nodes[node]['reward'] = 0
        if 'objects' in graph.nodes[node]:
            new_objects = []
            for obj in graph.nodes[node]['objects']:
                if obj.get('type') == 'monster': # Keep monsters, remove other reward objects
                    new_objects.append(obj)
            graph.nodes[node]['objects'] = new_objects

    # Recalculate for (0,1) which had gold, now it should be 0
    assert get_node_reward(graph, (0,1)) == 0

    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path is None

def test_best_move_greedy_prefers_shorter_path_for_equal_score(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero
    # Add a new node (0,-1) with same score as (0,1) but longer path
    # (0,1): Reward=100, CostReach=100, Score=1.0, Path len 2
    graph.add_node((0,-1), objects=[{"type": "resource_pile", "resource": "wood", "amount": 200}], reward=0) # Reward 200*0.5 = 100
    graph.add_node((-1,0), objects=[], reward=0)
    graph.add_edge((0,0), (-1,0), weight=50)
    graph.add_edge((-1,0), (0,-1), weight=50) # Path to (0,-1) is (0,0)->(-1,0)->(0,-1), cost 100, score 1.0, Path len 3

    # (0,1) path: [(0,0), (0,1)]
    # (0,-1) path: [(0,0), (-1,0), (0,-1)]
    # Both have score 1.0. (0,1) should be chosen due to shorter path.
    expected_path = [(0,0), (0,1)]
    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path == expected_path

def test_best_move_greedy_handles_source_node_not_in_graph(sample_graph_and_hero):
    graph, hero, combat_rho = sample_graph_and_hero
    hero.pos = (100, 100) # Position not in graph
    actual_path = best_move_greedy(hero, graph, combat_rho)
    assert actual_path is None

def test_best_move_greedy_empty_graph(sample_graph_and_hero):
    _, hero, combat_rho = sample_graph_and_hero
    empty_graph = nx.Graph()
    actual_path = best_move_greedy(hero, empty_graph, combat_rho)
    assert actual_path is None

def test_best_move_greedy_graph_with_only_start_node(sample_graph_and_hero):
    _, hero, combat_rho = sample_graph_and_hero
    single_node_graph = nx.Graph()
    single_node_graph.add_node(hero.pos)
    actual_path = best_move_greedy(hero, single_node_graph, combat_rho)
    assert actual_path is None

```
