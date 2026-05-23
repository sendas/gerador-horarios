from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Date, Time,
    DateTime, ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from app.database import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    schools = relationship("School", back_populates="cluster", cascade="all, delete-orphan")
    academic_years = relationship("AcademicYear", back_populates="cluster", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="cluster", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="cluster", cascade="all, delete-orphan")
    non_teaching_types = relationship("NonTeachingType", back_populates="cluster", cascade="all, delete-orphan")
    scheduling_rules = relationship("SchedulingRules", cascade="all, delete-orphan")


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cluster = relationship("Cluster", back_populates="schools")
    classes = relationship("Class", back_populates="school", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="school", cascade="all, delete-orphan")
    teacher_assignments = relationship("TeacherSchoolAssignment", back_populates="school", cascade="all, delete-orphan")
    time_slot_configs = relationship("TimeSlotConfig", back_populates="school", cascade="all, delete-orphan")


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
    classes = relationship("Class", back_populates="academic_year", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="academic_year", cascade="all, delete-orphan")
    time_slot_configs = relationship("TimeSlotConfig", back_populates="academic_year", cascade="all, delete-orphan")
    teacher_school_assignments = relationship("TeacherSchoolAssignment", back_populates="academic_year", cascade="all, delete-orphan")
    teacher_availabilities = relationship("TeacherAvailability", back_populates="academic_year", cascade="all, delete-orphan")
    non_teaching_assignments = relationship("NonTeachingAssignment", back_populates="academic_year", cascade="all, delete-orphan")
    subject_groups = relationship("SubjectGroup", back_populates="academic_year", cascade="all, delete-orphan")


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
    # Weekly structure: '1' | '1+1' | '2' | '2+1' | '1+1+1'
    # Translates to (split_count, consecutive_pairs) when adding curriculum entries
    weekly_structure = Column(String, default="1+1")
    # Regime: 'annual' | 'semestral'
    regime = Column(String, default="annual")
    default_semester = Column(Integer, nullable=True)  # 1 or 2 if semestral
    paired_subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    is_physical_education = Column(Boolean, default=False)   # triggers no-PE-after-lunch
    can_exempt_articulado = Column(Boolean, default=False)   # students can have dispensation

    cluster = relationship("Cluster", back_populates="subjects")
    paired_subject = relationship("Subject", foreign_keys="[Subject.paired_subject_id]", remote_side="Subject.id", uselist=False)
    curriculum_entries = relationship("CurriculumEntry", back_populates="subject", cascade="all, delete-orphan")
    teacher_subjects = relationship("TeacherSubject", back_populates="subject", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    name = Column(String, nullable=False)
    year_level = Column(Integer, nullable=False)
    num_students = Column(Integer, default=25)
    notes = Column(String, nullable=True)  # observações (ex: info do campo articulado)

    school = relationship("School", back_populates="classes")
    academic_year = relationship("AcademicYear", back_populates="classes")
    curriculum_entries = relationship("CurriculumEntry", back_populates="class_", cascade="all, delete-orphan")


class CurriculumEntry(Base):
    __tablename__ = "curriculum_entries"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    hours_per_week = Column(Float, nullable=False)
    is_split = Column(Boolean, default=False)
    split_count = Column(Integer, default=1)
    consecutive_pairs = Column(Integer, default=0)  # how many of the splits must be consecutive doubles
    is_semestral = Column(Boolean, default=False)
    semester = Column(Integer, nullable=True)  # 1 or 2
    paired_entry_id = Column(Integer, ForeignKey("curriculum_entries.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    paired_entry = relationship("CurriculumEntry", foreign_keys="[CurriculumEntry.paired_entry_id]", remote_side="CurriculumEntry.id", uselist=False)

    class_ = relationship("Class", back_populates="curriculum_entries")
    subject = relationship("Subject", back_populates="curriculum_entries")
    teacher = relationship("Teacher", foreign_keys="[CurriculumEntry.teacher_id]")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="curriculum_entry", cascade="all, delete-orphan")
    subject_group_entries = relationship("SubjectGroupEntry", back_populates="curriculum_entry", cascade="all, delete-orphan")


class SubjectGroup(Base):
    __tablename__ = "subject_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)

    academic_year = relationship("AcademicYear", back_populates="subject_groups")
    entries = relationship("SubjectGroupEntry", back_populates="group", cascade="all, delete-orphan")


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
    min_start_slot = Column(Integer, nullable=True)
    max_end_slot = Column(Integer, nullable=True)
    preferred_shift = Column(String, nullable=True)   # 'morning' | 'afternoon' | None
    max_consecutive_lessons = Column(Integer, nullable=True)
    teaching_component = Column(Integer, nullable=True)  # letivas/semana configuradas (14–22)
    credit_hours = Column(Integer, nullable=True, default=0)  # horas de crédito/redução
    birth_date = Column(Date, nullable=True)
    total_hours = Column(Integer, nullable=True, default=25)        # legacy — não usado no diálogo
    base_teaching_hours = Column(Integer, nullable=True, default=22) # CL — Componente Letiva
    te_hours = Column(Integer, nullable=True, default=3)            # TE — Trabalho no Estabelecimento
    te_role = Column(String, nullable=True)                         # cargo associado ao TE
    credit_role = Column(String, nullable=True)                     # cargo associado ao crédito horário

    cluster = relationship("Cluster", back_populates="teachers")
    school_assignments = relationship("TeacherSchoolAssignment", back_populates="teacher", cascade="all, delete-orphan")
    teacher_subjects = relationship("TeacherSubject", back_populates="teacher", cascade="all, delete-orphan")
    availabilities = relationship("TeacherAvailability", back_populates="teacher", cascade="all, delete-orphan")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="teacher")
    non_teaching_assignments = relationship("NonTeachingAssignment", back_populates="teacher", cascade="all, delete-orphan")


class TeacherSchoolAssignment(Base):
    __tablename__ = "teacher_school_assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    travel_time_minutes = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)  # escola base do professor

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
    generation_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    academic_year = relationship("AcademicYear", back_populates="timetables")
    scheduled_lessons = relationship("ScheduledLesson", back_populates="timetable", cascade="all, delete-orphan")
    locks = relationship("TimetableLock", back_populates="timetable", cascade="all, delete-orphan")


class ScheduledLesson(Base):
    __tablename__ = "scheduled_lessons"

    id = Column(Integer, primary_key=True, index=True)
    timetable_id = Column(Integer, ForeignKey("timetables.id"), nullable=False)
    curriculum_entry_id = Column(Integer, ForeignKey("curriculum_entries.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon..4=Fri
    slot_number = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=True)  # null=both, 1=semester1, 2=semester2

    timetable = relationship("Timetable", back_populates="scheduled_lessons")
    curriculum_entry = relationship("CurriculumEntry", back_populates="scheduled_lessons")
    teacher = relationship("Teacher", back_populates="scheduled_lessons")
    room = relationship("Room", back_populates="scheduled_lessons")


class SchedulingRules(Base):
    __tablename__ = "scheduling_rules"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=True)  # null = applies to all years
    max_periods_per_day_class = Column(Integer, default=5)
    max_periods_per_day_teacher = Column(Integer, default=6)
    max_consecutive_periods_class = Column(Integer, default=2)
    max_consecutive_periods_teacher = Column(Integer, default=4)
    avoid_isolated_teacher = Column(Boolean, default=False)  # penalize isolated single periods for teachers
    no_student_gaps = Column(Boolean, default=True)        # hard: no free slots between class lessons
    minimize_teacher_gaps = Column(Boolean, default=True)   # soft: reduce holes in teacher day
    teacher_gap_weight = Column(Integer, default=10)        # penalty weight for teacher gaps
    no_same_subject_twice_per_day = Column(Boolean, default=True)  # hard: split occurrences on different days
    distribute_subjects_weight = Column(Integer, default=5) # soft: spread subject across week days
    students_start_slot_1 = Column(Boolean, default=True)   # hard: 1st slot occupied each day
    no_pe_after_lunch = Column(Boolean, default=True)        # hard: no PE after slot lunch_after_slot
    lunch_after_slot = Column(Integer, default=4)            # last slot before lunch

    cluster = relationship("Cluster")
    academic_year = relationship("AcademicYear")


class BackupConfig(Base):
    __tablename__ = "backup_config"
    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, default=False)
    frequency = Column(String, default="weekly")   # manual | daily | weekly | monthly
    onedrive_client_id = Column(String, nullable=True)
    onedrive_refresh_token = Column(String, nullable=True)  # encrypted
    folder_path = Column(String, default="GeradorHorarios/Backups")
    last_backup_at = Column(DateTime, nullable=True)
    next_backup_at = Column(DateTime, nullable=True)


class BackupHistory(Base):
    __tablename__ = "backup_history"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)           # success | error
    destination = Column(String, default="download")  # download | onedrive
    size_bytes = Column(Integer, nullable=True)
    message = Column(String, nullable=True)
    filename = Column(String, nullable=True)


class NonTeachingType(Base):
    __tablename__ = "non_teaching_types"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, default="#e74c3c")

    cluster = relationship("Cluster", back_populates="non_teaching_types")
    assignments = relationship("NonTeachingAssignment", back_populates="non_teaching_type", cascade="all, delete-orphan")


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


class TimetableLock(Base):
    __tablename__ = "timetable_locks"

    id = Column(Integer, primary_key=True, index=True)
    timetable_id = Column(Integer, ForeignKey("timetables.id"), nullable=False)
    lock_type = Column(String, nullable=False)  # 'teacher' | 'class'
    entity_id = Column(Integer, nullable=False)

    timetable = relationship("Timetable", back_populates="locks")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)


class CurriculumPlan(Base):
    """Standard curriculum template per year level — defines which subjects and hours
    should be applied to all classes of a given year level in an academic year."""
    __tablename__ = "curriculum_plans"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False)
    year_level = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    hours_per_week = Column(Float, nullable=False, default=2.0)
    weekly_structure = Column(String, default="1+1")  # e.g. "2+1", "1+1+1", "1+1", "1"
    is_semestral = Column(Boolean, default=False)
    semester = Column(Integer, nullable=True)  # 1 or 2
    paired_subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)

    subject = relationship("Subject", foreign_keys="[CurriculumPlan.subject_id]")
    paired_subject = relationship("Subject", foreign_keys="[CurriculumPlan.paired_subject_id]")
    academic_year = relationship("AcademicYear")

