import itertools
from app.models import Farmer

def generate_next_states(farmer: Farmer, t: int):
    """
    Generates all possible next system states for time step t, including buying new lotes with a 14-day restriction.
    
    Args:
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
            if lote.plote_avi_id == aviary.avi_id:
                lote.set_plote_age()  # Update lote age based on current date/time step
                if aviary.avi_fase == "recria":
                    if lote.plote_age_weeks < 19:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))
                    else:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))
                elif aviary.avi_fase == "produccion":
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))  # Always allow remain
                    if lote.plote_age_weeks >= 67:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "T"))  # Allow transfer if age >= 67
                elif aviary.avi_fase == "predescarte":
                    possible_states.append((t, aviary.avi_id, lote.plote_id, "R"))
                    if lote.is_selling:
                        possible_states.append((t, aviary.avi_id, lote.plote_id, "S"))
        aviary_combinations.append(possible_states)
    
    unique_combinations = list({tuple(sorted(combination, key=lambda x: x[1])) for combination in itertools.product(*aviary_combinations)})
    return unique_combinations