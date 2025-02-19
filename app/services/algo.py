from app.models import Lote, Aviario, Farmer
from flask import jsonify, request
from datetime import datetime, timedelta
import itertools, copy


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

        # Initialize DP table
        dp = [{} for _ in range(projection_time + 1)]
        dp[0] = {(): 0}  # Initial state (empty system) with zero production

        #Initial aviary allocation set by database data
        for aviary in farmer.memo_aviaries.values():
            for lote in farmer.memo_lotes.values():
                if lote.plote_avi_id == aviary.avi_id:
                    aviary.allocated_lote = lote.plote_id
                    lote.plote_fase = aviary.avi_fase


        # Dynamic Programming process
        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            farmer.set_date(current_date)
            print(f"Processing time step {t} ({current_date})")
                
            next_dp = {}  # Next state storage

            for system_state, production in dp[t - 1].items():
                # Generate possible next system states and farmers clones for each to manage
                for new_system_state in generate_next_states(system_state, farmer, t):
                    farmer_clone = copy.deepcopy(farmer)
                    new_production = production + calculate_production(new_system_state, farmer_clone)[1]
                    farmer_clone = calculate_production(new_system_state, farmer_clone)[0]

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
    unique_combinations = list({tuple(sorted(combination, key=lambda x: x[1])) for combination in itertools.product(*aviary_combinations)})

    # Print unique combinations
    for combination in unique_combinations:
        print(combination)

    return unique_combinations


def calculate_production(system_state, farmer):
    """Computes the total production for a given system state."""
    print(f"Calculating production for system state: {system_state}")
    
    for (t, aviary_id, lote_id, action) in system_state:
        #print representation of the aviary
        lote = farmer.memo_lotes.get(lote_id)
        print(lote.__repr__())
        aviary = farmer.memo_aviaries.get(aviary_id)
        print(aviary.__repr__())

        if action == "D":
            aviary.schedule_disinfection()
            print(f"Aviary {aviary_id} scheduled for disinfection")
        elif action == "I":
            aviary.set_inactivate()
            print(f"Aviary {aviary_id} inactivated")
        elif action == "R":
            print(f"Lote {lote_id} remains in aviary {aviary_id}")  
            continue
        elif action == "T" or action == "S":
            print(f"Transferring lote {lote_id} to aviary {aviary_id}")
            farmer.transfer_lote(lote_id)


    # sys_production = farmer.fetch_dynamics()
    # print(f"System production: {sys_production}")

    # return farmer, sys_production


def extract_optimal_solution(dp, projection_time):
    """Finds the optimal state with max production from the DP results."""
    max_production = float('-inf')
    optimal_state = None

    for system_state, production in dp[projection_time].items():
        if production > max_production:
            max_production = production
            optimal_state = system_state

    return max_production, optimal_state



        












