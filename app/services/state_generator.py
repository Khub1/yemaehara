# app/services/state_generator.py
import itertools
from app.models import Farmer, Aviario, Lote

def generate_next_states(system_state, farmer: Farmer, t: int):
    """
    Generates all possible next system states for time step t, including buying new lotes with a 14-day restriction.
    
    Args:
        system_state: Tuple representing the current system state.
        farmer: Farmer instance with current aviaries and lotes.
        t: Current time step (assumed to be in days).
    
    Returns:
        List of tuples representing possible next states.
    """
    aviary_combinations = []
    
    # Check if a buy occurred within the last 14 days
    can_buy = True
    for (buy_t, _, _, buy_action) in farmer.new_lote_map.keys():
        if buy_action == "B" and t - buy_t < 14:  # Assuming t is in days
            can_buy = False
            break

    for aviary in farmer.memo_aviaries.values():
        possible_states = []
        if not aviary.allocated_lote and aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "D"))
        elif not aviary.allocated_lote and not aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "I"))
            if aviary.avi_fase == "recria" and aviary.avi_capacidad_ideal >= 60000 and can_buy:
                possible_states.append((t, aviary.avi_id, "NEW_LOTE", "B"))
    
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
        print(f"Generated state at t={t}: {combination}")
    return unique_combinations