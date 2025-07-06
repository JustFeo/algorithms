"""
Simplified deterministic game simulator for HOMM3.
Focuses on hero movement, resource collection, and basic combat resolution.
"""
from typing import Dict, Any, Tuple, List, Optional
import networkx as nx
import os
import json # For loading potential map object definitions if needed

# Default combat proxy ratio (rho)
# Win if hero_power >= RHO * guard_power
DEFAULT_RHO = 1.5

class Hero:
    """Represents a hero in the game."""
    def __init__(self, hero_id: str, pos: Tuple[int, int], base_movement_points: int, army: Optional[Dict[str, int]] = None):
        self.id = hero_id
        self.pos = pos
        self.base_movement_points = base_movement_points # Max movement points at start of day
        self.current_movement_points = base_movement_points
        self.army = army if army else {} # {"creature_id": count}
        self.inventory = {"resources": {}, "artifacts": []} # {"gold": 1000}, ["boots_of_speed"]
        self.army_strength_cache = 0 # Cache for army strength
        self.recalculate_army_strength()

    def recalculate_army_strength(self):
        """
        Calculates the hero's army strength.
        This is a placeholder. Actual strength depends on creature stats, hero skills, artifacts.
        For now, let's assume each creature unit contributes 10 to strength.
        """
        strength = 0
        for count in self.army.values():
            strength += count * 10 # Simplified strength calculation
        self.army_strength_cache = strength
        return strength

    def get_army_strength(self) -> int:
        return self.army_strength_cache

    def add_creatures(self, creature_id: str, count: int):
        self.army[creature_id] = self.army.get(creature_id, 0) + count
        self.recalculate_army_strength()

    def remove_creatures(self, creature_id: str, count: int):
        self.army[creature_id] = max(0, self.army.get(creature_id, 0) - count)
        if self.army[creature_id] == 0:
            del self.army[creature_id]
        self.recalculate_army_strength()

    def add_resource(self, resource_type: str, amount: int):
        self.inventory["resources"][resource_type] = self.inventory["resources"].get(resource_type, 0) + amount

    def add_artifact(self, artifact_id: str):
        if artifact_id not in self.inventory["artifacts"]:
            self.inventory["artifacts"].append(artifact_id)
            # TODO: Apply artifact effects, e.g., movement bonus

    def reset_daily_movement(self):
        self.current_movement_points = self.base_movement_points
        # TODO: Adjust base_movement_points based on artifacts like Boots of Speed, Stables, etc.

    def __repr__(self):
        return (f"Hero(id={self.id}, pos={self.pos}, move_pts={self.current_movement_points}/{self.base_movement_points}, "
                f"army_str={self.get_army_strength()}, gold={self.inventory['resources'].get('gold', 0)})")


class GameSimulator:
    """
    Manages the game state and simulates hero actions.
    """
    def __init__(self, graph: nx.Graph, heroes: List[Hero], initial_day: int = 1, combat_rho: float = DEFAULT_RHO):
        self.graph = graph # NetworkX graph of the map
        self.heroes = {hero.id: hero for hero in heroes}
        self.current_day = initial_day
        self.active_hero_id: Optional[str] = heroes[0].id if heroes else None
        self.combat_rho = combat_rho
        self.game_log: List[str] = []

    def get_hero(self, hero_id: Optional[str] = None) -> Optional[Hero]:
        hid = hero_id if hero_id else self.active_hero_id
        if not hid:
            return None
        return self.heroes.get(hid)

    def log_action(self, message: str):
        self.game_log.append(f"Day {self.current_day}, Hero {self.active_hero_id}: {message}")
        print(f"Day {self.current_day}, Hero {self.active_hero_id}: {message}")


    def combat_proxy(self, hero_strength: int, guard_strength: int) -> bool:
        """
        Deterministic combat proxy.
        Returns True if hero wins, False otherwise.
        """
        if guard_strength == 0:
            return True # No guards, always win
        if hero_strength == 0 and guard_strength > 0:
            return False # No army, always lose if guards present
        return hero_strength >= self.combat_rho * guard_strength

    def step(self, hero_id: str, action: str, target_pos: Optional[Tuple[int, int]] = None, **kwargs) -> Dict[str, Any]:
        """
        Processes a single hero action.
        Updates hero state, game state, and potentially day counter.

        Args:
            hero_id (str): The ID of the hero performing the action.
            action (str): The action to perform (e.g., "move", "interact", "end_turn").
            target_pos (Optional[Tuple[int, int]]): Target position for "move" or "interact".
            **kwargs: Additional arguments for the action.

        Returns:
            Dict[str, Any]: Result of the action (e.g., {"status": "success", "reward": 100}).
        """
        self.active_hero_id = hero_id
        hero = self.get_hero(hero_id)
        if not hero:
            return {"status": "error", "message": f"Hero {hero_id} not found."}

        if action == "move":
            if not target_pos:
                return {"status": "error", "message": "Target position not specified for move."}
            if hero.pos == target_pos:
                self.log_action(f"Already at {target_pos}, no move needed.")
                return {"status": "success", "message": "Already at target."}

            if not self.graph.has_node(hero.pos) or not self.graph.has_node(target_pos):
                return {"status": "error", "message": "Invalid hero or target position in graph."}

            if not self.graph.has_edge(hero.pos, target_pos):
                 # Check if it's just one step away, if not, pathfinding would be needed for multi-step.
                 # This simulator's step() assumes single tile moves for now.
                 # For multi-tile moves, a planner would call this multiple times.
                is_adjacent = abs(hero.pos[0] - target_pos[0]) <= 1 and abs(hero.pos[1] - target_pos[1]) <=1
                if not is_adjacent:
                    return {"status": "error", "message": f"Target {target_pos} is not adjacent to {hero.pos} for a single move."}
                else: # Adjacent but no edge? Should not happen in a well-formed grid graph.
                    return {"status": "error", "message": f"No direct path (edge) from {hero.pos} to {target_pos}."}


            move_cost = self.graph.edges[hero.pos, target_pos].get('weight', 100) # Default high cost

            if hero.current_movement_points < move_cost:
                self.log_action(f"Not enough movement points to move from {hero.pos} to {target_pos} (needs {move_cost}, has {hero.current_movement_points}).")
                return {"status": "error", "message": "Not enough movement points."}

            # Check for guards at target_pos
            guard_strength = self.graph.nodes[target_pos].get('guard_strength', 0)
            if 'objects' in self.graph.nodes[target_pos]: # More detailed guard check
                current_guard_strength = 0
                for obj_at_target in self.graph.nodes[target_pos]['objects']:
                    if obj_at_target.get('type') == 'monster' or obj_at_target.get('type') == 'neutral_guard':
                        current_guard_strength += obj_at_target.get('strength', 0)
                guard_strength = current_guard_strength

            if guard_strength > 0:
                hero_strength = hero.get_army_strength()
                self.log_action(f"Encountered guards at {target_pos} (strength {guard_strength}). Hero strength: {hero_strength}.")
                if not self.combat_proxy(hero_strength, guard_strength):
                    self.log_action(f"Combat lost against guards at {target_pos}.")
                    # Option: end turn, or just can't move there. For now, can't move.
                    # Or hero loses some army and turn ends.
                    # Simplified: turn ends, movement points consumed for attempt.
                    hero.current_movement_points = 0
                    return {"status": "combat_lost", "message": "Lost combat with guards."}
                else:
                    self.log_action(f"Combat won against guards at {target_pos}! Guards removed (conceptually).")
                    # Remove guard from graph node (conceptually for this simulation pass)
                    # In a real game, this state change would be more complex.
                    self.graph.nodes[target_pos]['guard_strength'] = 0
                    # Remove monster objects from the tile
                    if 'objects' in self.graph.nodes[target_pos]:
                        self.graph.nodes[target_pos]['objects'] = [
                            obj for obj in self.graph.nodes[target_pos]['objects']
                            if not (obj.get('type') == 'monster' or obj.get('type') == 'neutral_guard')
                        ]
                    # Combat typically ends turn or consumes most movement
                    hero.current_movement_points = 0 # Simplified: combat ends movement for the day

            hero.pos = target_pos
            if hero.current_movement_points > 0: # if combat didn't end turn
                 hero.current_movement_points -= move_cost

            self.log_action(f"Moved to {target_pos}. Remaining movement: {hero.current_movement_points}.")

            # After moving, automatically interact with the new tile
            interaction_result = self.step(hero_id, "interact", target_pos)
            return {"status": "success", "message": f"Moved to {target_pos}.", "interaction": interaction_result}

        elif action == "interact":
            if not target_pos: target_pos = hero.pos # Interact with current tile if no target_pos

            if not self.graph.has_node(target_pos):
                return {"status": "error", "message": f"Target position {target_pos} not in graph."}

            tile_data = self.graph.nodes[target_pos]
            collected_rewards = {"resources": {}, "artifacts": [], "xp": 0, "other": []}

            # Iterate over a copy of objects list to allow modification
            objects_on_tile = list(tile_data.get("objects", []))
            new_objects_on_tile = [] # Objects that remain after interaction

            for obj in objects_on_tile:
                obj_type = obj.get("type")
                interacted = False
                if obj_type == "resource_pile":
                    res_type = obj.get("resource", "gold")
                    res_amount = obj.get("amount", 0)
                    hero.add_resource(res_type, res_amount)
                    collected_rewards["resources"][res_type] = collected_rewards["resources"].get(res_type, 0) + res_amount
                    self.log_action(f"Collected {res_amount} {res_type} at {target_pos}.")
                    interacted = True
                elif obj_type == "artifact":
                    art_id = obj.get("id", "unknown_artifact")
                    hero.add_artifact(art_id)
                    collected_rewards["artifacts"].append(art_id)
                    self.log_action(f"Collected artifact {art_id} at {target_pos}.")
                    interacted = True
                elif obj_type == "mine": # Flagging a mine
                    # For simplicity, assume flagging gives some abstract reward or changes state
                    mine_type = obj.get("mine_type", "unknown_mine")
                    self.log_action(f"Flagged {mine_type} at {target_pos}.")
                    # In a real game: mine now belongs to player, generates daily income.
                    # This would require player ownership model.
                    # For now, just log and maybe give one-time reward.
                    obj["owner"] = hero.id # Mark as flagged by this hero's player (conceptually)
                    collected_rewards["other"].append(f"flagged_{mine_type}")
                    new_objects_on_tile.append(obj) # Mine remains, but is flagged
                elif obj_type == "monster" or obj_type == "neutral_guard":
                    # Interaction with monsters is handled by move (combat)
                    # If hero is on this tile, it means guards were defeated or not present.
                    new_objects_on_tile.append(obj) # If somehow not cleared by move logic
                    pass
                else:
                    new_objects_on_tile.append(obj) # Object not interacted with or non-consumable

                # Most interactions (picking up resources/artifacts) consume movement or end turn
                if interacted:
                    hero.current_movement_points = 0 # Simplified: interaction ends movement

            # Update objects on tile
            self.graph.nodes[target_pos]["objects"] = new_objects_on_tile

            # Update tile's base reward if it's a one-time pickup spot
            # For now, assume rewards are tied to objects, and objects are removed.
            # If tile itself had a reward: tile_data["reward"] = 0

            if not collected_rewards["resources"] and not collected_rewards["artifacts"] and not collected_rewards["other"]:
                 self.log_action(f"No interactable objects found or action taken at {target_pos}.")
                 return {"status": "no_interaction", "message": "Nothing to interact with."}

            return {"status": "success", "rewards": collected_rewards}

        elif action == "end_turn":
            hero.current_movement_points = 0
            self.log_action("Turn ended.")
            # Logic to switch to next hero or next day would go here
            # For now, just end this hero's turn. Day progression is separate.
            return {"status": "success", "message": "Hero turn ended."}

        elif action == "wait":
            hero.current_movement_points = 0 # Waiting consumes rest of movement
            self.log_action("Waited.")
            return {"status": "success", "message": "Hero waited."}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def end_day(self):
        """Resets heroes' movement points and increments day counter."""
        self.current_day += 1
        self.log_action(f"Day {self.current_day} begins.")
        for hero in self.heroes.values():
            hero.reset_daily_movement()
            # TODO: Daily income from mines, town growth etc.
        self.active_hero_id = list(self.heroes.keys())[0] if self.heroes else None # Reset to first hero

# Example Usage (for testing the simulator directly)
if __name__ == "__main__":
    # Create a dummy graph for testing
    test_graph = nx.Graph()
    nodes_data = {
        (0,0): {"terrain_type": "grass", "objects": [{"type": "resource_pile", "resource": "gold", "amount": 100}], "reward": 100},
        (0,1): {"terrain_type": "dirt", "objects": [{"type": "artifact", "id": "boots_of_speed"}], "reward": 50},
        (1,0): {"terrain_type": "swamp", "objects": [], "reward": 0},
        (1,1): {"terrain_type": "grass", "objects": [{"type": "monster", "name": "Goblins", "strength": 30}], "reward": 0, "guard_strength": 30},
        (2,1): {"terrain_type": "grass", "objects": [{"type": "mine", "mine_type": "gold_mine"}], "reward": 0},
    }
    for node, data in nodes_data.items():
        test_graph.add_node(node, **data)

    test_graph.add_edge((0,0), (0,1), weight=100)
    test_graph.add_edge((0,0), (1,0), weight=100)
    test_graph.add_edge((0,1), (1,1), weight=100)
    test_graph.add_edge((1,0), (1,1), weight=175) # Swamp cost to enter (1,0) if edge was other way
                                                # or from (1,0) to (1,1) if (1,0) is swamp
    test_graph.add_edge((1,1), (2,1), weight=100)


    # Create a hero
    hero1 = Hero(hero_id="hero_A", pos=(0,0), base_movement_points=1500, army={"pikemen": 20}) # Army strength 200

    # Initialize simulator
    sim = GameSimulator(graph=test_graph, heroes=[hero1], combat_rho=1.5)

    print(f"Initial state: {sim.get_hero()}")
    print(f"Tile (0,0) objects: {sim.graph.nodes[(0,0)].get('objects')}")

    # Test move and collect gold
    sim.step("hero_A", "move", target_pos=(0,0)) # Should do nothing or auto-interact
    print(f"State after 'moving' to current pos: {sim.get_hero()}")
    print(f"Tile (0,0) objects: {sim.graph.nodes[(0,0)].get('objects')}")
    print(f"Gold: {sim.get_hero().inventory['resources'].get('gold')}")

    # Reset hero for next test sequence
    hero1 = Hero(hero_id="hero_A", pos=(0,0), base_movement_points=1500, army={"pikemen": 20})
    sim = GameSimulator(graph=test_graph, heroes=[hero1], combat_rho=1.5) # Re-init sim or reset hero state

    # Test move to (0,1) and collect artifact
    print("\n--- Test: Move to (0,1) and collect artifact ---")
    result = sim.step("hero_A", "move", target_pos=(0,1))
    print(f"Action result: {result}")
    print(f"State after move to (0,1): {sim.get_hero()}")
    print(f"Hero artifacts: {sim.get_hero().inventory['artifacts']}")
    print(f"Tile (0,1) objects: {sim.graph.nodes[(0,1)].get('objects')}") # Should be empty

    # Test move to (1,1) and fight guards
    print("\n--- Test: Move to (1,1) and fight guards ---")
    # Beef up hero army for this
    hero1.add_creatures("swordsmen", 10) # Total army strength now 200 (pike) + 100 (sword) = 300
    hero1.pos = (0,1) # Current position before moving to (1,1)
    hero1.reset_daily_movement() # Fresh movement
    print(f"Hero state before fighting: {hero1}")
    print(f"Tile (1,1) guards: {sim.graph.nodes[(1,1)].get('guard_strength')}, objects: {sim.graph.nodes[(1,1)].get('objects')}")

    result = sim.step("hero_A", "move", target_pos=(1,1))
    print(f"Action result: {result}")
    print(f"State after attempting move to (1,1): {sim.get_hero()}")
    print(f"Tile (1,1) guards after combat: {sim.graph.nodes[(1,1)].get('guard_strength')}, objects: {sim.graph.nodes[(1,1)].get('objects')}")

    # Test insufficient strength
    print("\n--- Test: Move to (1,1) with weak army ---")
    weak_hero = Hero(hero_id="hero_B", pos=(0,1), base_movement_points=1500, army={"peasants": 1}) # Strength 10
    # Need to re-init graph or reset guard strength for this test if it was modified
    test_graph.nodes[(1,1)]["guard_strength"] = 30
    test_graph.nodes[(1,1)]["objects"] = [{"type": "monster", "name": "Goblins", "strength": 30}]
    sim_weak = GameSimulator(graph=test_graph, heroes=[weak_hero], combat_rho=1.5)
    print(f"Weak hero state: {sim_weak.get_hero()}")
    result = sim_weak.step("hero_B", "move", target_pos=(1,1))
    print(f"Action result: {result}")
    print(f"State after attempting move to (1,1): {sim_weak.get_hero()}")

    # Test end day
    print("\n--- Test: End Day ---")
    sim.end_day()
    print(f"Hero state after end_day: {sim.get_hero()}") # hero1 from original sim
    print(f"Current day: {sim.current_day}")

    # Test flagging a mine
    print("\n--- Test: Flag a mine ---")
    hero1.pos = (1,1) # Assume hero is now at (1,1) after winning combat
    hero1.reset_daily_movement()
    print(f"Tile (2,1) objects before flagging: {sim.graph.nodes[(2,1)].get('objects')}")
    result = sim.step("hero_A", "move", target_pos=(2,1)) # This moves AND interacts
    print(f"Action result: {result}")
    print(f"State after moving to (2,1) and interacting: {sim.get_hero()}")
    print(f"Tile (2,1) objects after flagging: {sim.graph.nodes[(2,1)].get('objects')}") # Should show owner or be modified

    print("\n--- Log ---")
    for entry in sim.game_log[-10:]: # Print last 10 log entries
        print(entry)

```
