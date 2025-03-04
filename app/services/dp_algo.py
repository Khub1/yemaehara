from app.models import Lote, Aviario, Farmer
from flask import jsonify, request
from datetime import datetime, timedelta
import itertools, copy

def dp_algo():
    try:
        data = request.get_json()
        avi_ids = data.get('avi_ids')
        lote_ids = data.get('lote_ids')
        projection_time = data.get('projection_time')
        initial_date = datetime.strptime(data.get('initial_date'), '%Y-%m-%d').date()

        farmer = Farmer()
        farmer.fetch_aviaries(avi_ids)
        farmer.fetch_lotes(lote_ids)
        if not farmer.memo_aviaries or not farmer.memo_lotes:
            return jsonify({"error": "No aviaries or lotes found"}), 400
        print("Initial data fetched successfully")
        farmer.set_date(initial_date)

        for aviary in farmer.memo_aviaries.values():
            for lote in farmer.memo_lotes.values():
                if lote.plote_avi_id == aviary.avi_id:
                    aviary.allocated_lote = lote.plote_id
                    lote.plote_fase = aviary.avi_fase

        # Fresh DP table with (production, farmer, previous_system_state)
        dp = [{} for _ in range(projection_time + 1)]
        dp[0] = {tuple(): (0, farmer, None)}

        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            next_dp = {}
            for system_state, (production, farmer_state, prev_state) in dp[t - 1].items():
                farmer_clone = copy.deepcopy(farmer_state)
                farmer_clone.set_date(current_date)
                for new_system_state in generate_next_states(system_state, farmer_clone, t):
                    new_farmer = copy.deepcopy(farmer_clone)
                    new_production, updated_farmer = calculate_production(new_system_state, new_farmer)
                    total_production = production + new_production
                    if new_system_state in next_dp:
                        current_val = next_dp[new_system_state]
                        print(f"Comparing existing: {current_val[0]} (type: {type(current_val[0])}) with new: {total_production} (type: {type(total_production)})")
                        if not isinstance(current_val[0], (int, float)):
                            raise ValueError(f"Invalid type in next_dp: {type(current_val[0])}")
                    if new_system_state not in next_dp or next_dp[new_system_state][0] < total_production:
                        next_dp[new_system_state] = (total_production, updated_farmer, system_state)
            dp[t] = next_dp

        max_production, state_sequence = extract_optimal_solution(dp, projection_time)
        all_actions = [action for state in state_sequence for action in state]
        response = {
            "max_production": max_production,
            "optimal_state": [
                {"t": t, "aviary_id": aviary, "lote_id": lote, "action": action}
                for (t, aviary, lote, action) in all_actions
            ]
        }

        # Print max production first
        print(f"\nMaximum Production: {max_production}")

        # Generate and print the table
        print("\nOptimal State Transition Table:")
        print("-" * 150)
        print(f"{'t':<5} {'date':<12} {'aviary':<8} {'aviary type':<12} {'lote':<8} {'age (days)':<12} {'age (weeks)':<12} {'action':<16} {'pop before':<12} {'deaths':<8} {'pop now':<12} {'production':<12}")
        print("-" * 150)

        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            current_state = state_sequence[t - 1]
            current_farmer = dp[t][current_state][1]
            prev_farmer = dp[t-1][state_sequence[t-2]][1] if t > 1 else farmer

            for (time, aviary_id, lote_id, action) in current_state:
                aviary_type = current_farmer.memo_aviaries[aviary_id].avi_fase if aviary_id in current_farmer.memo_aviaries else "Unknown"
                if lote_id:
                    current_lote = current_farmer.memo_lotes.get(lote_id)
                    prev_lote = prev_farmer.memo_lotes.get(lote_id) if t > 1 else None
                    age_days = current_lote.plote_age_days if current_lote else "N/A"
                    age_weeks = current_lote.plote_age_weeks if current_lote else "N/A"
                    pop_before = current_lote.plote_cantidad if t == 1 else (prev_lote.plote_cantidad if prev_lote else current_lote.plote_cantidad)
                    deaths = current_lote.plote_deaths if current_lote else 0
                    pop_now = pop_before - deaths if current_lote else 0
                    production = current_lote.plote_production if current_lote else 0
                    # Ensure non-negative values
                    pop_before = max(0, pop_before)
                    deaths = max(0, deaths)
                    pop_now = max(0, pop_now)
                    production = max(0, production)
                else:
                    age_days = "N/A"
                    age_weeks = "N/A"
                    pop_before = "N/A"
                    deaths = "N/A"
                    pop_now = "N/A"
                    production = "N/A"

                # Determine action with transfer source
                if t == 1:
                    detailed_action = f"Initial ({action})"
                else:
                    prev_state = state_sequence[t - 2]
                    prev_action = action
                    for (prev_t, prev_aviary, prev_lote, prev_action_candidate) in prev_state:
                        if prev_lote == lote_id and prev_aviary == aviary_id:
                            prev_action = prev_action_candidate
                        elif prev_lote == lote_id and prev_action_candidate == "T":
                            prev_action = f"T (from {prev_aviary})"
                    detailed_action = prev_action

                print(f"{t:<5} {str(current_date):<12} {aviary_id:<8} {aviary_type:<12} {str(lote_id) if lote_id else 'None':<8} {str(age_days):<12} {str(age_weeks):<12} {detailed_action:<16} {str(pop_before):<12} {str(deaths):<8} {str(pop_now):<12} {str(production):<12}")
        print("-" * 150)

        return jsonify(response)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_next_states(system_state, farmer, t):
    """Generates all possible next system states for time step t."""
    aviary_combinations = []
    
    for aviary in farmer.memo_aviaries.values():
        possible_states = []
        if not aviary.allocated_lote and aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "D"))
        elif not aviary.allocated_lote and not aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "I"))
        for lote in farmer.memo_lotes.values():
            lote.set_plote_age()
            if lote.plote_avi_id == aviary.avi_id:
                if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))
                else:
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))
                if lote.plote_fase == "produccion":
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))
                if lote.plote_fase == "predescarte":
                    if lote.is_selling:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "S"))
                    else:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "S"))
        aviary_combinations.append(possible_states)
    
    unique_combinations = list({tuple(sorted(combination, key=lambda x: x[1])) for combination in itertools.product(*aviary_combinations)})
    for combination in unique_combinations:
        print(combination)
    return unique_combinations

def calculate_production(system_state, farmer):
    """Computes the total production for a given system state."""
    print(f"Calculating production for system state: {system_state}")
    total_production = 0
    for (t, aviary_id, lote_id, action) in system_state:
        lote = farmer.memo_lotes.get(lote_id)
        aviary = farmer.memo_aviaries.get(aviary_id)
        if action == "D":
            aviary.schedule_disinfection()
            print(f"Aviary {aviary_id} scheduled for disinfection")
        elif action == "I":
            aviary.set_inactivate()
            print(f"Aviary {aviary_id} inactivated")
        elif action == "R":
            print(f"Lote {lote_id} remains in aviary {aviary_id}")
        elif action == "T" or action == "S":
            print(f"Transferring lote {lote_id} to aviary {aviary_id}")
            farmer.transfer_lote(lote_id)
        else:
            print(f"Unknown action {action}")
    total_production = farmer.fetch_dynamics()
    print(f"Production for system state {system_state}: {total_production}")
    return total_production, farmer

def extract_optimal_solution(dp, projection_time):
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






        












