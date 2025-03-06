from app.models import Farmer
from flask import jsonify, request
from datetime import datetime, timedelta
import copy
from app.services.state_generator import generate_next_states
from app.services.dynamics_evaluator import evaluate_dynamics
from app.services.solution_retriever import retrieve_optimal_solution
from app.services.input_initializer import init_adjust

def dp_algo():
    try:
        data = request.get_json()
        avi_ids = data.get('avi_ids')
        lote_ids = data.get('lote_ids')
        projection_time = data.get('projection_time')
        initial_date = datetime.strptime(data.get('initial_date'), '%Y-%m-%d').date()
        raza_id = data.get('raza_id', 1)
        pad_id = data.get('pad_id', 1)
        buy_cantidad = data.get('buy_cantidad', 60000)

        farmer = Farmer()
        farmer.fetch_aviaries(avi_ids)
        farmer.fetch_lotes(lote_ids)
        if not farmer.memo_aviaries or not farmer.memo_lotes:
            return jsonify({"error": "No aviaries or lotes found"}), 400
        print("Initial data fetched successfully")
        farmer.set_date(initial_date)
        farmer.reset_new_lote_map()  # Reset new_lote_map before simulation

        farmer = init_adjust(farmer)


        dp = [{} for _ in range(projection_time + 1)]
        dp[0] = {tuple(): (0, farmer, None)}

        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            next_dp = {}
            for system_state, (production, farmer_state, prev_state) in dp[t - 1].items():
                farmer_clone = copy.deepcopy(farmer_state)
                farmer_clone.set_date(current_date)
                for new_system_state in generate_next_states(farmer_clone, t):
                    new_farmer = copy.deepcopy(farmer_clone)
                    new_production, updated_farmer = evaluate_dynamics(new_system_state, new_farmer, raza_id, pad_id, buy_cantidad)
                    total_production = production + new_production
                    if new_system_state not in next_dp or next_dp[new_system_state][0] < total_production:
                        next_dp[new_system_state] = (total_production, updated_farmer, system_state)
            dp[t] = next_dp

        max_production, state_sequence = retrieve_optimal_solution(dp, projection_time)
        
        # Build the table as a list of rows for JSON response
        table_data = []
        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            current_state = state_sequence[t - 1]
            current_farmer = dp[t][current_state][1]
            prev_farmer = dp[t-1][state_sequence[t-2]][1] if t > 1 else farmer

            for (time, aviary_id, lote_id, action) in current_state:
                if lote_id == "NEW_LOTE" and action == "B":
                    lote_id = current_farmer.new_lote_map.get((t, aviary_id, "NEW_LOTE", "B"), "Unknown")

                aviary_type = current_farmer.memo_aviaries[aviary_id].avi_fase if aviary_id in current_farmer.memo_aviaries else "Unknown"
                if lote_id and lote_id != "Unknown":
                    current_lote = current_farmer.memo_lotes.get(lote_id)
                    prev_lote = prev_farmer.memo_lotes.get(lote_id) if t > 1 else None
                    age_days = current_lote.plote_age_days if current_lote else "N/A"
                    age_weeks = current_lote.plote_age_weeks if current_lote else "N/A"
                    pop_before = current_lote.plote_cantidad if t == 1 else (prev_lote.plote_cantidad if prev_lote else current_lote.plote_cantidad)
                    deaths = current_lote.plote_deaths if current_lote else 0
                    pop_now = pop_before - deaths if current_lote else 0
                    production = current_lote.plote_production if current_lote else 0
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

                row = {
                    "t": t,
                    "date": str(current_date),
                    "aviary": aviary_id,
                    "aviary_type": aviary_type,
                    "lote": str(lote_id) if lote_id else "None",
                    "age_days": str(age_days),
                    "age_weeks": str(age_weeks),
                    "action": detailed_action,
                    "pop_before": str(pop_before),
                    "deaths": str(deaths),
                    "pop_now": str(pop_now),
                    "production": str(production)
                }
                table_data.append(row)

        response = {
            "max_production": max_production,
            "optimal_solution_table": table_data
        }

        # Print for debugging (optional)
        print(f"\nMaximum Production: {max_production}")
        print("\nOptimal State Transition Table:")
        print("-" * 150)
        print(f"{'t':<5} {'date':<12} {'aviary':<8} {'aviary type':<12} {'lote':<8} {'age (days)':<12} {'age (weeks)':<12} {'action':<16} {'pop before':<12} {'deaths':<8} {'pop now':<12} {'production':<12}")
        print("-" * 150)
        for row in table_data:
            print(f"{row['t']:<5} {row['date']:<12} {row['aviary']:<8} {row['aviary_type']:<12} {row['lote']:<8} {row['age_days']:<12} {row['age_weeks']:<12} {row['action']:<16} {row['pop_before']:<12} {row['deaths']:<8} {row['pop_now']:<12} {row['production']:<12}")
        print("-" * 150)

        return jsonify(response)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        













        












