from app.models import Lote
from app.models import Aviario
from app.models import Farmer 
from flask import jsonify, request
from datetime import datetime

def dp_algo():
    """Service function to test get_aviaries method of Farmer """
    data = request.get_json()
    avi_ids = data.get('avi_ids')
    lote_ids = data.get('lote_ids')
    projection_time = data.get('projection_time')

    farmer = Farmer()
    report = {}
    dp = [{} for _ in range(projection_time + 1)]
    dp[0] = {(): (0, [])}  # Initial state with no assignments and zero production

    for t in range(1, projection_time + 1):
        if t == 1:
            farmer.fetch_aviaries(avi_ids)
            farmer.fetch_lotes(lote_ids)
            farmer.lote_to_aviary()
            farmer.set_lote_fases()
            farmer.set_system_date(datetime.now().date())
            farmer.fetch_lote_dynamics()
        
        for state, (production, assignments) in dp[t - 1].items():
            for aviary in farmer.memo_aviaries.values():
                for lote in farmer.memo_lotes.values():
                    if lote.plote_avi_id == aviary.avi_id:
                        # Create a new state by adding the new assignment
                        new_state = state + ((aviary.avi_id, lote.plote_id),)
                        new_production = production + lote.plote_production
                        new_assignments = assignments + [(t, aviary.avi_id, lote.plote_id)]
                        # Update the DP table with the new state and production
                        if new_state not in dp[t] or dp[t][new_state][0] < new_production:
                            dp[t][new_state] = (new_production, new_assignments)

    # Find the optimal solution
    max_production = 0
    optimal_assignments = []
    for state, (production, assignments) in dp[projection_time].items():
        if production > max_production:
            max_production = production
            optimal_assignments = assignments

    # Build the report based on the optimal assignments
    for t, aviary_id, lote_id in optimal_assignments:
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
            









