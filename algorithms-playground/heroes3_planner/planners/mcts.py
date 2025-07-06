"""
Monte Carlo Tree Search (MCTS) Planner for HOMM3.
"""
import math
import random
import copy # For deepcopying simulator states
from typing import Optional, List, Dict, Any, Tuple, Set

from heroes3_planner.simulator import GameSimulator, Hero
from heroes3_planner.planners.greedy import best_move_greedy


class MCTSNode:
    """
    Represents a node in the Monte Carlo Search Tree.
    """
    def __init__(self,
                 state_key: Any,
                 parent: Optional['MCTSNode'] = None,
                 action_that_led_here: Optional[Any] = None):
        self.state_key = state_key
        self.parent = parent
        self.action_that_led_here = action_that_led_here
        self.children: List['MCTSNode'] = []
        self.untried_actions: Optional[List[Any]] = None
        self.wins: float = 0.0
        self.visits: int = 0

    def get_untried_actions_stub(self, simulator_state_for_node: GameSimulator, hero_id: str, max_days_horizon: int):
        """
        Populates self.untried_actions based on the simulator state.
        This is a stub version; the MCTS search loop will manage this more directly.
        """
        if self.untried_actions is None:
            hero = simulator_state_for_node.get_hero(hero_id)
            if not hero:
                self.untried_actions = []
                return self.untried_actions

            self.untried_actions = get_legal_actions(
                hero.pos, hero.current_movement_points,
                simulator_state_for_node.current_day, max_days_horizon, simulator_state_for_node.graph
            )
        return self.untried_actions

    def expand(self, action: Any, child_state_key: Any) -> 'MCTSNode':
        child_node = MCTSNode(state_key=child_state_key, parent=self, action_that_led_here=action)
        self.children.append(child_node)
        if self.untried_actions: # Should have been populated before calling expand
            try:
                self.untried_actions.remove(action)
            except ValueError:
                 # This might happen if actions are generated on-the-fly and not from a fixed list
                 pass # Or log a warning: print(f"Warning: Action {action} not found in untried_actions of node {self.state_key}")
        return child_node

    def update(self, reward: float):
        self.visits += 1
        self.wins += reward

    def is_fully_expanded(self) -> bool:
        # Relies on untried_actions being correctly managed (populated then items removed).
        return self.untried_actions is not None and not self.untried_actions

    def is_terminal_node_state(self, current_day_of_state: int, max_days_horizon: int) -> bool:
        # A node is terminal if its state represents being at or beyond the planning horizon.
        return current_day_of_state > max_days_horizon

    def uct_value(self, exploration_constant: float = math.sqrt(2)) -> float:
        if self.visits == 0:
            return float('inf') # Ensure unvisited nodes are selected

        parent_visits = self.parent.visits if self.parent else self.visits
        if parent_visits == 0 : # Should ideally not happen for a child of an explored parent.
            parent_visits = 1 # Avoid math errors, though this indicates an unusual state.

        average_reward = self.wins / self.visits
        exploration_term = exploration_constant * math.sqrt(math.log(parent_visits) / self.visits)
        return average_reward + exploration_term

    def __repr__(self):
        uct_val_str = f"{self.uct_value():.2f}" if self.parent and self.parent.visits > 0 else "N/A"
        return (f"MCTSNode(state={self.state_key}, W/N={self.wins:.2f}/{self.visits}, "
                f"UCT={uct_val_str}, Children={len(self.children)})")

# --- MCTS Helper: State Key & Legal Actions ---

def get_mcts_state_key(sim: GameSimulator, hero_id: str) -> Tuple:
    """
    Generates an immutable, hashable key representing the current relevant game state for MCTS.
    Includes hero position, current day, hero movement points, and potentially collected items.
    For collected items, a frozenset of coordinates where one-time rewards were picked up.
    This needs to be carefully designed.
    """
    hero = sim.get_hero(hero_id)
    if not hero:
        # This case should be handled by the caller, but as a fallback:
        return ("NO_HERO", sim.current_day, 0, frozenset())

    # For simplicity, let's assume the graph nodes are updated by the simulator
    # when a reward is collected (e.g., object removed).
    # So, the graph's current state IS part of the simulator's state.
    # The key then primarily needs hero-specific and time-specific info.
    # If graph changes are not deepcopied with simulator, this is an issue.
    # For now, assume sim copy is deep enough.

    # A more robust key might involve hashing aspects of the graph if it's small,
    # or tracking collected item IDs explicitly.
    # For now: (pos, day, mp_left). This means different reward states at same (pos,day,mp) are aliased.
    # This is a common simplification if full state hashing is too complex/slow.
    # We rely on the simulator copy to hold the true state of collected items.
    return (hero.pos, sim.current_day, hero.current_movement_points)


def get_legal_actions(
    current_pos: Tuple[int,int],
    current_mp: int,
    current_day: int,
    max_days_horizon: int,
    graph: nx.Graph
) -> List[Any]:
    actions = []
    if current_mp > 0:
        for neighbor_pos in graph.neighbors(current_pos):
            edge_data = graph.get_edge_data(current_pos, neighbor_pos)
            if edge_data:
                move_cost = edge_data.get('weight', 100)
                if current_mp >= move_cost:
                    actions.append(("move", neighbor_pos))

    if current_day < max_days_horizon:
        actions.append(("end_day", None))

    # If actions is empty, it implies a terminal or stuck state for expansion purposes.
    return actions

# --- MCTS Algorithm Core ---

def mcts_planner(
    initial_sim_state: GameSimulator,
    hero_id: str,
    num_iterations: int,
    max_days_horizon: int, # Planning horizon for MCTS and rollouts
    exploration_constant: float = 1.414 # math.sqrt(2) is common, using 1.414 directly
) -> Optional[Any]:
    """
    Performs MCTS search from the initial_sim_state.
    Returns the best action to take from the root state.
    """
    initial_hero = initial_sim_state.get_hero(hero_id)
    if not initial_hero:
        raise ValueError(f"Hero {hero_id} not found in initial simulator state.")

    root_state_key = get_mcts_state_key(initial_sim_state, hero_id)
    root_node = MCTSNode(state_key=root_state_key)
    # root_node.visits = 1 # Avoid UCT issues with log(0) if root is selected; or handle in UCT.
                         # It's better to let visits start at 0 and handle in UCT.

    for i in range(num_iterations):
        iter_sim = copy.deepcopy(initial_sim_state) # Fresh simulator state for this iteration
        iter_hero = iter_sim.get_hero(hero_id)

        # 1. Selection
        current_mcts_node = root_node
        path_to_leaf_nodes = [current_mcts_node]

        while not current_mcts_node.is_terminal_node_state(iter_sim.current_day, max_days_horizon) and \
              current_mcts_node.is_fully_expanded() and current_mcts_node.children:

            current_mcts_node = max(current_mcts_node.children, key=lambda c: c.uct_value(exploration_constant))
            path_to_leaf_nodes.append(current_mcts_node)

            # Advance iter_sim state to match the selected child node
            action_taken = current_mcts_node.action_that_led_here
            if action_taken:
                action_type, action_target = action_taken
                if action_type == "move":
                    iter_sim.step(hero_id, "move", target_pos=action_target)
                elif action_type == "end_day":
                    iter_sim.end_day()
                iter_hero = iter_sim.get_hero(hero_id) # Refresh hero after sim step

        # 2. Expansion
        expanded_node_for_rollout = current_mcts_node # Default to current if terminal or no expansion

        if not current_mcts_node.is_terminal_node_state(iter_sim.current_day, max_days_horizon):
            if current_mcts_node.untried_actions is None: # Populate untried actions if first time
                current_mcts_node.untried_actions = get_legal_actions(
                    iter_hero.pos, iter_hero.current_movement_points,
                    iter_sim.current_day, max_days_horizon, iter_sim.graph
                )

            if current_mcts_node.untried_actions: # If there are actions to try
                action_to_expand = random.choice(current_mcts_node.untried_actions)
                # current_mcts_node.untried_actions.remove(action_to_expand) # Done in expand method

                # Simulate action to get child state key
                sim_after_action = copy.deepcopy(iter_sim)
                hero_after_action = sim_after_action.get_hero(hero_id)

                action_type, action_target = action_to_expand
                if action_type == "move":
                    sim_after_action.step(hero_id, "move", target_pos=action_target)
                elif action_type == "end_day":
                    sim_after_action.end_day()

                child_state_key = get_mcts_state_key(sim_after_action, hero_id)
                new_child_node = current_mcts_node.expand(action_to_expand, child_state_key)
                path_to_leaf_nodes.append(new_child_node)
                expanded_node_for_rollout = new_child_node

                # Simulator state for rollout is sim_after_action
                iter_sim = sim_after_action # The main simulator for this iteration is now at this expanded state
                iter_hero = iter_sim.get_hero(hero_id)


        # 3. Simulation (Rollout)
        rollout_sim = copy.deepcopy(iter_sim) # Simulate from the state of expanded_node_for_rollout
        rollout_hero_obj = rollout_sim.get_hero(hero_id)

        current_rollout_reward = 0.0
        # If expanded_node_for_rollout is terminal, its reward is effectively 0 from this point.
        # Rewards are relative to the state *before* the rollout.

        rollout_days_limit = max_days_horizon - rollout_sim.current_day + 1
        for _ in range(rollout_days_limit):
            if not rollout_hero_obj or rollout_sim.current_day > max_days_horizon : break

            # Simulate one day using greedy policy
            day_start_mp = rollout_hero_obj.current_movement_points # Should be full if start of day
            while rollout_hero_obj.current_movement_points > 0:
                greedy_path_segment = best_move_greedy(
                    rollout_hero_obj, rollout_sim.graph, rollout_sim.combat_rho
                )
                if not greedy_path_segment or len(greedy_path_segment) < 2:
                    break

                next_greedy_tile = greedy_path_segment[1]
                action_res = rollout_sim.step(hero_id, "move", target_pos=next_greedy_tile)

                interaction_rewards = action_res.get("interaction", {}).get("rewards", {})
                for res_type, res_amount in interaction_rewards.get("resources", {}).items():
                    # Simple sum of all resource values for now, could be weighted
                    current_rollout_reward += res_amount

                if action_res.get("status") != "success": break

            if rollout_sim.current_day < max_days_horizon : # Avoid ending day if it's the last day of horizon
                rollout_sim.end_day()
                rollout_hero_obj = rollout_sim.get_hero(hero_id)
            else:
                break # Reached day limit for rollout

        # 4. Backpropagation
        for node_in_path in reversed(path_to_leaf_nodes):
            node_in_path.update(current_rollout_reward)

    # After iterations, select best action from root's children
    if not root_node.children: return None

    best_action_node = max(root_node.children, key=lambda c: c.visits if c.visits > 0 else -float('inf'))
    # Alternative: max(root_node.children, key=lambda c: (c.wins / c.visits) if c.visits > 0 else -float('inf'))

    return best_action_node.action_that_led_here


if __name__ == '__main__':
    # Example Node Usage
    root_state_key = ("(0,0)", 1, 1500)
    root_node = MCTSNode(state_key=root_state_key)
    # root_node.visits = 1 # If we want to avoid inf UCT for root's children initially.
                        # MCTS usually starts selection from root, so root's UCT not used.
    print(f"Root: {root_node}")

    # Simulate expansion
    action1 = ("move", (0,1))
    child1_state_key = ("(0,1)", 1, 1400)
    # Manually populate untried_actions for root for this test
    root_node.untried_actions = [action1, ("move", (1,0))]
    child1_node = root_node.expand(action1, child1_state_key)

    print(f"Root after expanding child1: {root_node}")
    print(f"Child1: {child1_node}")

    # Simulate a rollout and backpropagation for child1
    # Path to leaf for this rollout was [root_node, child1_node]
    child1_node.update(reward=100.0)
    root_node.update(reward=100.0)

    print(f"Child1 after update: {child1_node}")
    print(f"Root after update (from child1 path): {root_node}")

    print(f"Child1 UCT: {child1_node.uct_value()}")

    action2 = ("move", (1,0)) # This was in root_node.untried_actions
    child2_state_key = ("(1,0)", 1, 1400) # Assuming same cost for move
    child2_node = root_node.expand(action2, child2_state_key) # untried_actions updated in expand

    child2_node.update(reward=10.0)
    root_node.update(reward=10.0)

    print(f"Root W/N: {root_node.wins}/{root_node.visits}")
    print(f"Child1 W/N: {child1_node.wins}/{child1_node.visits}")
    print(f"Child2 W/N: {child2_node.wins}/{child2_node.visits}")

    print(f"Child1 UCT (parent_visits={root_node.visits}): {child1_node.uct_value()}")
    print(f"Child2 UCT (parent_visits={root_node.visits}): {child2_node.uct_value()}")

    # Test get_legal_actions (needs a graph)
    sample_graph = nx.Graph()
    sample_graph.add_edge((0,0),(0,1), weight=100)
    sample_graph.add_edge((0,0),(1,0), weight=150)
    legal = get_legal_actions(current_pos=(0,0), current_mp=200, current_day=1, max_days_horizon=3, graph=sample_graph)
    print(f"Legal actions from (0,0) with 200MP, Day 1/3: {legal}")
    # Expected: [('move', (0,1)), ('move', (1,0)), ('end_day', None)]

    legal_low_mp = get_legal_actions(current_pos=(0,0), current_mp=50, current_day=1, max_days_horizon=3, graph=sample_graph)
    print(f"Legal actions from (0,0) with 50MP, Day 1/3: {legal_low_mp}")
    # Expected: [('end_day', None)]

    legal_last_day = get_legal_actions(current_pos=(0,0), current_mp=200, current_day=3, max_days_horizon=3, graph=sample_graph)
    print(f"Legal actions from (0,0) with 200MP, Day 3/3: {legal_last_day}")
    # Expected: [('move', (0,1)), ('move', (1,0))] (no 'end_day')


    # A basic MCTS planner run would need a GameSimulator instance.
    # This is too complex for a simple if __name__ == "__main__" without more setup.
    # Unit tests will cover mcts_planner function.

```
