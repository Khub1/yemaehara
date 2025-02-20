from app.models.batch import Lote
from app.models.aviary import Aviario
from app.utils.database import get_connection
from datetime import datetime, date

class Farmer:
    """Handles fetching and managing multiple Lote objects from the database"""
    def __init__(self):
        self.memo_aviaries = {}
        self.memo_lotes = {}

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
        """Allocate a lote to a different aviary if conditions are met"""
        lote = self.memo_lotes.get(lote_id)
        next_aviary = self.memo_aviaries.get(avi_id)
        previous_aviary= self.memo_aviaries.get(lote.plote_avi_id)

        # Set the old aviary to need disinfection
        if previous_aviary:
            previous_aviary.needs_disinfection = True
            previous_aviary.allocated_lote = None
            print(f"Aviary {previous_aviary.avi_id} needs disinfection")

        lote.plote_avi_id = avi_id
        next_aviary.allocated_lote = lote_id
        lote.plote_fase = next_aviary.avi_fase
        next_aviary.is_active = True
        print(f"Lote {lote_id} allocated to aviary {avi_id} in phase {lote.plote_fase}")

    def find_aviary(self, fase, lote):
        """Find available aviaries for a given phase and lote"""
        available_aviaries = []
        for aviary in self.memo_aviaries.values():
            if aviary.avi_fase == fase and aviary.allocated_lote is None:
                if aviary.is_active:
                    print(f"Aviary {aviary.avi_id} is active, cannot assign lote {lote.plote_id}")
                elif aviary.needs_disinfection:
                    print(f"Aviary {aviary.avi_id} needs disinfection, cannot assign lote {lote.plote_id}")
                elif lote.plote_cantidad > aviary.avi_capacidad_ideal:
                    print(f"Lote {lote.plote_id} population exceeds aviary {aviary.avi_id} capacity, cannot assign")
                else:
                    available_aviaries.append(aviary.avi_id)
        print(f"Available aviaries for {fase}: {available_aviaries}")
        return available_aviaries
    
    def transfer_lote(self, lote_id):
        """Transfer a lote to a target phase aviary if it meets the criteria"""
        lote = self.memo_lotes.get(lote_id)
        
        if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
            available_aviaries = self.find_aviary("produccion", lote)
            print(f"Available production aviaries for lote {lote_id}: {available_aviaries}")
            target_aviary_id = available_aviaries[0] if available_aviaries else None
            print(f"Set target production aviary for lote {lote_id}: {target_aviary_id}")
            if not target_aviary_id:
                print(f"No available production aviary found")
            else:
                self.allocate_lote(lote_id, target_aviary_id)
                print(f"Lote {lote_id} transferred to production aviary {target_aviary_id}")
                    
        if lote.plote_fase == "produccion":
            available_aviaries = self.find_aviary("predescarte", lote)
            print(f"Available predescarte aviaries for lote {lote_id}: {available_aviaries}")
            target_aviary_id = available_aviaries[0] if available_aviaries else None
            print(f"Set target predescarte aviary for lote {lote_id}: {target_aviary_id}")
            if not target_aviary_id:
                print(f"No available predescarte aviary found")
            else:
                self.allocate_lote(lote_id, target_aviary_id)
                print(f"Lote {lote_id} transferred to predescarte aviary {target_aviary_id}")

        if lote.plote_fase == "predescarte":
            #sell population 
            print(f"Selling population for lote {lote_id}")
            lote.sell_population()
            print(f"Lote {lote_id} sold")