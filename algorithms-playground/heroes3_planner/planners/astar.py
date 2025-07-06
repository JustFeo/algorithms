"""
A* Planner for HOMM3.
Plans a sequence of moves over a multi-day horizon to maximize collected rewards.
"""
from typing import Tuple, List, Set, Optional, Dict, Any
import heapq
import itertools # For unique sequence IDs in priority queue
import networkx as nx

# Assuming Hero and GameSimulator are accessible for state information and simulation
# For type hinting and potentially direct use. Actual instances passed by caller.
from heroes3_planner.simulator import Hero
# Re-use reward and cost logic from greedy planner for consistency if applicable
from heroes3_planner.planners.greedy import get_node_reward, estimate_cost_to_fight


class AStarState:
    """
    Represents a state in the A* search space.
    """
    def __init__(self,
                 pos: Tuple[int, int],
                 day: int,
                 movement_left: int,
                 total_collected_reward: float,
                 path: List[Tuple[int, int]],
                 hero_army_strength: int,
                 # To handle rewards that are collected once:
                 # Pass a set of collected reward coordinates or IDs along the path.
                 collected_reward_sources: Set[Tuple[int,int]],
                 g_score: float,
                 parent: Optional['AStarState'] = None):
        self.pos = pos
        self.day = day
        self.movement_left = movement_left
        self.total_collected_reward = total_collected_reward
        self.path = path
        self.hero_army_strength = hero_army_strength
        self.collected_reward_sources = collected_reward_sources # Set of (x,y) of collected one-time rewards

        self.parent = parent
        self.g_score = g_score
        self.h_score = 0.0
        self.f_score = 0.0

    def __lt__(self, other: 'AStarState') -> bool:
        # For heapq, which is a min-heap. If we store (-f_score, id, self),
        # this __lt__ is used by Python for tuple comparison if f_scores are equal.
        # It's good practice to have a deterministic tie-breaker.
        if self.f_score != other.f_score:
            # This might seem inverted if thinking about maximizing f_score with a min-heap.
            # However, if storing (-f_score, ...), then a smaller -f_score (i.e. larger f_score) is preferred.
            # If states are directly in a structure that uses __lt__ to find the "best",
            # and "best" means highest f_score, then this should be self.f_score > other.f_score.
            # For now, let's assume standard sorting: lower f_score is "less".
            # The priority queue handling will manage maximization.
            return self.f_score < other.f_score
        if self.total_collected_reward != other.total_collected_reward:
            return self.total_collected_reward < other.total_collected_reward # Maximize this for tie-breaking
        if self.day != other.day:
            return self.day > other.day # Fewer days is better
        return len(self.path) > len(other.path) # Shorter path is better

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AStarState):
            return NotImplemented
        # State for visited set: (pos, day, movement_left, frozenset(collected_reward_sources))
        # Army strength might also be needed if it can change and affects available actions/costs.
        return (self.pos == other.pos and
                self.day == other.day and
                self.movement_left == other.movement_left and
                self.hero_army_strength == other.hero_army_strength and
                self.collected_reward_sources == other.collected_reward_sources)

    def __hash__(self) -> int:
        return hash((self.pos, self.day, self.movement_left, self.hero_army_strength, frozenset(self.collected_reward_sources)))

    def __repr__(self) -> str:
        return (f"AStarState(pos={self.pos}, day={self.day}, move_left={self.movement_left}, "
                f"reward={self.total_collected_reward:.2f}, collected_sources_len={len(self.collected_reward_sources)}, "
                f"f={self.f_score:.2f} (g={self.g_score:.2f}, h={self.h_score:.2f}), path_len={len(self.path)})")


# --- Helper Functions for A* ---

# Memoization cache for heuristic
heuristic_cache = {}

def calculate_heuristic(
    current_pos: Tuple[int, int],
    current_day: int,
    graph: nx.Graph,
    max_days: int,
    base_daily_movement: int,
    hero_strength: int, # Pass current hero strength for heuristic involving combat
    combat_rho: float,
    collected_reward_sources: Set[Tuple[int,int]] # Pass collected sources to heuristic
) -> float:
    """
    Estimates the future reward potential from the current state.
    An admissible heuristic should not overestimate the true future reward.
    For maximizing rewards, g_score is total_collected_reward.
    h_score should be an optimistic estimate of additional rewards.
    """
    cache_key = (current_pos, current_day, frozenset(collected_reward_sources))
    if cache_key in heuristic_cache:
        return heuristic_cache[cache_key]

    remaining_days = max_days - current_day + 1
    if remaining_days <= 0:
        return 0.0

    # Simple admissible heuristic: value of the best single uncollected item on the map.
    # This doesn't account for reachability or remaining time well, but is admissible.
    max_potential_single_reward = 0.0
    for node_pos, data in graph.nodes(data=True):
        if node_pos not in collected_reward_sources:
            # Check if fightable for heuristic (optimistic: assume we can reach and fight if good reward)
            cost_fight_est = estimate_cost_to_fight(Hero("temp", (0,0),0, army={}), graph, node_pos, combat_rho) # Hero arg is dummy for this call structure
            # A better estimate_cost_to_fight for heuristic might take hero_strength directly

            # Simplified: if it's guarded and we are weak, maybe don't consider it for simple heuristic
            # Or, for admissibility, assume we can always win the fight if it leads to reward.
            # For now, let's assume get_node_reward gives potential reward if collected.
            if cost_fight_est < float('inf'): # Only consider if guards are beatable by *some* reasonable army
                                              # This estimate_cost_to_fight needs hero object or strength.
                                              # Let's pass the current hero's strength.
                # Create a temporary hero object for estimate_cost_to_fight
                temp_hero_for_heuristic = Hero("heuristic_hero", current_pos, base_daily_movement)
                temp_hero_for_heuristic.army_strength_cache = hero_strength # Use current A* state's hero strength

                fight_cost_at_node = estimate_cost_to_fight(temp_hero_for_heuristic, graph, node_pos, combat_rho)

                if fight_cost_at_node < float('inf'): # If this specific hero can win
                    node_r = get_node_reward(graph, node_pos)
                    max_potential_single_reward = max(max_potential_single_reward, node_r)

    # A slightly more involved heuristic:
    # Sum of top N rewards, that are "theoretically reachable" within remaining days.
    # For now, let's use a very simple sum of all *uncollected* rewards, discounted by a factor,
    # or just the max_potential_single_reward * remaining_days (this is likely not admissible).

    # Admissible heuristic: sum of all rewards from uncollected_reward_sources that are reachable
    # from current_pos within (remaining_days * base_daily_movement) ignoring other constraints.
    # This is essentially the "all-pairs shortest paths" problem if costs are uniform.
    # A simpler admissible heuristic is often just 0, or value of best item.

    # For now, let's use: max_potential_single_reward. This is weak.
    # A slightly better one: (sum of all uncollected rewards on map) / (number of uncollected rewards) * remaining_days
    # This is an average based approach.
    # Let's try: Sum of all positive rewards on *unvisited* nodes. (Still not great for admissibility)

    h = 0.0
    # A slightly more complex heuristic:
    # Find all nodes with positive rewards not yet collected.
    # For each, estimate if it's reachable in remaining_days * base_daily_movement.
    # Sum rewards of reachable ones. (This could be slow).

    # Simpler: Sum of top K uncollected rewards.
    uncollected_rewards = []
    for r_pos in graph.nodes():
        if r_pos not in collected_reward_sources:
            temp_hero_for_heuristic = Hero("heuristic_hero", current_pos, base_daily_movement)
            temp_hero_for_heuristic.army_strength_cache = hero_strength
            fight_cost_at_node = estimate_cost_to_fight(temp_hero_for_heuristic, graph, r_pos, combat_rho)
            if fight_cost_at_node < float('inf'):
                 uncollected_rewards.append(get_node_reward(graph, r_pos))

    uncollected_rewards.sort(reverse=True)

    # Heuristic: sum of the largest 'remaining_days' number of uncollected rewards
    # (optimistically assume we can get one best item per day)
    # h = sum(uncollected_rewards[:remaining_days]) # Previous more complex heuristic

    # Using a simple admissible heuristic (0) for initial debugging and correctness check.
    # This turns A* into Dijkstra's algorithm if costs are uniform, or UCS.
    # Since our g_score is total_collected_reward (we want to maximize it),
    # and heapq with -f_score extracts max f_score, h=0 means we prioritize paths
    # that have already accumulated high rewards.
    h = 0.0

    heuristic_cache[cache_key] = h
    return h


def reconstruct_path_from_state(state: AStarState) -> List[Tuple[int, int]]:
    """Reconstructs the path from the goal state using its stored path attribute."""
    return state.path


def a_star_planner(
    initial_hero: Hero, # Pass the full Hero object
    graph: nx.Graph,
    combat_rho: float,
    max_days: int,
    base_daily_movement: int
):
    """
    A* search algorithm to find a path for a hero over a given number of days
    that maximizes total collected reward.
    """

    start_pos = initial_hero.pos

    # Initial reward at starting tile (if any). This should be collected "before" the plan starts.
    # Or, the planner should handle it as the first action if valuable.
    # For simplicity, we assume the state's total_collected_reward starts at 0,
    # and rewards are gained upon *entering* a new tile.

    initial_collected_sources = set()
    # If there's a reward at the very start_pos that should be considered "collected"
    # initial_reward_at_start = get_node_reward(graph, start_pos)
    # if initial_reward_at_start > 0:
    #     initial_collected_sources.add(start_pos)

    start_node = AStarState(
        pos=start_pos,
        day=1,
        movement_left=base_daily_movement, # Use hero's current if day 1, or base if planning from future day
        total_collected_reward=0, # initial_reward_at_start if collected
        path=[start_pos],
        hero_army_strength=initial_hero.get_army_strength(),
        collected_reward_sources=initial_collected_sources,
        g_score=0 # g_score is total_collected_reward
    )
    start_node.h_score = calculate_heuristic(start_pos, 1, graph, max_days, base_daily_movement, start_node.hero_army_strength, combat_rho, start_node.collected_reward_sources)
    start_node.f_score = start_node.g_score + start_node.h_score

    open_set = []
    pq_id_counter = itertools.count()
    heapq.heappush(open_set, (-start_node.f_score, next(pq_id_counter), start_node))

    # visited_info stores max g_score (reward) for a state tuple
    # State tuple: (pos, day, movement_left, hero_army_strength_hashable, frozenset_collected_rewards)
    visited_g_scores: Dict[Tuple[Any, ...], float] = {}

    # Key for visited_g_scores
    start_state_key = (start_node.pos, start_node.day, start_node.movement_left, start_node.hero_army_strength, frozenset(start_node.collected_reward_sources))
    visited_g_scores[start_state_key] = start_node.total_collected_reward

    best_overall_state: Optional[AStarState] = start_node # Track state with highest reward across entire search

    max_iterations = 10000 # Safety break for complex searches
    iterations = 0

    while open_set and iterations < max_iterations:
        iterations += 1
        neg_f_score, _, current_astar_state = heapq.heappop(open_set)

        current_f_score = -neg_f_score

        # If a better path to this state (as defined by its key) was already found and processed
        current_state_key = (current_astar_state.pos, current_astar_state.day, current_astar_state.movement_left, current_astar_state.hero_army_strength, frozenset(current_astar_state.collected_reward_sources))
        if current_astar_state.total_collected_reward < visited_g_scores.get(current_state_key, -float('inf')):
            continue

        # Pruning: If current_f_score (actual_reward_so_far + optimistic_future_reward)
        # is already less than the best actual_reward_found_so_far by another completed path,
        # we might be able to prune. (This is more relevant for anytime algorithms or with tighter bounds)
        if best_overall_state and current_f_score < best_overall_state.total_collected_reward:
             pass # Continue, as this path is unlikely to beat the best actual path found. Needs careful thought.

        # Update best_overall_state if current state path has more reward
        if best_overall_state is None or current_astar_state.total_collected_reward > best_overall_state.total_collected_reward:
            best_overall_state = current_astar_state

        if current_astar_state.day > max_days: # Path ended due to reaching day horizon
            continue

        # --- Generate Successor States ---

        # Action 1: Move to an adjacent tile
        possible_next_moves = []
        for neighbor_pos in graph.neighbors(current_astar_state.pos):
            if not graph.has_edge(current_astar_state.pos, neighbor_pos): continue

            move_cost = graph.edges[current_astar_state.pos, neighbor_pos].get('weight', 100)

            if current_astar_state.movement_left >= move_cost:
                # Check for combat at neighbor_pos
                # Use a temporary hero object for estimate_cost_to_fight, with current A* state's army strength
                temp_hero = Hero("astar_temp", current_astar_state.pos, base_daily_movement)
                temp_hero.army_strength_cache = current_astar_state.hero_army_strength

                fight_at_neighbor_cost = estimate_cost_to_fight(temp_hero, graph, neighbor_pos, combat_rho)

                if fight_at_neighbor_cost == float('inf'): # Cannot win fight at neighbor
                    continue

                # If winnable, calculate reward and new state
                new_pos = neighbor_pos
                new_movement_left_after_move = current_astar_state.movement_left - move_cost

                # Calculate reward for this step (only if not previously collected on this path)
                step_reward = 0
                if new_pos not in current_astar_state.collected_reward_sources:
                    step_reward = get_node_reward(graph, new_pos)

                new_total_collected_reward = current_astar_state.total_collected_reward + step_reward
                new_path = current_astar_state.path + [new_pos]
                new_collected_sources = current_astar_state.collected_reward_sources.copy()
                if step_reward > 0: # Add to collected if it was a new reward
                    new_collected_sources.add(new_pos)

                # Movement for interacting/fighting (simplified: assume it's part of reaching the tile)
                # If combat happens or valuable items are picked up, it might end the hero's turn (movement = 0)
                # This requires simulator logic. For A*, let's assume movement points are only for travel.
                # Interaction costs (like ending turn) can be modeled by setting new_movement_left to 0.
                # For now, let's assume simple move, then movement_left is just reduced.
                # If objects on tile (e.g. pickup) should end turn:
                # new_movement_left_after_interaction = 0 if step_reward > 0 else new_movement_left_after_move
                new_movement_left_after_interaction = new_movement_left_after_move # Simplification

                successor_state = AStarState(
                    pos=new_pos, day=current_astar_state.day, movement_left=new_movement_left_after_interaction,
                    total_collected_reward=new_total_collected_reward, path=new_path,
                    hero_army_strength=current_astar_state.hero_army_strength, # Static army for now
                    collected_reward_sources=new_collected_sources,
                    g_score=new_total_collected_reward, parent=current_astar_state
                )
                possible_next_moves.append(successor_state)

        # Action 2: End current day (if not already max_days and has valid reason, e.g. no good moves or out of mp)
        # This action is taken from current_astar_state.pos
        if current_astar_state.day < max_days:
            end_day_state = AStarState(
                pos=current_astar_state.pos, day=current_astar_state.day + 1, movement_left=base_daily_movement, # Reset movement
                total_collected_reward=current_astar_state.total_collected_reward, # No reward for just ending day
                path=current_astar_state.path, # Path doesn't change location-wise, just day increments
                hero_army_strength=current_astar_state.hero_army_strength,
                collected_reward_sources=current_astar_state.collected_reward_sources.copy(),
                g_score=current_astar_state.total_collected_reward, parent=current_astar_state
            )
            possible_next_moves.append(end_day_state)

        # Process all generated successor states
        for next_state in possible_next_moves:
            next_state.h_score = calculate_heuristic(next_state.pos, next_state.day, graph, max_days, base_daily_movement, next_state.hero_army_strength, combat_rho, next_state.collected_reward_sources)
            next_state.f_score = next_state.g_score + next_state.h_score

            successor_key = (next_state.pos, next_state.day, next_state.movement_left, next_state.hero_army_strength, frozenset(next_state.collected_reward_sources))

            if next_state.total_collected_reward > visited_g_scores.get(successor_key, -float('inf')):
                heapq.heappush(open_set, (-next_state.f_score, next(pq_id_counter), next_state))
                visited_g_scores[successor_key] = next_state.total_collected_reward

    if best_overall_state:
        # Filter out trailing "wait" states if path ends with multiple day changes at same spot
        final_path = best_overall_state.path
        if len(final_path) > 1:
            # If the last few steps are just day changes at the same spot, might want to trim them
            # For now, return the full path as determined by A* state.
            pass
        return reconstruct_path_from_state(best_overall_state)
    return None


if __name__ == '__main__':
    # Example state creation
    initial_pos = (0,0)
    start_state = AStarState(
        pos=initial_pos, day=1, movement_left=1500, total_collected_reward=0.0,
        path=[initial_pos], hero_army_strength=100, collected_reward_sources=set(), g_score=0.0
    )
    start_state.h_score = 100.0
    start_state.f_score = start_state.g_score + start_state.h_score
    print(start_state)

    state2 = AStarState(
        pos=(0,1), day=1, movement_left=1400, total_collected_reward=10.0,
        path=[initial_pos, (0,1)], hero_army_strength=100,
        collected_reward_sources=set([(0,1)]), g_score=10.0, parent=start_state
    )
    state2.h_score = 80.0
    state2.f_score = state2.g_score + state2.h_score
    print(state2)

    print(f"state2 < start_state: {state2 < start_state}")

    state_eq1 = AStarState((0,0), 1, 1500, 0, [(0,0)], 100, set(), 0)
    state_eq2 = AStarState((0,0), 1, 1500, 0, [(0,0)], 100, set(), 0)

    print(f"state_eq1 == state_eq2: {state_eq1 == state_eq2}")
    print(f"hash(state_eq1) == hash(state_eq2): {hash(state_eq1) == hash(state_eq2)}")

    # --- Basic Test for A* Planner ---
    print("\n--- A* Planner Basic Test ---")
    test_graph_astar = nx.Graph()
    hero_start_pos_astar = (0,0)

    nodes_data_astar = {
        hero_start_pos_astar: {"objects": [], "reward": 0}, # Start node
        (0,1): {"objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}]}, # Reward 100
        (1,0): {"objects": [], "reward": 10}, # Reward 10
        (1,1): {"objects": [{"type": "resource_pile", "resource": "gems", "amount": 5}], "reward": 0} # Reward 5*0.5=2.5 (gems val) - get_node_reward needs update for this
                                                                                                    # For now, let's make it gold for simplicity in get_node_reward
    }
    # Update (1,1) for simpler reward calculation in test
    nodes_data_astar[(1,1)]["objects"] = [{"type": "resource_pile", "resource": "gold", "amount": 150}] # Reward 150


    for node, data in nodes_data_astar.items():
        graph_node_data = data.copy()
        if 'reward' not in graph_node_data: # Ensure base reward is present
            graph_node_data['reward'] = 0
        test_graph_astar.add_node(node, **graph_node_data)

    edges_data_astar = [
        (hero_start_pos_astar, (0,1), 100),
        (hero_start_pos_astar, (1,0), 100),
        ((0,1), (1,1), 100),
        ((1,0), (1,1), 100),
    ]
    for u, v, w in edges_data_astar:
        test_graph_astar.add_edge(u,v, weight=w)

    hero_astar_test = Hero(hero_id="astar_hero", pos=hero_start_pos_astar, base_movement_points=250, army={"pikemen": 5}) # Low movement

    # Heuristic will be 0 for now, so it's Dijkstra-like based on maximizing reward.
    # Max days = 1. Hero can make 2 moves if each costs 100.
    # Path 1: (0,0) -> (0,1) -> (1,1)
    #   (0,0): R=0
    #   (0,1): R=100. Total R=100. MoveCost=100. MP Left = 150.
    #   (1,1): R=150. Total R=100+150=250. MoveCost=100. MP Left = 50.
    # Path 2: (0,0) -> (1,0) -> (1,1)
    #   (1,0): R=10. Total R=10. MoveCost=100. MP Left = 150.
    #   (1,1): R=150. Total R=10+150=160. MoveCost=100. MP Left = 50.
    # Expected: [(0,0), (0,1), (1,1)] with total reward 250.

    # Clear heuristic cache for clean test run
    heuristic_cache.clear()

    best_path_astar = a_star_planner(
        initial_hero=hero_astar_test,
        graph=test_graph_astar,
        combat_rho=1.5,
        max_days=1,
        base_daily_movement=hero_astar_test.base_movement_points
    )

    print(f"A* Test Result Path: {best_path_astar}")
    if best_path_astar:
        # Calculate reward along this path
        path_reward = 0
        collected_on_path = set()
        for node_on_path in best_path_astar:
            if node_on_path not in collected_on_path:
                path_reward += get_node_reward(test_graph_astar, node_on_path)
                # Add only if it's a "pickup" type reward. For simplicity, assume all are.
                if get_node_reward(test_graph_astar, node_on_path) > 0:
                    collected_on_path.add(node_on_path)
        print(f"A* Test Path Calculated Reward: {path_reward}")

    # Expected: [(0,0), (0,1), (1,1)]
    # Reward: At (0,0) initial = 0. At (0,1) collect 100. At (1,1) collect 150. Total = 250.
    assert best_path_astar == [(0,0), (0,1), (1,1)], f"Expected [(0,0), (0,1), (1,1)], got {best_path_astar}"

    print("A* basic test with 1 day horizon completed.")

    # Test with 2-day horizon
    hero_astar_test_2day = Hero(hero_id="astar_hero_2day", pos=hero_start_pos_astar, base_movement_points=150, army={"pikemen": 5}) # 1 move per day

    # Day 1: (0,0) -> (0,1) (R=100). MP left = 50. End day.
    # Day 2: (0,1) -> (1,1) (R=150). MP left = 50. Total R = 250.
    # Path: [(0,0), (0,1), (0,1), (1,1)] (repeated (0,1) indicates end of day there)
    heuristic_cache.clear()
    best_path_astar_2day = a_star_planner(
        initial_hero=hero_astar_test_2day,
        graph=test_graph_astar,
        combat_rho=1.5,
        max_days=2,
        base_daily_movement=hero_astar_test_2day.base_movement_points
    )
    print(f"A* 2-Day Test Result Path: {best_path_astar_2day}")
    # Path reconstruction needs to be smarter or state representation for "end day" needs adjustment
    # Current path for end_day_state is `current_astar_state.path + [current_astar_state.pos]`
    # which is not quite right. It should just be `current_astar_state.path`.
    # Let's fix that in AStarState path update for end_day action.
    # No, the path should log the sequence of locations. If a day ends, hero is still at current_astar_state.pos.
    # The next day starts at that same position. So the path will naturally show [(0,0), (0,1), (0,1), (1,1)] if day ends at (0,1).

    # Expected for 2 days with 150MP/day:
    # Day 1: (0,0) -> (0,1) [collect 100]. Path: [(0,0),(0,1)]. End Day.
    # Day 2: (0,1) -> (1,1) [collect 150]. Path: [(0,0),(0,1),(1,1)]. Total Reward: 250
    # The planner's returned path should be the sequence of coordinates.
    # If it includes multiple entries for same location due to day end, that's fine for logging.
    assert best_path_astar_2day == [(0,0), (0,1), (1,1)], f"Expected [(0,0), (0,1), (1,1)] for 2day, got {best_path_astar_2day}"
    print("A* basic test with 2 day horizon completed.")

```
