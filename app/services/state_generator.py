# app/services/state_generator.py
import itertools
from app.models import Farmer, Aviario, Lote

def generate_next_states(system_state, farmer: Farmer, t: int):
    """
    Generates all possible next system states for time step t, including buying new lotes.
    
    Args:
        system_state: Tuple representing the current system state.
        farmer: Farmer instance with current aviaries and lotes.
        t: Current time step.
    
    Returns:
        List of tuples representing possible next states.
    """
    aviary_combinations = []

    # Track newly created lote IDs to avoid duplicates
    existing_lote_ids = set(farmer.memo_lotes.keys())
    new_lote_counter = max(existing_lote_ids, default=0) + 1 if existing_lote_ids else 1

    for aviary in farmer.memo_aviaries.values():
        possible_states = []
        # Disinfection state
        if not aviary.allocated_lote and aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "D"))
        # Idle or Buy state
        elif not aviary.allocated_lote and not aviary.needs_disinfection:
            possible_states.append((t, aviary.avi_id, None, "I"))
            if aviary.avi_fase == "recria" and aviary.avi_capacidad_ideal >= 60000:  # Default buy_cantidad
                possible_states.append((t, aviary.avi_id, "NEW_LOTE", "B"))  # Placeholder for new lote

        # Existing lote actions
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