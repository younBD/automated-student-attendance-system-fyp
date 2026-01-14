from .base_entity import BaseEntity
from database.models import Semester

class SemesterModel(BaseEntity[Semester]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Semester)
