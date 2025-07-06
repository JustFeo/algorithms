"""
Greedy planner for HOMM3.
Selects the best immediate move based on a reward/cost heuristic.
"""
from typing import List, Tuple, Optional, Dict, Any
import networkx as nx
from heroes3_planner.simulator import Hero # Assuming Hero class is in simulator.py for now
# from ..simulator import Hero # Use this if planners is a sub-package and simulator is sibling

def get_node_reward(graph: nx.Graph, node_pos: Tuple[int, int]) -> float:
    """
    Calculates the reward associated with a node.
    This can be from resources, artifacts, unguarded mines, etc.
    """
    if not graph.has_node(node_pos):
        return 0.0

    reward = graph.nodes[node_pos].get('reward', 0.0)

    # Consider rewards from objects on the tile
    # This logic might be more complex, e.g. some objects give one-time rewards,
    # others (like mines) give continuous rewards or have other effects.
    # For greedy, we primarily look for immediate, quantifiable rewards.
    for obj in graph.nodes[node_pos].get('objects', []):
        if obj.get('type') == 'resource_pile':
            # Value of resource could be normalized or based on game importance
            # For now, let's assume 'amount' is the direct reward value if resource is gold,
            # or some other valuation for other resources.
            if obj.get('resource') == 'gold':
                reward += obj.get('amount', 0)
            else: # Other resources like wood, ore
                reward += obj.get('amount', 0) * 0.5 # Simple placeholder valuation
        elif obj.get('type') == 'artifact':
            reward += obj.get('value', 100) # Placeholder value for an artifact
        # TODO: Add other reward sources: chests, dwellings (if quantifiable for one-time visit)
        # Mines are more complex as their reward is typically per-day after flagging.
        # For a simple greedy, maybe an unflagged mine has a one-time "flagging" reward.
        elif obj.get('type') == 'mine' and not obj.get('owner'):
             reward += obj.get('flag_reward', 250) # Arbitrary reward for flagging a new mine

    return float(reward)


def estimate_cost_to_fight(hero: Hero, graph: nx.Graph, node_pos: Tuple[int, int], combat_rho: float) -> float:
    """
    Estimates the 'cost' of fighting guards at a node.
    - 0 if no guards.
    - A high value (infinity) if guards are too strong.
    - Otherwise, could be 0 if easily winnable, or some heuristic value.
      For this greedy version, let's assume 0 if winnable, infinity if not.
      A more advanced greedy might factor in expected losses or time.
    """
    if not graph.has_node(node_pos):
        return float('inf')

    guard_strength = graph.nodes[node_pos].get('guard_strength', 0)
    if 'objects' in graph.nodes[node_pos]: # More detailed guard check
        current_guard_strength = 0
        for obj_at_target in graph.nodes[node_pos]['objects']:
            if obj_at_target.get('type') == 'monster' or obj_at_target.get('type') == 'neutral_guard':
                current_guard_strength += obj_at_target.get('strength', 0)
        guard_strength = current_guard_strength

    if guard_strength == 0:
        return 0.0

    hero_strength = hero.get_army_strength()

    # Using the combat proxy logic (hero_strength >= rho * guard_strength)
    if hero_strength >= combat_rho * guard_strength:
        return 0.0 # Winnable, cost is effectively 0 for this simple greedy
    else:
        return float('inf') # Unwinnable or too costly

def best_move_greedy(
    hero: Hero,
    graph: nx.Graph,
    combat_rho: float,
    max_path_cost: Optional[float] = None
) -> Optional[List[Tuple[int, int]]]:
    """
    Calculates the best single move for a hero using a greedy approach.
    The "move" can be a path to a target tile.
    The greedy heuristic is: reward / (cost_to_reach + cost_to_fight).

    Args:
        hero: The hero object.
        graph: The map graph (NetworkX).
        combat_rho: Combat ratio for determining winnability.
        max_path_cost: If None, uses hero.current_movement_points. Otherwise, uses this value.

    Returns:
        A list of coordinates representing the path to the best target,
        or None if no beneficial move is found.
    """
    current_pos = hero.pos
    if max_path_cost is None:
        max_movement_points = hero.current_movement_points
    else:
        max_movement_points = max_path_cost

    if not graph.has_node(current_pos):
        return None # Hero not on graph

    best_target_path = None
    max_score = -float('inf')

    # Explore reachable nodes using Dijkstra's algorithm to find shortest paths (costs)
    # 'weight' attribute on edges is assumed to be movement cost.
    try:
        # length is cost_to_reach, path is the sequence of nodes
        paths_costs: Dict[Tuple[int, int], float] = nx.shortest_path_length(graph, source=current_pos, weight='weight')
        paths: Dict[Tuple[int, int], List[Tuple[int, int]]] = nx.shortest_path(graph, source=current_pos, weight='weight')
    except nx.NetworkXNoPath: # Should not happen if graph is connected and source is valid
        return None


    for target_node, cost_to_reach in paths_costs.items():
        if target_node == current_pos:
            continue # Skip current position

        if cost_to_reach > max_movement_points:
            continue # Cannot reach this node with current movement points

        path_to_target = paths[target_node]

        reward = get_node_reward(graph, target_node)
        cost_fight = estimate_cost_to_fight(hero, graph, target_node, combat_rho)

        if cost_fight == float('inf'):
            continue # Cannot win fight or too costly

        # Avoid division by zero if cost_to_reach is 0 (should not happen for different target_node)
        # or if both reward and cost are zero.
        # Add a small epsilon to cost to prevent division by zero if reward > 0 and cost = 0.
        effective_cost = cost_to_reach + cost_fight
        if effective_cost <= 0: # If cost is 0 (e.g. adjacent, no fight) and reward > 0, this is good.
            if reward > 0:
                score = float('inf') # Prioritize free rewards highly
            else:
                score = 0 # No reward, no cost, no score
        else:
            score = reward / effective_cost

        # Special handling for positive reward with zero cost to ensure it's preferred
        if reward > 0 and cost_to_reach == 0 and cost_fight == 0: # e.g. item on current tile already
            # This case should ideally be handled by an "interact" action rather than "move".
            # However, if it's a target for a "move", it means it's an adjacent "free" pickup.
             pass # Score calculation above should handle this.

        if score > max_score:
            max_score = score
            best_target_path = path_to_target
        elif score == max_score and score > 0: # Prefer shorter paths if scores are equal and positive
            if best_target_path is None or len(path_to_target) < len(best_target_path):
                best_target_path = path_to_target

    if best_target_path and max_score <= 0: # If best_target_path exists, but score is not positive
        # This means we might have found a path to a 0-reward, 0-cost (except movement) node.
        # We only want to move if there's a positive incentive.
        return None

    return best_target_path


if __name__ == "__main__":
    # Example Usage:
    # Setup a dummy graph and hero (similar to simulator's test)
    test_graph = nx.Graph()
    hero_start_pos = (0,0)

    nodes_data_greedy = {
        hero_start_pos: {"terrain_type": "grass", "objects": [], "reward": 0},
        (0,1): {"terrain_type": "dirt", "objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}], "reward": 100}, # Reward 100
        (1,0): {"terrain_type": "swamp", "objects": [], "reward": 10}, # Reward 10
        (1,1): {"terrain_type": "grass", "objects": [{"type": "monster", "name": "Goblins", "strength": 30}], "reward": 200, "guard_strength": 30}, # High reward, but guarded
        (2,0): {"terrain_type": "sand", "objects": [{"type": "artifact", "id": "sword", "value": 150}], "reward": 150}, # Reward 150
        (2,1): {"terrain_type": "rough", "objects": [{"type": "mine", "mine_type": "ore_mine", "flag_reward": 200}], "reward": 0} # Node itself has 0, but mine object has flag_reward.
                                                                                                                                # get_node_reward should pick this up.
    }
    for node, data in nodes_data_greedy.items():
        test_graph.add_node(node, **data)

    # Edges: (node1, node2, weight)
    edges_data_greedy = [
        (hero_start_pos, (0,1), 100),
        (hero_start_pos, (1,0), 120), # Slightly more expensive path
        ((0,1), (1,1), 80),
        ((1,0), (1,1), 100),
        ((1,0), (2,0), 150),
        ((1,1), (2,1), 90)
    ]
    for u, v, w in edges_data_greedy:
        test_graph.add_edge(u,v, weight=w)

    # Create a hero
    # Army strength 20*10 = 200. Combat rho = 1.5. Guard (30 str) needs 30*1.5 = 45 hero strength. So, winnable.
    hero_greedy = Hero(hero_id="greedy_hero", pos=hero_start_pos, base_movement_points=300, army={"pikemen": 20})
    test_combat_rho = 1.5

    print(f"Hero initial state: {hero_greedy}")
    print(f"Hero movement points: {hero_greedy.current_movement_points}")

    # Test with enough movement points
    best_path = best_move_greedy(hero_greedy, test_graph, test_combat_rho)
    print(f"Best greedy path (unlimited movement for test): {best_path}")
    if best_path:
        target_node = best_path[-1]
        cost_to_reach = nx.shortest_path_length(test_graph, source=hero_start_pos, target=target_node, weight='weight')
        reward = get_node_reward(test_graph, target_node)
        cost_fight = estimate_cost_to_fight(hero_greedy, test_graph, target_node, test_combat_rho)
        print(f"  Target: {target_node}, Reward: {reward}, Cost_Reach: {cost_to_reach}, Cost_Fight: {cost_fight}, Score: {reward/(cost_to_reach+cost_fight if cost_to_reach+cost_fight > 0 else 1)}")


    # Test with limited movement
    hero_greedy.current_movement_points = 100
    print(f"\nHero movement points: {hero_greedy.current_movement_points}")
    best_path_limited_mp = best_move_greedy(hero_greedy, test_graph, test_combat_rho)
    print(f"Best greedy path (MP={hero_greedy.current_movement_points}): {best_path_limited_mp}")
    if best_path_limited_mp:
        target_node = best_path_limited_mp[-1]
        cost_to_reach = nx.shortest_path_length(test_graph, source=hero_start_pos, target=target_node, weight='weight')
        reward = get_node_reward(test_graph, target_node)
        cost_fight = estimate_cost_to_fight(hero_greedy, test_graph, target_node, test_combat_rho)
        print(f"  Target: {target_node}, Reward: {reward}, Cost_Reach: {cost_to_reach}, Cost_Fight: {cost_fight}, Score: {reward/(cost_to_reach+cost_fight if cost_to_reach+cost_fight > 0 else 1)}")

    # Test with hero unable to defeat guards
    hero_greedy.army = {"peasant": 1} # Army strength 1*10 = 10. Guard needs 45. Not winnable.
    hero_greedy.recalculate_army_strength()
    hero_greedy.current_movement_points = 300 # Reset MP
    print(f"\nHero state (weak army): {hero_greedy}")
    best_path_weak_hero = best_move_greedy(hero_greedy, test_graph, test_combat_rho)
    print(f"Best greedy path (weak hero): {best_path_weak_hero}")
    if best_path_weak_hero:
        target_node = best_path_weak_hero[-1]
        cost_to_reach = nx.shortest_path_length(test_graph, source=hero_start_pos, target=target_node, weight='weight')
        reward = get_node_reward(test_graph, target_node)
        cost_fight = estimate_cost_to_fight(hero_greedy, test_graph, target_node, test_combat_rho)
        print(f"  Target: {target_node}, Reward: {reward}, Cost_Reach: {cost_to_reach}, Cost_Fight: {cost_fight}, Score: {reward/(cost_to_reach+cost_fight if cost_to_reach+cost_fight > 0 else 1)}")

    # Test case where best score is 0 or negative (no beneficial move)
    empty_graph = nx.Graph()
    empty_graph.add_node((0,0), reward=0)
    empty_graph.add_node((0,1), reward=0)
    empty_graph.add_edge((0,0), (0,1), weight=100)
    hero_no_reward = Hero("no_reward_hero", (0,0), 150)
    print(f"\nHero no reward: {hero_no_reward}")
    path_no_reward = best_move_greedy(hero_no_reward, empty_graph, 1.5)
    print(f"Path with no rewards: {path_no_reward}") # Should be None

```
