from app.models.batch import Lote
from app.models.aviary import Aviario
from app.utils.database import get_connection
import pandas as pd
from datetime import datetime, date
import pprint as pp

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
                aviaries_list = {}
                for aviary in aviaries:
                    AviarioX = Aviario(
                        aviary.avi_id
                    )
                    AviarioX.avi_name=aviary.avi_name,
                    AviarioX.avi_capacidad_autorizada=aviary.avi_capacidad_autorizada
                    fase_map = {
                        aviary.avi_recria: "recria",
                        aviary.avi_produccion: "produccion",
                        aviary.avi_predescarte: "predescarte"
                    }
                    AviarioX.avi_fase = fase_map.get(1, "unknown")
                    aviaries_list[AviarioX.avi_id] = AviarioX
                self.memo_aviaries = aviaries_list
                return 

        except Exception as e:
            print(f"Database error: {str(e)}")
            return self.memo_aviaries

    def fetch_lotes(self, plote_ids):
            """Retrieve multiple Lote objects by a list of IDs"""
            if not plote_ids:
                return []

            placeholders = ",".join(["?" for _ in plote_ids])  # Create ?,?,? for SQL query
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
                    lotes_list = {}
                    for lote in lotes:
                        LoteX = Lote(
                            lote.plote_raza_id,
                            lote.plote_pad_id,
                            lote.plote_cantidad
                        )
                        LoteX.plote_id = lote.plote_id
                        LoteX.plote_name = lote.plote_name
                        LoteX.plote_fnac_a = lote.plote_fnac_a
                        LoteX.plote_fnac_b = lote.plote_fnac_b
                        LoteX.plote_fprod = lote.plote_fprod
                        LoteX.plote_avi_id = lote.plote_avi_id
                        LoteX.plote_cvtadia = lote.plote_cvtadia
                        lotes_list[LoteX.plote_id] = LoteX

                    self.memo_lotes = lotes_list
                    print(f"memo_lotes: {self.memo_lotes}")
                    return 
            except Exception as e:
                print(f"Database error: {str(e)}")
                return []
    
    def lote_to_aviary(self):
        for aviary in self.memo_aviaries.values():
            for lote in self.memo_lotes.values():
                if lote.plote_avi_id == aviary.avi_id:
                    aviary.assigned_lote = lote.plote_id
                    print(f"Lote {lote.plote_id} assigned to aviary {aviary.avi_id}")

    def set_lote_fases(self):
        for aviary in self.memo_aviaries.values():
            for lote in self.memo_lotes.values():
                if lote.plote_avi_id == aviary.avi_id:
                    lote.plote_fase = aviary.avi_fase
                    print(f"Lote {lote.plote_id} in phase {lote.plote_fase} within aviary {aviary.avi_id}")

    def set_system_date(self, date):
        for aviary in self.memo_aviaries.values():
            aviary.date = date
        for lote in self.memo_lotes.values():
            lote.plote_date = date
        return 
    
    def fetch_lote_dynamics(self):
        for lote in self.memo_lotes.values():
            # force population dynamics
            lote.set_plote_age()
            lote.fetch_bios()
            lote.population_dynamics()

    def build_report(self):
        report = {}
        for aviary in self.memo_aviaries.values():
            lote = self.memo_lotes.get(aviary.assigned_lote)
            report[len(report) + 1] = {
                "date": aviary.date,
                "avi_id": aviary.avi_id,
                "avi_name": aviary.avi_name,
                "avi_state": aviary.is_active,
                "avi_desinfection_state": aviary.needs_disinfection,
                "avi_fase": aviary.avi_fase,
                "avi_assigned_lote": {
                    "lote_id": lote.plote_id if lote else None,
                    "lote_name": lote.plote_name if lote else None,
                    "lote_age_days": lote.plote_age_days if lote else None,
                    "lote_age_weeks": lote.plote_age_weeks if lote else None,
                    "lote_cantidad": lote.plote_cantidad if lote else None,
                    "lote_production": lote.plote_production if lote else None,
                    "lote_deaths": lote.plote_deaths if lote else None,
                    "lote_cvtadia": lote.plote_cvtadia if lote else None
                }
            }
        return print("Report built")

    def move_lote(self, lote_id, avi_id):
        lote = self.memo_lotes.get(lote_id)
        aviary = self.memo_aviaries.get(avi_id)
        if aviary.is_active:
            return print(f"Aviary {avi_id} is active, cannot move lote {lote_id}")
        else:
            if aviary.needs_disinfection:
                return print(f"Aviary {avi_id} needs disinfection, cannot move lote {lote_id}")
            else:   
                lote.plote_avi_id = avi_id
                aviary.assigned_lote = lote_id
                return print(f"Lote {lote_id} moved to aviary {avi_id}")
            
    def lote_to_production(self, lote_id):
        lote = self.memo_lotes.get(lote_id)
        if lote.plote_fase == "recria" and lote.plote_age_weeks >= lote.plote_eprod:
            return True
        else:
            return False
        
    def lote_to_predescarte(self, lote_id):
        lote = self.memo_lotes.get(lote_id)
        if lote.plote_fase == "produccion":
            return True
        else:
            return False
        
    
        
    
        
            


        






# #test farmer class
# farmer = Farmer()
# farmer.fetch_aviaries([76, 77, 78, 79, 80, 81, 82])
# farmer.fetch_lotes([3262, 3263, 3264, 3265, 3266])
# farmer.lote_to_aviary()
# farmer.set_lote_fases()
# farmer.set_system_date(datetime.now().date())
# farmer.fetch_lote_dynamics()
# report = farmer.build_report()

# #pp.pprint(report)
# pp.pprint(report)


    
    
    






    