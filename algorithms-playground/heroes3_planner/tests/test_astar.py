import pytest
import networkx as nx
from heroes3_planner.simulator import Hero
from heroes3_planner.planners.astar import a_star_planner, AStarState, calculate_heuristic, heuristic_cache
from heroes3_planner.planners.greedy import get_node_reward # Using this for reward calculation consistency

# Test fixture for a sample graph and hero
@pytest.fixture
def astar_test_setup_basic():
    graph = nx.Graph()
    hero_start_pos = (0,0)

    # Define nodes with potential rewards and objects
    # rewards are via get_node_reward which processes objects
    nodes_data = {
        hero_start_pos: {"objects": [], "reward": 0}, # Start node
        (0,1): {"objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}]}, # R=100
        (1,0): {"objects": [], "reward": 10}, # R=10
        (1,1): {"objects": [{"type": "resource_pile", "resource": "gold", "amount": 150}]}, # R=150
        (2,1): {"objects": [{"type": "artifact", "id": "gem_ring", "value": 200}]} # R=200
    }
    for node, data in nodes_data.items():
        graph_node_data = data.copy()
        if 'reward' not in graph_node_data: graph_node_data['reward'] = 0
        graph.add_node(node, **graph_node_data)

    # Define edges with movement costs
    edges_data = [
        (hero_start_pos, (0,1), 100),
        (hero_start_pos, (1,0), 100),
        ((0,1), (1,1), 100),
        ((1,0), (1,1), 100),
        ((1,1), (2,1), 100)
    ]
    for u, v, w in edges_data:
        graph.add_edge(u,v, weight=w)

    hero = Hero(hero_id="astar_hero", pos=hero_start_pos, base_movement_points=250, army={"swordsman":10}) # Army str 100
    combat_rho = 1.5
    base_daily_movement = hero.base_movement_points

    # Clear heuristic cache before each test run that uses it
    heuristic_cache.clear()

    return graph, hero, combat_rho, base_daily_movement

# --- Test Cases ---

def test_astar_simple_1day_best_reward(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic

    # Max_days = 1. Hero MP = 250.
    # Path 1: (0,0) -> (0,1) [R=100, Cost=100, MP Left=150] -> (1,1) [R=150, Cost=100, MP Left=50]. Total R=250. Path: [(0,0),(0,1),(1,1)]
    # Path 2: (0,0) -> (1,0) [R=10, Cost=100, MP Left=150] -> (1,1) [R=150, Cost=100, MP Left=50]. Total R=160. Path: [(0,0),(1,0),(1,1)]
    # Path 3: (0,0) -> (0,1) [R=100]. End. Total R=100.
    # Path 4: (0,0) -> (1,0) [R=10]. End. Total R=10.

    # With h=0, it should find the path yielding max reward within 1 day.
    # Expected: [(0,0),(0,1),(1,1)], total reward 250.
    # (2,1) is also R=200, path (0,0)->(0,1)->(1,1)->(2,1) cost 300. Not reachable in 250MP.

    hero.current_movement_points = base_daily_movement # Ensure fresh MP for test
    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=base_daily_movement)

    assert result_path == [(0,0), (0,1), (1,1)]

def test_astar_1day_movement_limited(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic
    hero.base_movement_points = 150 # Can only make one move costing 100, then has 50MP left.
    hero.current_movement_points = 150

    # Path 1: (0,0) -> (0,1) [R=100, Cost=100, MP Left=50]. Total R=100.
    # Path 2: (0,0) -> (1,0) [R=10, Cost=100, MP Left=50]. Total R=10.
    # Expected: [(0,0),(0,1)]
    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=150)
    assert result_path == [(0,0), (0,1)]

def test_astar_2day_reaches_further_reward(astar_test_setup_basic):
    graph, hero, combat_rho, _ = astar_test_setup_basic # Use default MP from fixture (250)

    # Day 1: (0,0) -> (0,1) [R=100, Cost=100, MP Left=150] -> (1,1) [R=150, Cost=100, MP Left=50]. Total R=250. End Day.
    # Day 2: Start at (1,1), MP=250. Move to (2,1) [R=200, Cost=100, MP Left=150]. Total R=250+200=450.
    # Expected path: [(0,0), (0,1), (1,1), (2,1)]

    result_path = a_star_planner(hero, graph, combat_rho, max_days=2, base_daily_movement=hero.base_movement_points)
    assert result_path == [(0,0), (0,1), (1,1), (2,1)]

def test_astar_2day_wait_for_better_opportunity(astar_test_setup_basic):
    graph, hero, combat_rho, _ = astar_test_setup_basic
    # Modify graph: (0,1) is low reward, (2,1) is high but needs 2 full moves (100+100+100=300MP total)
    # Hero has 250MP. So, cannot reach (2,1) in 1 day.
    # (0,0) -> (0,1) costs 100. Node (0,1) reward set to 5.
    # (0,1) -> (1,1) costs 100. Node (1,1) reward set to 10.
    # (1,1) -> (2,1) costs 100. Node (2,1) reward set to 500.

    graph.nodes[(0,1)]['objects'] = [{"type": "resource_pile", "resource": "gold", "amount": 5}]
    graph.nodes[(1,1)]['objects'] = [{"type": "resource_pile", "resource": "gold", "amount": 10}]
    graph.nodes[(2,1)]['objects'] = [{"type": "resource_pile", "resource": "gold", "amount": 500}]

    # Expected:
    # Day 1: (0,0) -> (0,1) (R=5, cost=100, mp_left=150) -> (1,1) (R=10, cost=100, mp_left=50). Total R=15. End Day at (1,1).
    # Day 2: Start at (1,1) (R=15 carry over), mp=250. -> (2,1) (R=500, cost=100, mp_left=150). Total R=15+500=515.
    # Path: [(0,0), (0,1), (1,1), (2,1)]

    heuristic_cache.clear() # Ensure fresh heuristic calculation if it matters
    result_path = a_star_planner(hero, graph, combat_rho, max_days=2, base_daily_movement=hero.base_movement_points)
    assert result_path == [(0,0), (0,1), (1,1), (2,1)]

def test_astar_no_rewards_path(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic
    # Remove all rewards
    for node in graph.nodes():
        graph.nodes[node]['objects'] = []
        graph.nodes[node]['reward'] = 0

    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=base_daily_movement)
    # With h=0, and no rewards, g_score is always 0. f_score is 0.
    # It will explore, best_overall_state will remain the start_node. Path will be [start_pos].
    assert result_path == [hero.pos]

def test_astar_guarded_reward_winnable(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic
    # Add guard to (0,1) which has R=100. Hero army str = 100.
    # Guard strength 30. combat_rho 1.5. Hero wins if 100 >= 1.5*30 (45). Hero wins.
    graph.nodes[(0,1)]['objects'].append({"type": "monster", "name": "weak_guard", "strength": 30})
    # estimate_cost_to_fight should return 0.

    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=base_daily_movement)
    # Should still go for (0,1) then (1,1) as guards are weak.
    assert result_path == [(0,0), (0,1), (1,1)]

def test_astar_guarded_reward_unwinnable(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic
    # Add strong guard to (0,1) (R=100). Hero army str = 100.
    # Guard strength 100. Hero loses if 100 < 1.5*100 (150).
    graph.nodes[(0,1)]['objects'] = [{"type": "monster", "name": "strong_guard", "strength": 100}]
    # estimate_cost_to_fight for (0,1) will be inf.

    # Now, path through (0,1) is blocked.
    # Alternative path to (1,1) is via (1,0).
    # (0,0) -> (1,0) [R=10, Cost=100, MP Left=150] -> (1,1) [R=150, Cost=100, MP Left=50]. Total R=160.
    # Path to (2,1) via (1,0)->(1,1)->(2,1) gives R=10+150+200 = 360, but needs 300MP. Not in 1 day.
    # So, for 1 day, best is [(0,0),(1,0),(1,1)].

    hero.current_movement_points = base_daily_movement
    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=base_daily_movement)
    assert result_path == [(0,0), (1,0), (1,1)]

def test_astar_collected_rewards_not_recollected(astar_test_setup_basic):
    graph, hero, combat_rho, base_daily_movement = astar_test_setup_basic
    # Create a small loop: (0,0) -> (0,1) [R=100] -> (0,0)
    # Add edge back from (0,1) to (0,0)
    graph.add_edge((0,1), (0,0), weight=50)
    hero.base_movement_points = 150 # (0,0)->(0,1) cost 100. (0,1)->(0,0) cost 50. Total 150.
    hero.current_movement_points = 150

    # Expected: (0,0) -> (0,1). Reward 100. Path [(0,0),(0,1)]
    # If it goes (0,0)->(0,1)->(0,0), reward at (0,1) should only be counted once.
    # The state includes `collected_reward_sources`.
    # Max day = 1.
    result_path = a_star_planner(hero, graph, combat_rho, max_days=1, base_daily_movement=150)

    # Expected path is just to (0,1) as it's the only reward.
    # Looping back to (0,0) offers no new reward and ends movement.
    assert result_path == [(0,0), (0,1)]

    # Verify total reward from the best state in planner (if accessible)
    # This requires modifying a_star_planner to return more info or checking logs.
    # For now, path implies the reward was handled correctly.


# TODO: Add tests for heuristic effectiveness once a non-zero heuristic is implemented and stable.
# TODO: Add tests for scenarios where army strength changes and affects outcomes.
# TODO: Add tests for very limited movement (e.g., cannot move at all).

```
