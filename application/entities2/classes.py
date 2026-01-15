from .base_entity import BaseEntity
from database.models import Class, Course, Venue, User, CourseUser, AttendanceRecord, Semester
from datetime import date, datetime, timedelta
from sqlalchemy import func, extract, case
from sqlalchemy.orm import aliased

class ClassModel(BaseEntity[Class]):
    """Specific entity for User model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, Class)

    def get_today(self, institution_id):
        return (
            self.session
            .query(Class)
            .join(Course, Class.course_id == Course.course_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .all()
        )
    
    def get_completed(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.end_time < datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def get_upcoming(self, course_id):
        return (
            self.session
            .query(Class.class_id, Class.start_time, Class.end_time, Venue.name, User.name)
            .join(User, User.user_id == Class.lecturer_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Class.course_id == course_id)
            .filter(Class.start_time > datetime.now())
            .filter(User.role == "lecturer")
            .all()
        )

    def admin_dashboard_classes_today(self, institution_id):
        cols = ["id", "module", "venue", "lecturer"]
        classes = (
            self.session
            .query(Class.class_id, Course.name, Venue.name, User.name)
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(User, Class.lecturer_id == User.user_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .filter(Course.institution_id == institution_id)
            .filter(Class.start_time > date.today())
            .filter(Class.start_time < date.today() + timedelta(days=1))
            .all()
        )
        return self.add_headers(cols, classes)
    
    def admin_class_details(self, class_id):
        headers = ["start_time", "venue", "lecturer"]
        class_data = (
            self.session
            .query(Class.start_time, Venue.name, User.name)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(User, Class.lecturer_id == User.user_id)
            .filter(Class.class_id == class_id)
            .one()
        )
        class_details: dict = dict(zip(headers, class_data))
        q_in_course = (
            self.session
            .query(func.count(User.user_id))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
        )
        q_total = q_in_course.scalar_subquery()
        q_attendance_exists = q_in_course.join(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
        q_present = q_attendance_exists.filter(AttendanceRecord.status == "present").scalar_subquery()
        q_late = q_attendance_exists.filter(AttendanceRecord.status == "late").scalar_subquery()
        q_excused = q_attendance_exists.filter(AttendanceRecord.status == "excused").scalar_subquery()
        q_absent = q_attendance_exists.filter(AttendanceRecord.status == "absent").scalar_subquery()

        cols = ["total", "present", "late", "excused", "absent"]
        row = self.session.query(q_total, q_present, q_late, q_excused, q_absent).one()

        class_details.update(dict(zip(cols, row)))
        class_details["marked"] = sum(row[1:])
        return class_details

    def student_attendance_absent_late(self, user_id):
        headers = [
            "class_id", "course_code", "course_name", "start_date", "venue", "lecturer", "status"
        ]
        Lecturer = aliased(User)
        data = (
            self.session
            .query(Class.class_id, Course.code, Course.name, Class.start_time, Venue.name, Lecturer.name
                   , func.coalesce(AttendanceRecord.status, "unmarked"))
            .select_from(Semester)
            .join(CourseUser, Semester.semester_id == CourseUser.semester_id)
            .join(User, CourseUser.user_id == User.user_id)
            .join(Course, CourseUser.course_id == Course.course_id)
            .join(Class, Class.course_id == Course.course_id)
            .join(Venue, Class.venue_id == Venue.venue_id)
            .join(Lecturer, Class.lecturer_id == Lecturer.user_id)
            .outerjoin(
                AttendanceRecord,
                (AttendanceRecord.class_id == Class.class_id) &
                (AttendanceRecord.student_id == user_id)
            )
            .filter((Semester.start_date <= func.now()) & (Semester.end_date >= func.now()))
            .filter(CourseUser.user_id == user_id)
            .filter(User.role == "student")
            .distinct(Class.class_id)
            .all()
        )
        data = [d for d in data if d[-1] in ["absent", "late"]]
        return self.add_headers(headers, data)

    def student_attendance_monthly(self, user_id, num_months: int=4):
        n_months_ago = datetime.now() - timedelta(days=30 * num_months)
        cutoff_date = n_months_ago.replace(day=1)
        print(cutoff_date)
        headers = ["year", "month", "total_classes", "p", "a", "l", "e"]
        return self.add_headers(headers, (
            self.session.query(
                extract('year', Class.start_time).label('year'),
                extract('month', Class.start_time).label('month'),
                func.count(Class.class_id).label('total_classes'),
                func.sum(case((AttendanceRecord.status == "present", 1), else_=0)).label('p'),
                func.sum(case((AttendanceRecord.status == "absent", 1), else_=0)).label('a'),
                func.sum(case((AttendanceRecord.status == "late", 1), else_=0)).label('l'),
                func.sum(case((AttendanceRecord.status == "excused", 1), else_=0)).label('e'),
            )
            .join(Class, AttendanceRecord.class_id == Class.class_id)
            .filter(AttendanceRecord.student_id == user_id)
            .filter(Class.start_time >= cutoff_date)
            # .filter(Class.start_time < datetime.now())
            .filter(Class.start_time < date(2026, 6,27))
            .group_by('year', 'month')
            .order_by('year', 'month')
        ))

    def get_attendance_records(self, class_id):
        headers = ["student_name", "student_id", "status"]
        records = (
            self.session
            .query(User.name, User.user_id, func.coalesce(AttendanceRecord.status, "unmarked"))
            .select_from(Class)
            .join(Course, Class.course_id == Course.course_id)
            .join(CourseUser, CourseUser.course_id == Course.course_id)
            .join(User, User.user_id == CourseUser.user_id)
            .outerjoin(AttendanceRecord, AttendanceRecord.class_id == Class.class_id)
            .filter(Class.class_id == class_id)
            .filter(User.role == "student")
            .all()
        )
        return self.add_headers(headers, records)

    def class_is_institution(self, class_id, institution_id) -> bool:
        return (
            self.session
            .query(Course.institution_id)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .filter(Course.institution_id == institution_id)
            .count() > 0
        )
    
    def get_course_name(self, class_id) -> str:
        result = (
            self.session
            .query(Course.name)
            .join(Class, Class.course_id == Course.course_id)
            .filter(Class.class_id == class_id)
            .one_or_none()
        )
        return result[0] if result else ""
    