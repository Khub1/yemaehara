from app.models.batch import Lote
from app.models.aviary import Aviario
from app.utils.database import get_connection
from datetime import datetime, date

class Farmer:
    """Handles fetching and managing multiple Lote objects from the database"""
    def __init__(self):
        self.memo_aviaries = {}
        self.memo_lotes = {}
        self.new_lote_map = {}

    def fetch_aviaries(self, avi_ids):
        """Retrieve aviaries by avi_ids or by matching avi_blo_id with blo_id from m_prm_bloques"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                if avi_ids:
                    placeholders = ",".join(["?" for _ in avi_ids])
                    query = f"SELECT * FROM m_prm_aviarios WHERE avi_id IN ({placeholders})"
                    cursor.execute(query, avi_ids)
                else:
                    return []
                aviaries = cursor.fetchall()
                for aviary in aviaries:
                    AviarioX = Aviario(aviary.avi_id)
                    AviarioX.avi_name = aviary.avi_name
                    AviarioX.avi_capacidad_ideal = aviary.avi_capacidad_ideal
                    AviarioX.needs_disinfection = (aviary.avi_desf_est == 1)
                    fase_map = {
                        aviary.avi_recria: "recria",
                        aviary.avi_produccion: "produccion",
                        aviary.avi_predescarte: "predescarte"
                    }
                    AviarioX.avi_fase = fase_map.get(1, "unknown")
                    self.memo_aviaries[AviarioX.avi_id] = AviarioX
                return self.memo_aviaries
        except Exception as e:
            print(f"Database error: {str(e)}")
            return self.memo_aviaries

    def fetch_lotes(self, plote_ids):
        """Retrieve multiple Lote objects by a list of IDs"""
        if not plote_ids:
            return []
        placeholders = ",".join(["?" for _ in plote_ids])
        query = f"""
            SELECT plote_id, plote_name, plote_raza_id, plote_pad_id, id_escenario, plote_eprod, 
            plote_fnac_a, plote_fnac_b, plote_fprod, plote_avi_id, plote_cantidad, plote_cvtadia
            FROM m_prm_pro_lotes 
            WHERE plote_id IN ({placeholders})
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, plote_ids)
                lotes = cursor.fetchall()
                for lote in lotes:
                    LoteX = Lote(lote.plote_raza_id, lote.plote_pad_id, lote.plote_cantidad)
                    LoteX.plote_id = lote.plote_id
                    LoteX.plote_name = lote.plote_name
                    LoteX.plote_fnac_a = lote.plote_fnac_a
                    LoteX.plote_fnac_b = lote.plote_fnac_b
                    LoteX.plote_fprod = lote.plote_fprod
                    LoteX.plote_avi_id = lote.plote_avi_id
                    LoteX.plote_cvtadia = lote.plote_cvtadia
                    self.memo_lotes[LoteX.plote_id] = LoteX
                return self.memo_lotes
        except Exception as e:
            print(f"Database error: {str(e)}")
            return []
        
    def buy_lote(self, raza_id, pad_id, cantidad):
        """Create a new Lote object and save it to the database using"""
        new_lote = Lote(raza_id, pad_id, cantidad)
        new_lote._set_plote_id()
        new_lote._set_plote_name()
        new_lote._set_plote_fnac()
        new_lote._set_plote_fprod()
        new_lote._set_plote_cvtadia()
        new_lote._save_to_db()
        self.memo_lotes[new_lote.plote_id] = new_lote
        return new_lote

    def set_date(self, date):
        """Set the system date for all aviaries and lotes"""
        for aviary in self.memo_aviaries.values():
            aviary.date = date
        for lote in self.memo_lotes.values():
            lote.plote_date = date

    def fetch_dynamics(self):
        """Fetch and update the dynamics for all lotes"""
        agg_production = 0
        for lote in self.memo_lotes.values():
            #print representation of the lote
            print(lote.__repr__())
            lote.fetch_bios()
            dynamics = lote.population_dynamics()
            agg_production += dynamics[0]

        return agg_production

    def allocate_lote(self, lote_id, avi_id):
        lote = self.memo_lotes.get(lote_id)
        next_aviary = self.memo_aviaries.get(avi_id)
        previous_aviary = self.memo_aviaries.get(lote.plote_avi_id)

        if previous_aviary:
            previous_aviary.allocated_lote = None
            previous_aviary.set_inactivate()  # Schedules disinfection and sets due date
            print(f"Aviary {previous_aviary.avi_id} scheduled for disinfection")

        lote.plote_avi_id = avi_id
        next_aviary.allocated_lote = lote_id
        lote.plote_fase = next_aviary.avi_fase
        next_aviary.is_active = True
        print(f"Lote {lote_id} allocated to aviary {avi_id} in phase {lote.plote_fase}")

    def find_aviary(self, fase, lote):
        available_aviaries = []
        for aviary in self.memo_aviaries.values():
            if aviary.avi_fase == fase and aviary.allocated_lote is None:
                if aviary.needs_disinfection:
                    if aviary.check_disinfection_due():
                        aviary.needs_disinfection = False  # Disinfection complete
                    else:
                        print(f"Aviary {aviary.avi_id} is under disinfection until {aviary.disinfection_due_date}")
                        continue
                if aviary.is_active:
                    print(f"Aviary {aviary.avi_id} is active, cannot assign lote {lote.plote_id}")
                    continue
                if lote.plote_cantidad > aviary.avi_capacidad_ideal:
                    print(f"Lote {lote.plote_id} exceeds capacity of aviary {aviary.avi_id}")
                    continue
                available_aviaries.append(aviary.avi_id)
        print(f"Available aviaries for {fase}: {available_aviaries}")
        return available_aviaries
    
    def transfer_lote(self, lote_id):
        lote = self.memo_lotes.get(lote_id)
        if not lote:
            return  # Invalid lote
        
        if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
            available_aviaries = self.find_aviary("produccion", lote)
            target_aviary_id = available_aviaries[0] if available_aviaries else None
            if target_aviary_id:
                self.allocate_lote(lote_id, target_aviary_id)
                        
        if lote.plote_fase == "produccion":
            available_aviaries = self.find_aviary("predescarte", lote)
            target_aviary_id = available_aviaries[0] if available_aviaries else None
            if target_aviary_id:
                self.allocate_lote(lote_id, target_aviary_id)

        if lote.plote_fase == "predescarte":
            print(f"Selling population for lote {lote_id}")
            lote.sell_population()
            if lote.plote_cantidad <= 0:
                aviary = self.memo_aviaries.get(lote.plote_avi_id)
                if aviary:
                    aviary.allocated_lote = None
                    aviary.set_inactivate()  # Trigger disinfection
                    print(f"Aviary {aviary.avi_id} scheduled for disinfection after selling lote {lote_id}")
            print(f"Lote {lote_id} sold")

    def buy_lote(self, raza_id, pad_id, cantidad=60000):
        """Create a new Lote object by using set_lote_instantiation"""
        new_lote = Lote(raza_id, pad_id, cantidad)
        new_lote.set_lote_instantiation()
        self.memo_lotes[new_lote.plote_id] = new_lote

    def reset_new_lote_map(self):
        """Reset the new_lote_map to an empty dictionary"""
        self.new_lote_map = {}
