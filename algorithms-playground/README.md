# Algorithms Playground - Heroes 3 Planner

This project aims to create a turn advisor for Heroes of Might and Magic III, using the VCMI engine.

## Project Structure

- `heroes3_planner/`: Core Python library for the planner.
  - `data/`: For map exports and game data.
  - `models/`: For combat proxy, reward functions, etc.
  - `planners/`: Different planning algorithms (greedy, A*, MCTS).
    - `greedy.py`
    - `astar.py`
    - `mcts.py`
  - `simulator.py`: Simplified game simulator.
  - `tests/`: Unit and integration tests.
- `notebooks/`: Jupyter notebooks for experiments and analysis.
  - `experiments.ipynb`
- `vcmi_bridge/`: Lua or REST scripts for VCMI integration.
- `README.md`: This file.

## CI & Linting

- `pytest` for testing.
- `coverage.py` for test coverage.
- `black` for code formatting.
- `flake8` for linting.
- Pre-commit hooks manage these tools.

## Roadmap
(Refer to the original problem description for the detailed roadmap)

1.  **Data Layer:** Export map data, build graph.
2.  **Simulator Stub:** Basic hero state updates, combat proxy.
3.  **Baseline Greedy:** Implement greedy planner.
4.  **Heuristic Search:** A* planner.
5.  **MCTS Refinement:** MCTS planner.
6.  **Integration:** VCMI bridge.
7.  **Evaluation:** Benchmarking.
8.  **Polish:** Documentation and presentation.
