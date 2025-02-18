from app.models import Lote, Aviario, Farmer
from flask import jsonify, request
from datetime import datetime, timedelta
import itertools

def dp_algo():
    """Flask service function to optimize aviary allocation using DP."""
    try:
        data = request.get_json()

        avi_ids = data.get('avi_ids')
        lote_ids = data.get('lote_ids')
        projection_time = data.get('projection_time')
        initial_date = datetime.strptime(data.get('initial_date'), '%Y-%m-%d').date()

        farmer = Farmer()
        farmer.fetch_aviaries(avi_ids)
        farmer.fetch_lotes(lote_ids)


        # If fetches return empty, return an error
        if not farmer.memo_aviaries or not farmer.memo_lotes:
            return jsonify({"error": "No aviaries or lotes found"}), 400
        else:
            print("Initial data fetched successfully")

        #Initial aviary allocation set by database data
        for aviary in farmer.memo_aviaries.values():
            for lote in farmer.memo_lotes.values():
                if lote.plote_avi_id == aviary.avi_id:
                    aviary.allocated_lote = lote.plote_id
                    lote.plote_fase = aviary.avi_fase


        # Initialize DP table
        dp = [{} for _ in range(projection_time + 1)]
        dp[0] = {(): 0}  # Initial state (empty system) with zero production

        # Dynamic Programming process
        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            farmer.set_date(current_date)
            print(f"Processing time step {t} ({current_date})")
                
            next_dp = {}  # Next state storage

            for system_state, production in dp[t - 1].items():
                # Generate possible next system states
                for new_system_state in generate_next_states(system_state, farmer, t):
                    new_production = calculate_production(new_system_state, farmer)

                    # Store the best production for this state
                    if new_system_state not in next_dp or next_dp[new_system_state] < new_production:
                        next_dp[new_system_state] = new_production

            # Move to next time step
            dp[t] = next_dp

        # Extract the best solution
        max_production, optimal_state = extract_optimal_solution(dp, projection_time)

        # Build response
        response = {
            "max_production": max_production,
            "optimal_state": [
                {"t": t, "aviary_id": aviary, "lote_id": lote, "action": action}
                for (t, aviary, lote, action) in optimal_state
            ]
        }

        return jsonify(response)

    except Exception as e:
        print("Error:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500


# 🔹 Helper Functions

def generate_next_states(system_state, farmer, t):
    """Generates all possible next system states for time step t."""
    aviary_combinations = []
    
    for aviary in farmer.memo_aviaries.values():
        
        print(f"Processing possible state combinations for aviary {aviary.avi_id} at time step {t} ...")
        possible_states = []

        if not aviary.allocated_lote and aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "D"))  # Disinfect
        elif not aviary.allocated_lote and not aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "I"))  # Inactivate
        


        for lote in farmer.memo_lotes.values():

            lote.set_plote_age() # Update lote age
            
            if lote.plote_avi_id == aviary.avi_id:

                if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))  # Transfer
                else:
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))  # Remain

                if lote.plote_fase == "produccion":
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))  # Remain
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))  # Transfer

                if lote.plote_fase == "predescarte":
                    if lote.is_selling:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "S"))  # Sell
                    else:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "R")) # Remain
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "S")) # Sell

        aviary_combinations.append(possible_states)
        

    # Generate all valid system state combinations
    all_combinations = itertools.product(*aviary_combinations)

    # Convert to set to ensure uniqueness
    unique_combinations = {tuple(combination) for combination in all_combinations if len(combination) == len(farmer.memo_aviaries)}

    # Print unique combinations
    for combination in unique_combinations:
        print(combination)

    return list(unique_combinations)


def calculate_production(system_state, farmer):
    """Computes the total production for a given system state."""
    total_production = 0
    
    for (t, aviary_id, lote_id, action) in system_state:
        if lote_id and action in ["R", "T"]:
            lote = farmer.memo_lotes[lote_id]
            total_production += lote.plote_production

        if action == "TF":  # Transfer Failed penalty
            total_production -= 100000

    return total_production


def extract_optimal_solution(dp, projection_time):
    """Finds the optimal state with max production from the DP results."""
    max_production = float('-inf')
    optimal_state = None

    for system_state, production in dp[projection_time].items():
        if production > max_production:
            max_production = production
            optimal_state = system_state

    return max_production, optimal_state



        












