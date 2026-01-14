from .base_entity import BaseEntity
from database.models import Semester, Institution
from datetime import date

class SemesterModel(BaseEntity[Semester]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Semester)

    def get_current_semester_info(self):
        headers = ["institution_name", "semester_name"]
        data = (
            self.session
            .query(Institution.name, Semester.name)
            .select_from(Semester)
            .join(Institution, Institution.institution_id == Semester.institution_id)
            .filter(
                (Semester.start_date <= date.today()) &
                (Semester.end_date >= date.today())
            )
            .first()
        )
        return dict(zip(headers, data))

