import re
from datetime import datetime, timedelta
from app.utils.database import get_connection  

class Lote:
    def __init__(self, plote_raza_id, pad_id, plote_cantidad, plote_eprod=19):
        # Identidad
        self.plote_id = None
        self.plote_name = None
        self.plote_raza_id = plote_raza_id
        self.plote_pad_id = pad_id
        # Tiempos predefinidos
        self.plote_eprod = plote_eprod
        self.plote_fnac_a = None
        self.plote_fnac_b = None
        self.plote_fprod = None
        # Tiempos en simulación
        self.plote_date = None
        self.plote_age_days = None
        self.plote_age_weeks = None
        # Espacio
        self.plote_avi_id = None
        # Cantidad
        self.plote_cantidad = plote_cantidad
        self.is_selling = False
        # Estado de producción 
        self.plote_fase = None
        self.assigned_aviario = None
        # Patrones de produccion
        self.bio_patterns = None
        self.plote_production = None
        self.plote_deaths = None

    # Representación de la clase
    def __repr__(self):
        return (f"Lote(plote_id={self.plote_id}, plote_name={self.plote_name}, plote_raza_id={self.plote_raza_id}, "
                f"plote_pad_id={self.plote_pad_id}, plote_eprod={self.plote_eprod}, plote_fnac_a={self.plote_fnac_a}, "
                f"plote_fnac_b={self.plote_fnac_b}, plote_fprod={self.plote_fprod}, plote_date={self.plote_date}, "
                f"plote_age_days={self.plote_age_days}, plote_age_weeks={self.plote_age_weeks}, plote_avi_id={self.plote_avi_id}, "
                f"plote_cantidad={self.plote_cantidad}, plote_cvtadia={self.plote_cvtadia}, plote_state={self.plote_state}, "
                f"bio_patterns={self.bio_patterns}, assigned_aviario={self.assigned_aviario})")

    ############################ Functions that create identity for the Lote ###########################
    def _set_plote_id(self):
        """Fetch the maximum plote_id from the database"""
        try:
            with get_connection() as conn:  
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(plote_id) FROM m_prm_pro_lotes")
                result = cursor.fetchone()
                self.plote_id = (result[0] + 1) if result and result[0] is not None else 1
                print(f"plote_id set to: {self.plote_id}")
        except Exception as e:
            print(f"Database error: {str(e)}")
            raise

    def _set_plote_name(self):
        """Calculate the next plote_name based on the summation logic"""
        try:
            with get_connection() as conn:  
                cursor = conn.cursor()
                cursor.execute("SELECT plote_name FROM m_prm_pro_lotes")
                rows = cursor.fetchall()

                max_sum = 0
                max_addends = (0, 0)

                for row in rows:
                    plote_name = row[0]
                    numbers = list(map(int, re.findall(r'\d+', plote_name)))
                    if len(numbers) == 2:
                        current_sum = sum(numbers)
                        if current_sum > max_sum:
                            max_sum = current_sum
                            max_addends = tuple(numbers)

                first_addend, second_addend = max_addends
                lote_1 = second_addend + 1
                lote_2 = second_addend + 2
                self.plote_name = f"{lote_1}+{lote_2}"
                print(f"Next plote_name: {self.plote_name}")

        except Exception as e:
            print(f"Database error: {str(e)}")
            raise

    def _set_plote_fnac(self):
        """Set birth and production dates"""
        try:
            current_date = datetime.now()
            self.plote_fnac_a = current_date.date()
            self.plote_fnac_b = self.plote_fnac_a + timedelta(days=7)
            self.plote_fprod = self.plote_fnac_a + timedelta(days=self.plote_eprod * 7)
            print(f"plote_fnac_a set to: {self.plote_fnac_a}")
            print(f"plote_fnac_b set to: {self.plote_fnac_b}")
            print(f"plote_fprod set to: {self.plote_fprod}")
        except Exception as e:
            print(f"Error setting plote_fnac_a: {str(e)}")
            raise
    
    def fetch_bios(self):
        """Fetch production pattern based on plote_pad_id"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pdet_edad, pdet_productividad, pdet_pmortd
                    FROM m_prm_padron_detalle
                    WHERE pdet_padron_id = ?
                    ORDER BY pdet_edad ASC
                """, (self.plote_pad_id,))
                
                rows = cursor.fetchall()
                if rows:
                    self.bio_patterns = [
                        {
                            "edad": row[0],
                            "productividad": row[1],
                            "mortalidad": row[2]
                        }
                        for row in rows
                    ]
                    print(f"Loaded {len(self.bio_patterns)} production patterns from plote_pad_id {self.plote_pad_id} for lote {self.plote_id}")
                else:
                    print(f"No production patterns found for plote_pad_id {self.plote_pad_id}")

        except Exception as e:
            print(f"Database error in fetching production patterns: {str(e)}")
            raise 

    def set_lote_instantiation(self, id_escenario):
        """Initialize Lote instance"""
        self.id_escenario = id_escenario
        print(f"id_escenario set to: {self.id_escenario}")
        self._set_plote_id()
        self._set_plote_name()
        self._set_plote_fnac()
        self.fetch_bios()


    ############################ Functions that happend once simulation runs ###########################
    def set_plote_age(self):
        """Set the time step for the lote"""
        if isinstance(self.plote_date, datetime):
            plote_date = self.plote_date.date()
        else:
            plote_date = self.plote_date

        self.plote_age_days = (plote_date - self.plote_fnac_a).days
        self.plote_age_weeks = round(self.plote_age_days / 7)
        return
        
    def _compute_bios(self):
        """Compute both productivity and mortality for the current simulated time."""
        try:
            if not self.bio_patterns:
                print("No production patterns available for this lote.")
                return None, None  # Return None for both values if patterns are missing
            # Use the current age in weeks
            lote_age_weeks = self.plote_age_weeks
            # Find the closest matching "edad" (in weeks)
            closest_pattern = min(
                self.bio_patterns,
                key=lambda pattern: abs(pattern["edad"] - lote_age_weeks)
            )
            # Compute productivity and mortality
            if self.plote_eprod > lote_age_weeks:
                productivity = 0
                mortality = closest_pattern["mortalidad"]
            else:
                productivity = closest_pattern["productividad"] / 100
                mortality = closest_pattern["mortalidad"]

            return productivity, mortality
        
        except Exception as e:
            print(f"Error computing productivity and mortality: {str(e)}")
            return None, None

    def population_dynamics(self):
        """Compute the population dynamics for the lote"""
        try:
            if self.plote_cantidad > 0:
                productivity, mortality = self._compute_bios()
                self.plote_deaths = round(self.plote_cantidad * mortality)
                self.plote_production = round(self.plote_cantidad * productivity)
                self.plote_cantidad -= self.plote_deaths
                return print(f"Population dynamics computed: {self.plote_production} produced, {self.plote_deaths} dead.")
            else:
                print("No population dynamics to compute.")
        except Exception as e:
            print(f"Error computing population dynamics: {str(e)}")
            return
    
    def sell_population(self, cantidad=2500):
        """Sell a given amount of population"""
        try:
            if self.plote_cantidad > 0:
                if cantidad > self.plote_cantidad:
                    cantidad = self.plote_cantidad
                self.plote_cantidad -= cantidad
                print(f"{cantidad} population sold from lote {self.plote_id}")
                if self.plote_cantidad == 0:
                    aviary = self.farmer.memo_aviaries.get(self.plote_avi_id)
                    if aviary:
                        aviary.needs_disinfection = True
                        print(f"Aviary {aviary.avi_id} needs disinfection")
            else:
                print("No population to sell.")
        except Exception as e:
            print(f"Error selling population: {str(e)}")



    
    





    
