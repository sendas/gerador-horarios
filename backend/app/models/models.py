from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Date, Time,
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    schools = relationship("School", back_populates="cluster")
    academic_years = relationship("AcademicYear", back_populates="cluster")
    subjects = relationship("Subject", back_populates="cluster")
    teachers = relationship("Teacher", back_populates="cluster")
    non_teaching_types = relationship("NonTeachingType", back_populates="cluster")


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cluster = relationship("Cluster", back_populates="schools")
    classes = relationship("Class", back_populates="school")
    rooms = relationship("Room", back_populates="school")
    teacher_assignments = relationship("TeacherSchoolAssignment", back_populates="school")
    time_slot_configs = relationship("TimeSlotConfig", back_populates="school")


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    cluster = relationship("Cluster", back_populates="academic_years")
    classes = relationship("Class", back_populates="academic_year")
    timetables = relationship("Timetable", back_populates="academic_year")
    time_slot_configs = relationship("TimeSlotConfig", back_populates="academic_year")
    teacher_school_assignments = relationship("TeacherSchoolAssignment", back_populates="academic_year")
    teacher_availabilities = relationship("TeacherAvailability", back_populates="academic_year")
    non_teaching_assignments = relationship("NonTeachingAssignment", back_populates="academic_year")
    subject_groups = relationship("SubjectGroup", back_populates="academic_year")


class TimeSlotConfig(Base):
    __tablename__ = "time_slot_configs"

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon..4=Fri
    slot_number = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_break = Column(Boolean, default=False)

    academic_year = relationship("AcademicYear", back_populates="time_slot_configs")
    school = relationship("School", back_populates="time_slot_configs")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    name = Column(String, nullable=False)
    capacity = Column(Integer, default=30)
    room_type = Column(String, default="classroom")

    school = relationship("School", back_populates="rooms")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="room")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    color = Column(String, default="#3498db")

    cluster = relationship("Cluster", back_populates="subjects")
    curriculum_entries = relationship("CurriculumEntry", back_populates="subject")
    teacher_subjects = relationship("TeacherSubject", back_populates="subject")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    name = Column(String, nullable=False)
    year_level = Column(Integer, nullable=False)
    num_students = Column(Integer, default=25)

    school = relationship("School", back_populates="classes")
    academic_year = relationship("AcademicYear", back_populates="classes")
    curriculum_entries = relationship("CurriculumEntry", back_populates="class_")


class CurriculumEntry(Base):
    __tablename__ = "curriculum_entries"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    hours_per_week = Column(Float, nullable=False)
    is_split = Column(Boolean, default=False)
    split_count = Column(Integer, default=1)

    class_ = relationship("Class", back_populates="curriculum_entries")
    subject = relationship("Subject", back_populates="curriculum_entries")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="curriculum_entry")
    subject_group_entries = relationship("SubjectGroupEntry", back_populates="curriculum_entry")


class SubjectGroup(Base):
    __tablename__ = "subject_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)

    academic_year = relationship("AcademicYear", back_populates="subject_groups")
    entries = relationship("SubjectGroupEntry", back_populates="group")


class SubjectGroupEntry(Base):
    __tablename__ = "subject_group_entries"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("subject_groups.id"), nullable=False)
    curriculum_entry_id = Column(Integer, ForeignKey("curriculum_entries.id"), nullable=False)

    group = relationship("SubjectGroup", back_populates="entries")
    curriculum_entry = relationship("CurriculumEntry", back_populates="subject_group_entries")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    max_daily_lessons = Column(Integer, default=5)
    preferred_free_day = Column(Integer, nullable=True)  # 0-4 Mon-Fri

    cluster = relationship("Cluster", back_populates="teachers")
    school_assignments = relationship("TeacherSchoolAssignment", back_populates="teacher")
    teacher_subjects = relationship("TeacherSubject", back_populates="teacher")
    availabilities = relationship("TeacherAvailability", back_populates="teacher")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="teacher")
    non_teaching_assignments = relationship("NonTeachingAssignment", back_populates="teacher")


class TeacherSchoolAssignment(Base):
    __tablename__ = "teacher_school_assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    travel_time_minutes = Column(Integer, default=0)

    teacher = relationship("Teacher", back_populates="school_assignments")
    school = relationship("School", back_populates="teacher_assignments")
    academic_year = relationship("AcademicYear", back_populates="teacher_school_assignments")


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    __table_args__ = (UniqueConstraint("teacher_id", "subject_id"),)

    teacher = relationship("Teacher", back_populates="teacher_subjects")
    subject = relationship("Subject", back_populates="teacher_subjects")


class TeacherAvailability(Base):
    __tablename__ = "teacher_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    slot_number = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True)

    teacher = relationship("Teacher", back_populates="availabilities")
    academic_year = relationship("AcademicYear", back_populates="teacher_availabilities")


class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, default="draft")  # draft/generating/generated/error
    solver_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    academic_year = relationship("AcademicYear", back_populates="timetables")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="timetable", cascade="all, delete-orphan")


class ScheduledLesson(Base):
    __tablename__ = "scheduled_lessons"

    id = Column(Integer, primary_key=True, index=True)
    timetable_id = Column(Integer, ForeignKey("timetables.id"), nullable=False)
    curriculum_entry_id = Column(Integer, ForeignKey("curriculum_entries.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon..4=Fri
    slot_number = Column(Integer, nullable=False)

    timetable = relationship("Timetable", back_populates="scheduled_lessons")
    curriculum_entry = relationship("CurriculumEntry", back_populates="scheduled_lessons")
    teacher = relationship("Teacher", back_populates="scheduled_lessons")
    room = relationship("Room", back_populates="scheduled_lessons")


class NonTeachingType(Base):
    __tablename__ = "non_teaching_types"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, default="#e74c3c")

    cluster = relationship("Cluster", back_populates="non_teaching_types")
    assignments = relationship("NonTeachingAssignment", back_populates="non_teaching_type")


class NonTeachingAssignment(Base):
    __tablename__ = "non_teaching_assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    non_teaching_type_id = Column(Integer, ForeignKey("non_teaching_types.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    slot_number = Column(Integer, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)

    teacher = relationship("Teacher", back_populates="non_teaching_assignments")
    non_teaching_type = relationship("NonTeachingType", back_populates="assignments")
    academic_year = relationship("AcademicYear", back_populates="non_teaching_assignments")
