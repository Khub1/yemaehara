# app/services/validation.py
from app.models import Farmer

def fix_init(farmer: Farmer):
    """
    Corrects initial lote placements in recria aviaries if their age exceeds 19 weeks.
    
    Args:
        farmer: Farmer instance with initial aviaries and lotes loaded.
    
    Returns:
        Farmer: Corrected Farmer instance with lotes reassigned as needed.
    
    Raises:
        ValueError: If no suitable production aviary is available for reassignment.
    """
    RECRIA_MAX_AGE = 19  # weeks

    # Step 1: Identify mismatches in recria aviaries
    reassignments = []
    for lote in farmer.memo_lotes.values():
        if lote.plote_avi_id:  # Only check assigned lotes
            # Ensure age is calculated
            lote.set_plote_age()
            print(f"Checking lote {lote.plote_id} in aviary {lote.plote_avi_id} with age {lote.plote_age_weeks} weeks")
            aviary = farmer.memo_aviaries.get(lote.plote_avi_id)
            if not aviary:
                continue  # Skip if aviary not found
            
            # Check if age is valid
            if lote.plote_age_weeks is None:
                raise ValueError(f"Lote {lote.plote_id} has no valid age (birth date missing)")
            
            if aviary.avi_fase == "recria" and lote.plote_age_weeks >= RECRIA_MAX_AGE:
                reassignments.append(lote)
                aviary.allocated_lote = None
                lote.plote_avi_id = None

    # Step 2: Reassign mismatched lotes to production aviaries
    for lote in reassignments:
        available_aviary = None
        for aviary in farmer.memo_aviaries.values():
            if (aviary.avi_fase == "produccion" and 
                not aviary.allocated_lote and 
                aviary.avi_capacidad_ideal >= lote.plote_cantidad and 
                not aviary.needs_disinfection):
                available_aviary = aviary
                break
        
        if not available_aviary:
            raise ValueError(f"No available production aviary for lote {lote.plote_id} with age {lote.plote_age_weeks} weeks")
        
        farmer.allocate_lote(lote.plote_id, available_aviary.avi_id)
        print(f"Corrected: Lote {lote.plote_id} (age {lote.plote_age_weeks}) moved to production aviary {available_aviary.avi_id}")

    return farmer

