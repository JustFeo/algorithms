"""
HOMM3 Turn Advisor CLI

This tool uses different planning algorithms (Greedy, A*, MCTS) to suggest
the best course of action for a hero in Heroes of Might and Magic III.
"""
import argparse
import time
import networkx as nx

# Project imports (adjust paths if necessary, or ensure package is installed)
from heroes3_planner.simulator import Hero, GameSimulator
from heroes3_planner.planners.greedy import best_move_greedy
from heroes3_planner.planners.astar import a_star_planner
from heroes3_planner.planners.mcts import mcts_planner, MCTSNode # MCTSNode for type hint if needed
from heroes3_planner.planners.mcts import heuristic_cache as mcts_heuristic_cache # if mcts uses astar's heuristic cache
from heroes3_planner.planners.astar import heuristic_cache as astar_heuristic_cache


# --- Sample Game State Setup ---
def setup_sample_game_state():
    """
    Creates a sample graph, hero, and simulator instance for testing the advisor.
    This is similar to the setup in experiments.ipynb or unit tests.
    """
    graph = nx.Graph()
    hero_start_pos = (0,0)

    nodes_data = {
        hero_start_pos: {"objects": [], "reward": 0},
        (0,1): {"objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}]},
        (1,0): {"objects": [], "reward": 10},
        (1,1): {"objects": [{"type": "resource_pile", "resource": "gold", "amount": 150}], "guard_strength": 0}, # No guard initially
        (2,1): {"objects": [{"type": "artifact", "id": "gem_ring", "value": 200}]},
        (2,0): {"objects": [{"type": "mine", "mine_type": "gold_mine", "flag_reward": 300}]},
        (0,2): {"objects": [{"type": "resource_pile", "resource": "wood", "amount": 20}]},
        (1,2): {"objects": [{"type": "monster", "name": "Goblins", "strength": 50}], "guard_strength": 50, "reward": 50}, # Guarded minor reward
        (2,2): {"objects": [{"type": "resource_pile", "resource": "gems", "amount": 5, "value_per_gem":50}]} # 5*50=250 reward
    }
    for node, data in nodes_data.items():
        graph_node_data = data.copy()
        if 'reward' not in graph_node_data: graph_node_data['reward'] = 0 # Base reward for tile itself
        if 'guard_strength' not in graph_node_data: graph_node_data['guard_strength'] = 0
        graph.add_node(node, **graph_node_data)

    edges_data = [
        (hero_start_pos, (0,1), 100), (hero_start_pos, (1,0), 100),
        ((0,1), (1,1), 100), ((0,1), (0,2), 100),
        ((1,0), (1,1), 100), ((1,0), (2,0), 100),
        ((1,1), (2,1), 100), ((1,1), (1,2), 100),
        ((2,1), (2,0), 100), ((2,1), (2,2), 100),
        ((0,2), (1,2), 100), ((1,2), (2,2), 100)
    ]
    for u, v, w in edges_data:
        graph.add_edge(u,v, weight=w)

    hero = Hero(hero_id="cli_hero", pos=hero_start_pos, base_movement_points=300, army={"pikemen": 30}) # Army str 300
    combat_rho = 1.5

    # Ensure get_node_reward handles new gem value structure if used directly by planners
    # For now, relying on planner's internal calls to get_node_reward.

    sim = GameSimulator(graph=graph, heroes=[hero], combat_rho=combat_rho)
    return sim, hero.id

def load_game_state_from_json(file_path: str) -> Tuple[GameSimulator, str]:
    """
    Placeholder for loading game state from a JSON file.
    This would involve parsing the JSON into graph, hero objects, etc.
    For now, it will just return the sample game state.
    """
    print(f"Note: Loading from '{file_path}' is not yet implemented. Using sample state.")
    return setup_sample_game_state()

def main():
    parser = argparse.ArgumentParser(description="Heroes of Might and Magic III - Turn Advisor")
    parser.add_argument(
        "--planner",
        type=str,
        choices=["greedy", "astar", "mcts"],
        default="mcts",
        help="Planner algorithm to use."
    )
    parser.add_argument(
        "--statefile",
        type=str,
        default=None,
        help="Path to a JSON file representing the game state (not yet implemented)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="Planning horizon in days (for A* and MCTS)."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of iterations for MCTS."
    )
    parser.add_argument(
        "--mp",
        type=int,
        default=300,
        help="Hero's base movement points for the sample state."
    )
    parser.add_argument(
        "--army_units",
        type=int,
        default=30,
        help="Number of pikemen for the hero in the sample state (strength = units * 10)."
    )

    args = parser.parse_args()

    print(f"Starting Turn Advisor with planner: {args.planner.upper()}")

    if args.statefile:
        sim, hero_id = load_game_state_from_json(args.statefile)
    else:
        print("No state file provided, using a default sample game state.")
        sim, hero_id = setup_sample_game_state()
        # Adjust sample hero based on CLI args
        hero = sim.get_hero(hero_id)
        if hero:
            hero.base_movement_points = args.mp
            hero.current_movement_points = args.mp
            hero.army = {"pikemen": args.army_units}
            hero.recalculate_army_strength()
            print(f"Sample hero initialized with MP: {args.mp}, Army: {args.army_units} pikemen (Strength: {hero.get_army_strength()})")


    current_hero = sim.get_hero(hero_id)
    if not current_hero:
        print("Error: Could not retrieve hero from game state.")
        return

    print(f"Planning for Hero: {current_hero.id} at Pos: {current_hero.pos} with MP: {current_hero.current_movement_points}, Day: {sim.current_day}")

    start_time = time.time()
    suggested_action_or_path = None

    if args.planner == "greedy":
        # Greedy planner returns a path for the current turn based on available MP
        suggested_action_or_path = best_move_greedy(
            current_hero, sim.graph, sim.combat_rho
        )
        if suggested_action_or_path and len(suggested_action_or_path) > 1:
            suggested_action_or_path = ("move_path", suggested_action_or_path)
        else:
            suggested_action_or_path = ("wait", "No beneficial greedy move.")

    elif args.planner == "astar":
        astar_heuristic_cache.clear() # Clear cache for fresh run
        planned_path = a_star_planner(
            initial_hero=current_hero,
            graph=sim.graph,
            combat_rho=sim.combat_rho,
            max_days=args.days,
            base_daily_movement=current_hero.base_movement_points
        )
        if planned_path and len(planned_path) > 1:
            # A* returns a path. The first "action" is to follow this path.
            # We can take the first step of this path as the immediate action.
            suggested_action_or_path = ("move_path_astar", planned_path) # ("move", planned_path[1]) if only next step
        else:
            suggested_action_or_path = ("wait", "A* found no beneficial multi-day plan.")

    elif args.planner == "mcts":
        # MCTS planner should return an immediate best action from root
        mcts_heuristic_cache.clear() # Clear MCTS's heuristic cache if it uses one (A* one for now)
        suggested_action_or_path = mcts_planner(
            initial_sim_state=sim, # MCTS needs the full simulator state
            hero_id=hero_id,
            num_iterations=args.iterations,
            max_days_horizon=args.days, # MCTS plans up to this horizon
            exploration_constant=1.414
        )
        if not suggested_action_or_path:
             suggested_action_or_path = ("wait", "MCTS found no beneficial action.")


    end_time = time.time()
    planning_time = end_time - start_time

    print(f"\n--- Advice ({args.planner.upper()}) ---")
    if suggested_action_or_path:
        action_type = suggested_action_or_path[0]
        action_detail = suggested_action_or_path[1]
        print(f"Suggested Action Type: {action_type}")
        if isinstance(action_detail, list): # Path
            print(f"Suggested Path: {action_detail}")
            if len(action_detail) > 1:
                 print(f"Immediate next step: Move to {action_detail[1]}")
        else: # Simple action or message
            print(f"Details: {action_detail}")
    else:
        print("No specific action suggested. Consider waiting or manual exploration.")

    print(f"Planning Time: {planning_time:.4f} seconds")

if __name__ == "__main__":
    main()
```
