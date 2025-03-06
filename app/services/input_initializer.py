# app/services/input_validation.py
from app.models.farmer import Farmer

def init_adjust(farmer: Farmer) -> Farmer:
    """
    Initializes and validates the farmer's initial state by setting up lote assignments
    and correcting mismatches based on age and phase.

    Args:
        farmer: The Farmer instance to initialize.

    Returns:
        The adjusted Farmer instance.

    Raises:
        ValueError: If a lote has no valid age, exceeds capacity, or lacks a suitable aviary.
    """
    print("Starting initialization process...") 

    RECRIA_MAX_AGE = 19

    # Lists for reassignments and free aviaries
    reassign_to_production = []
    reassign_to_recria = []
    free_production_avi = []
    free_recria_avi = []

    # Step 1: Set ages for all lotes
    for lote in farmer.memo_lotes.values():
        lote.set_plote_age()
        if lote.plote_age_weeks is None:
            raise ValueError(f"Lote {lote.plote_id} has no valid age")
        print(f"Lote {lote.plote_id}: age={lote.plote_age_weeks}, avi_id={lote.plote_avi_id}")

    # Step 2: Validate initial assignments and categorize aviaries (preserve fetched state)
    for aviary in farmer.memo_aviaries.values():
        
        # Set initial fetched assignments explicitly
        for lote in farmer.memo_lotes.values():
            if lote.plote_avi_id == aviary.avi_id and aviary.allocated_lote is None:
                aviary.allocated_lote = lote.plote_id
                aviary.set_active()  # Mark as active for initial assignment
                print(f"Initial assignment: Lote {lote.plote_id} to aviary {aviary.avi_id}")

        if aviary.needs_disinfection:
            print(f"Aviary {aviary.avi_id} is under disinfection until {aviary.disinfection_due_date}")
        elif aviary.allocated_lote is None:  # Only truly empty aviaries are free
            if aviary.avi_fase.lower() == "recria":
                free_recria_avi.append(aviary)
                print(f"Aviary {aviary.avi_id} added to free recria aviaries")
            elif aviary.avi_fase.lower() == "produccion":
                free_production_avi.append(aviary)
                print(f"Aviary {aviary.avi_id} added to free production aviaries")

        # Validate assigned lotes without clearing yet
        if aviary.allocated_lote:
            lote = farmer.memo_lotes.get(aviary.allocated_lote)
            if lote.plote_cantidad > aviary.avi_capacidad_ideal:
                raise ValueError(f"Lote {lote.plote_id} (cantidad={lote.plote_cantidad}) exceeds capacity of aviary {aviary.avi_id} (capacidad={aviary.avi_capacidad_ideal})")
            
            aviary_phase = aviary.avi_fase.lower()
            if aviary_phase == "recria" and lote.plote_age_weeks >= RECRIA_MAX_AGE:
                print(f"Lote {lote.plote_id} exceeds age limit ({lote.plote_age_weeks} >= {RECRIA_MAX_AGE}) for recria aviary {aviary.avi_id}, marking for production")
                reassign_to_production.append((lote, aviary))
            elif aviary_phase in ("produccion", "predescarte") and lote.plote_age_weeks < RECRIA_MAX_AGE:
                print(f"Lote {lote.plote_id} below age limit ({lote.plote_age_weeks} < {RECRIA_MAX_AGE}) for {aviary_phase} aviary {aviary.avi_id}, marking for recria")
                reassign_to_recria.append((lote, aviary))
            else:
                lote.plote_fase = aviary.avi_fase
                print(f"Lote {lote.plote_id} validated in aviary {aviary.avi_id} in phase {aviary.avi_fase}")

    # Print initial assignments before any reassignment changes
    print("\nInitial Assignments Before Reassignment:")
    print("-" * 50)
    for aviary in farmer.memo_aviaries.values():
        lote_id = aviary.allocated_lote if aviary.allocated_lote else "None"
        status = "Active" if aviary.is_active else "Inactive"
        disinfection = "Yes" if aviary.needs_disinfection else "No"
        due_date = aviary.disinfection_due_date if aviary.needs_disinfection else "N/A"
        print(f"Aviary {aviary.avi_id} ({aviary.avi_fase}): Lote={lote_id}, Status={status}, Needs Disinfection={disinfection}, Due Date={due_date}")

    # Step 3: Clear mismatched aviaries
    for lote, source_aviary in reassign_to_production + reassign_to_recria:
        source_aviary.allocated_lote = None
        lote.plote_avi_id = None
        source_aviary.set_inactive()
        print(f"Cleared lote {lote.plote_id} from aviary {source_aviary.avi_id} for reassignment")

    # Step 4: Perform reassignments to free aviaries only
    for lote, _ in reassign_to_production:
        if free_production_avi:
            aviary = free_production_avi.pop()
            aviary.allocated_lote = lote.plote_id
            lote.plote_avi_id = aviary.avi_id
            lote.plote_fase = aviary.avi_fase
            aviary.set_active()
            print(f"Reassigned lote {lote.plote_id} to production aviary {aviary.avi_id}")
        else:
            raise ValueError(f"No available production aviary for lote {lote.plote_id} (age={lote.plote_age_weeks})")

    for lote, _ in reassign_to_recria:
        if free_recria_avi:
            aviary = free_recria_avi.pop()
            aviary.allocated_lote = lote.plote_id
            lote.plote_avi_id = aviary.avi_id
            lote.plote_fase = aviary.avi_fase
            aviary.set_active()
            print(f"Reassigned lote {lote.plote_id} to recria aviary {aviary.avi_id}")
        else:
            raise ValueError(f"No available recria aviary for lote {lote.plote_id} (age={lote.plote_age_weeks})")

    # Print assignments after reassignment
    print("\nAssignments After Reassignment:")
    print("-" * 50)
    for aviary in farmer.memo_aviaries.values():
        lote_id = aviary.allocated_lote if aviary.allocated_lote else "None"
        status = "Active" if aviary.is_active else "Inactive"
        disinfection = "Yes" if aviary.needs_disinfection else "No"
        due_date = aviary.disinfection_due_date if aviary.needs_disinfection else "N/A"
        print(f"Aviary {aviary.avi_id} ({aviary.avi_fase}): Lote={lote_id}, Status={status}, Needs Disinfection={disinfection}, Due Date={due_date}")

    print("Initialization process has been completed") 

    return farmer
        

        



    

