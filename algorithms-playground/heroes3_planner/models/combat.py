"""
Models related to combat, including the combat proxy.
"""

# Default combat proxy ratio (rho)
# Win if hero_power >= RHO * guard_power
DEFAULT_RHO = 1.5

def combat_proxy_outcome(hero_army_strength: int, guard_army_strength: int, rho: float = DEFAULT_RHO) -> bool:
    """
    Determines the outcome of a battle using a simple proxy.

    Args:
        hero_army_strength (int): The calculated strength of the hero's army.
        guard_army_strength (int): The calculated strength of the guarding army.
        rho (float): The ratio factor. Hero wins if hero_strength >= rho * guard_strength.

    Returns:
        bool: True if the hero wins, False otherwise.
    """
    if guard_army_strength == 0:
        return True  # No guards, hero always wins
    if hero_army_strength == 0 and guard_army_strength > 0:
        return False # No army, hero always loses if guards are present

    return hero_army_strength >= rho * guard_army_strength

if __name__ == "__main__":
    # Example Usage
    strong_hero_power = 100
    weak_hero_power = 50
    guard_power = 60

    print(f"Strong hero ({strong_hero_power}) vs Guards ({guard_power}) with RHO={DEFAULT_RHO}: Win -> {combat_proxy_outcome(strong_hero_power, guard_power)}")
    print(f"Weak hero ({weak_hero_power}) vs Guards ({guard_power}) with RHO={DEFAULT_RHO}: Win -> {combat_proxy_outcome(weak_hero_power, guard_power)}")
    print(f"Hero ({strong_hero_power}) vs No Guards (0) with RHO={DEFAULT_RHO}: Win -> {combat_proxy_outcome(strong_hero_power, 0)}")
    print(f"No Army Hero (0) vs Guards ({guard_power}) with RHO={DEFAULT_RHO}: Win -> {combat_proxy_outcome(0, guard_power)}")

    custom_rho = 2.0
    print(f"Strong hero ({strong_hero_power}) vs Guards ({guard_power}) with RHO={custom_rho}: Win -> {combat_proxy_outcome(strong_hero_power, guard_power, custom_rho)}")
