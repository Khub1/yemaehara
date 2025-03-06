# app/services/production_evaluator.py
from app.models import Farmer

def evaluate_dynamics(system_state, farmer: Farmer, raza_id: int = 24, pad_id: int = 231, buy_cantidad: int = 45000):
    """
    Evaluates the total production for a given system state by applying actions.
    """

    print(f"Evaluating production for system state: {system_state}")
    total_production = 0
    
    for (t, aviary_id, lote_id, action) in system_state:
            aviary = farmer.memo_aviaries.get(aviary_id)
            lote = farmer.memo_lotes.get(lote_id) if lote_id and lote_id != "NEW_LOTE" else None
            
            if action == "D":
                aviary.schedule_disinfection()
                print(f"Aviary {aviary_id} scheduled for disinfection")
            elif action == "I":
                aviary.set_inactive()
                print(f"Aviary {aviary_id} inactivated")
            elif action == "B":
                new_lote = farmer.buy_lote(raza_id, pad_id, buy_cantidad, id_escenario=1)
                farmer.allocate_lote(new_lote.plote_id, aviary_id)
                farmer.new_lote_map[(t, aviary_id, "NEW_LOTE", "B")] = new_lote.plote_id
                print(f"Bought and allocated new lote {new_lote.plote_id} to aviary {aviary_id}")
            elif action == "R":
                print(f"Lote {lote_id} remains in aviary {aviary_id}")
            elif action == "T" or action == "S":
                print(f"Transferring/selling lote {lote_id} from aviary {aviary_id}")
                farmer.transfer_lote(lote_id)
            else:
                print(f"Unknown action {action}")

    total_production = farmer.fetch_dynamics()
    print(f"Production for system state {system_state}: {total_production}")
    
    return total_production, farmer