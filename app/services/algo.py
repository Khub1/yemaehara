from app.models import Lote, Aviario, Farmer
from flask import jsonify, request
from datetime import datetime, timedelta

from app.models import Lote, Aviario, Farmer
from flask import jsonify, request
from datetime import datetime, timedelta

def dp_algo():
    """Service function to optimize aviary allocation using DP."""
    try:
        data = request.get_json()
        print("Received data:", data)  # Log the received data

        avi_ids = data.get('avi_ids')
        lote_ids = data.get('lote_ids')
        projection_time = data.get('projection_time')
        initial_date = datetime.strptime(data.get('initial_date'), '%Y-%m-%d').date()

        farmer = Farmer()
        report = {}
        dp = [{} for _ in range(projection_time + 1)]
        dp[0] = {(): (0, [])}  # Initial state with no assignments and zero production

        # Fetch all data initially
        farmer.fetch_aviaries(avi_ids)
        farmer.fetch_lotes(lote_ids)
        print("Fetched aviaries:", farmer.memo_aviaries)
        print("Fetched lotes:", farmer.memo_lotes)

        # If fetches return empty then error
        if not farmer.memo_aviaries or not farmer.memo_lotes:
            raise ValueError("No aviaries or lotes found")

        for t in range(1, projection_time + 1):
            current_date = initial_date + timedelta(days=t - 1)
            farmer.set_date(current_date)
            print(f"Current date set to: {current_date}")

            for state, (production, assignments) in dp[t - 1].items():
                for aviary in farmer.memo_aviaries.values():
                    for lote in farmer.memo_lotes.values():
                        if lote.plote_avi_id == aviary.avi_id:
                            # Option 1: Keep lote in the same aviary (R)
                            farmer.fetch_dynamics()
                            new_state = state + ((aviary.avi_id, lote.plote_id, "R"),)
                            new_production = production + lote.plote_production
                            new_assignments = assignments + [(t, aviary.avi_id, lote.plote_id, "R")]
                            dp[t][new_state] = (new_production, new_assignments)
                            print(f"Option 1: Keeping lote {lote.plote_id} in aviary {aviary.avi_id} with production {new_production}")

                            # Option 2: Transfer lote if phase transition is met (T)
                            target_phase = None
                            if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
                                target_phase = "produccion"
                            elif lote.plote_fase == "produccion":
                                target_phase = "predescarte"
                            
                            if target_phase:
                                target_aviary_ids = farmer.find_aviary(target_phase, lote)
                                if target_aviary_ids:
                                    new_aviary_id = target_aviary_ids[0]
                                    farmer.transfer_lote(lote.plote_id, new_aviary_id)
                                    farmer.fetch_dynamics()
                                    new_state = state + ((new_aviary_id, lote.plote_id, "T"),)
                                    new_production = production + lote.plote_production
                                    new_assignments = assignments + [(t, new_aviary_id, lote.plote_id, "T")]
                                    dp[t][new_state] = (new_production, new_assignments)
                                    print(f"Option 2: Transferred lote {lote.plote_id} to aviary {new_aviary_id} with production {new_production}")
                                elif target_phase == "produccion" and not target_aviary_ids:
                                    # Apply penalty only if transfer to "produccion" is not possible (TF)
                                    new_state = state + ((aviary.avi_id, lote.plote_id, "TF"),)
                                    new_production = production - 100000
                                    dp[t][new_state] = (new_production, assignments)
                                    print(f"Option 2: Penalized lote {lote.plote_id} in aviary {aviary.avi_id} with production {new_production}")

                            # Option 3: Sell lote if in predescarte phase (S)
                            if lote.plote_fase == "predescarte" or lote.is_selling:
                                lote.sell_population()
                                lote.is_selling = True
                                farmer.fetch_dynamics()
                                new_production = production + lote.plote_production  # Reduce production due to selling
                                new_state = state + ((aviary.avi_id, lote.plote_id, "S"),)
                                dp[t][new_state] = (new_production, new_assignments)
                                print(f"Option 3: Sold lote {lote.plote_id} in aviary {aviary.avi_id} with production {new_production}")
        

        #print the dp table but organized and understanble for a human 
        for t in range(projection_time + 1):
            print(f"Time {t}:")
            for state, (production, assignments) in dp[t].items():
                print(f"State: {state}, Production: {production}, Assignments: {assignments}")

        # Extract optimal solution
        max_production = 0
        optimal_assignments = []
        for state, (production, assignments) in dp[projection_time].items():
            if production > max_production:
                max_production = production
                optimal_assignments = assignments
        print(f"Max production: {max_production}")
        print(f"Optimal assignments: {optimal_assignments}")

        # Build the report
        for t, aviary_id, lote_id, action in optimal_assignments:
            if t not in report:
                report[t] = []
            aviary = farmer.memo_aviaries[aviary_id]
            lote = farmer.memo_lotes[lote_id]
            report[t].append({
                "date": aviary.date,
                "avi_id": aviary.avi_id,
                "avi_name": aviary.avi_name,
                "avi_state": aviary.is_active,
                "avi_desinfection_state": aviary.needs_disinfection,
                "avi_fase": aviary.avi_fase,
                "action": action,
                "avi_assigned_lote": {
                    "lote_id": lote.plote_id,
                    "lote_name": lote.plote_name,
                    "lote_age_days": lote.plote_age_days,
                    "lote_age_weeks": lote.plote_age_weeks,
                    "lote_cantidad": lote.plote_cantidad,
                    "lote_production": lote.plote_production,
                    "lote_deaths": lote.plote_deaths,
                    "lote_cvtadia": lote.plote_cvtadia
                }
            })

        return jsonify(report)

    except Exception as e:
        print("Error:", str(e))  # Log the error
        return jsonify({"error": str(e)}), 500


        












