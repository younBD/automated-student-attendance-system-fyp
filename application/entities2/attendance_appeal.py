from .base_entity import BaseEntity
from typing import List, Optional, Dict
from datetime import datetime, date
from database.models import *

class AttendanceAppealModel(BaseEntity[AttendanceAppeal]):
    """Entity for AttendanceRecord model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, AttendanceAppeal)
    
    def student_appeals(self, student_id: int) -> List[AttendanceAppeal]:
        headers = ["id", "course_code", "course_name", "class_date", "reason", "status"]
        data = (
            self.session
            .query(AttendanceAppeal.appeal_id, Course.code, Course.name, Class.start_time, AttendanceAppeal.reason, AttendanceAppeal.status)
            .select_from(AttendanceAppeal)
            .join(AttendanceRecord, AttendanceRecord.attendance_id == AttendanceAppeal.attendance_id)
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .join(Course, Class.course_id == Course.course_id)
            .filter(
                AttendanceAppeal.student_id == student_id
            )
            .all()
        )
        headered_data = self.add_headers(headers, data)
        for item in headered_data:
            item["module"] = f"{item['course_code']} - {item['course_name']}"
            item["class_date"] = item["class_date"].strftime("%d %b %Y")
        return headered_data