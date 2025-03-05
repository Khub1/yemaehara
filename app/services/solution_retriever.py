# app/services/solution_extractor.py

def retrieve_optimal_solution(dp: list, projection_time: int) -> tuple[float, list]:
    """
    Extracts the optimal solution from the dynamic programming table, returning the maximum production
    and the sequence of states that achieves it.

    Args:
        dp: A list of dictionaries where dp[t] maps system states to (production, farmer, prev_state) tuples.
        projection_time: The final time step of the simulation.

    Returns:
        A tuple (max_production, state_sequence) where:
            - max_production: The highest production value achieved.
            - state_sequence: A list of system states from t=1 to t=projection_time.

    Raises:
        ValueError: If no states exist at the final time step or if production values are invalid.
    """
    
    if not dp[projection_time]:
        raise ValueError(f"No states at final time step t={projection_time}")
    
    max_production = float('-inf')
    optimal_state = None
    print(f"Extracting solution at t={projection_time}, dp[{projection_time}] has {len(dp[projection_time])} states")
    
    for system_state, value in dp[projection_time].items():
        production, farmer, prev_state = value
        print(f"State={system_state}, Production={production} (type: {type(production)})")
        if not isinstance(production, (int, float)):
            raise ValueError(f"Invalid production type in dp[{projection_time}]: {type(production)}")
        if production > max_production:
            max_production = production
            optimal_state = system_state

    state_sequence = []
    current_state = optimal_state
    for t in range(projection_time, 0, -1):
        state_sequence.append(current_state)
        if t > 1:
            current_state = dp[t][current_state][2]
    state_sequence.reverse()

    return max_production, state_sequence