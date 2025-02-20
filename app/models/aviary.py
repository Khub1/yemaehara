import re
from datetime import datetime, timedelta
from app.utils.database import get_connection  


class Aviario:
    def __init__(self, avi_id):
        self.avi_id = avi_id
        self.avi_name = None
        self.avi_capacidad_ideal = None
        self.avi_fase = None
        #######################################
        self.needs_disinfection = False
        self.disinfection_period_days = 30
        self.disinfection_due_date = None
        #######################################
        self.allocated_lote = None
        self.production = {}
        self.is_active = False
        #######################################
        self.date = None

    def __repr__(self):
        return (f"Aviario(avi_id={self.avi_id}, avi_name={self.avi_name},"
                f"avi_capacidad_ideal={self.avi_capacidad_ideal}, "
                f"avi_desinfeccion={self.production})")

    def set_activate(self):
        if self.is_active == False:
            self.is_active = self.check_disinfection_due(self.date)
        else:
            pass

    def pick_production(self, dynamics):
        if self.is_active:
            self.production[self.date] = {"productivity": dynamics[0], "mortality": dynamics[1]}
        else:   
            self.set_activate()
            if self.is_active:
                self.production[self.date] = {"productivity": dynamics[0], "mortality": dynamics[1]}
            else:
                self.production[self.date] = {"productivity": 0, "mortality": 0}
        
    def set_inactivate(self):
        self.is_active = False
        self.schedule_disinfection()

    def schedule_disinfection(self):
        if self.date is None:
            raise ValueError(f"Cannot schedule disinfection for aviary {self.avi_id}: date not set")
        self.needs_disinfection = True
        self.disinfection_due_date = self.date + timedelta(days=self.disinfection_period_days)

    def check_disinfection_due(self):
        if self.disinfection_due_date is None:
            return False  # Not scheduled yet, so not due
        return self.date >= self.disinfection_due_date


