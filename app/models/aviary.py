# app/models/aviary.py
import re
from datetime import datetime, timedelta
from app.utils.database import get_connection  

# app/models/aviary.py
import re
from datetime import datetime, timedelta
from app.utils.database import get_connection  

class Aviario:
    def __init__(self, avi_id, needs_disinfection=False):
        self.avi_id = avi_id
        self.avi_name = None
        self.avi_capacidad_ideal = None
        self.avi_fase = None
        #######################################
        self.needs_disinfection = needs_disinfection
        self.disinfection_period_days = 30
        self.disinfection_due_date = None
        #######################################
        self.allocated_lote = None
        self.is_active = False
        self.was_inactive = False
        #######################################
        self.date = None

        # If needs_disinfection is True at initialization, set active state and due date
        if self.needs_disinfection and self.date is not None:
            self.is_active = True  # Disinfection is an active process
            self.disinfection_due_date = self.date + timedelta(days=self.disinfection_period_days)
            print(f"Aviary {self.avi_id} initialized with disinfection in progress until {self.disinfection_due_date}")

    def __repr__(self):
        return (f"Aviary(avi_id={self.avi_id}, avi_name={self.avi_name}, "
                f"avi_capacidad_ideal={self.avi_capacidad_ideal}, "
                f"avi_fase={self.avi_fase}, "
                f"needs_disinfection={self.needs_disinfection}, "
                f"is_active={self.is_active}, "
                f"allocated_lote={self.allocated_lote})")

    def set_date(self, date):
        """Set the date and initialize disinfection state if needed."""
        self.date = date
        if self.needs_disinfection and self.disinfection_due_date is None:
            self.is_active = True
            self.disinfection_due_date = self.date + timedelta(days=self.disinfection_period_days)
            print(f"Aviary {self.avi_id} disinfection initialized with date {self.date}, due {self.disinfection_due_date}")

    def set_active(self):
        """
        Set the aviary to active if it’s clean or disinfection is complete.
        Raises an error if disinfection is still in progress.
        """
        if self.needs_disinfection:
            if self.check_disinfection_due():
                self.needs_disinfection = False
                self.disinfection_due_date = None
                self.was_inactive = True
                print(f"Aviary {self.avi_id} disinfection complete, ready for active state")
            else:
                raise ValueError(f"Aviary {self.avi_id} cannot be set active: disinfection in progress until {self.disinfection_due_date}")
        if not self.is_active:
            self.is_active = True
            self.was_inactive = False
            print(f"Aviary {self.avi_id} set to active")

    def set_inactive(self):
        """
        Set the aviary to inactive, scheduling disinfection only if it was occupied.
        """
        if self.allocated_lote:  # Only schedule disinfection if a lote was present
            self.schedule_disinfection()
            print(f"Aviary {self.avi_id} set inactive and scheduled for disinfection")
        else:
            self.is_active = False
            self.needs_disinfection = False  # Ensure clean state if never occupied
            self.was_inactive = True
            print(f"Aviary {self.avi_id} set inactive (no disinfection needed)")

    def schedule_disinfection(self):
        """
        Schedule disinfection, marking the aviary as active during the process.
        """
        if self.date is None:
            raise ValueError(f"Cannot schedule disinfection for aviary {self.avi_id}: date not set")
        self.needs_disinfection = True
        self.disinfection_due_date = self.date + timedelta(days=self.disinfection_period_days)
        self.is_active = True  # Disinfection is an active process
        self.was_inactive = False
        print(f"Aviary {self.avi_id} scheduled for disinfection until {self.disinfection_due_date}")

    def check_disinfection_due(self):
        """
        Check if disinfection is complete based on the current date.
        Returns True if complete or not scheduled, False if in progress.
        """
        if self.disinfection_due_date is None:
            return True  # No disinfection scheduled, so "due" is effectively complete
        return self.date >= self.disinfection_due_date


