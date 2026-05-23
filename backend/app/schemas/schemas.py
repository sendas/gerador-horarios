from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ── Cluster ──────────────────────────────────────────────────────────────────

class ClusterBase(BaseModel):
    name: str
    description: Optional[str] = None

class ClusterCreate(ClusterBase):
    pass

class ClusterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ClusterResponse(ClusterBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ── School ───────────────────────────────────────────────────────────────────

class SchoolBase(BaseModel):
    cluster_id: int
    name: str
    code: str
    address: Optional[str] = None

class SchoolCreate(SchoolBase):
    pass

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    cluster_id: Optional[int] = None

class SchoolResponse(SchoolBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ── AcademicYear ─────────────────────────────────────────────────────────────

class AcademicYearBase(BaseModel):
    cluster_id: int
    name: str
    start_date: date
    end_date: date
    is_active: bool = False

class AcademicYearCreate(AcademicYearBase):
    pass

class AcademicYearUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

class AcademicYearResponse(AcademicYearBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ── TimeSlotConfig ────────────────────────────────────────────────────────────

class TimeSlotConfigBase(BaseModel):
    academic_year_id: int
    school_id: Optional[int] = None
    day_of_week: int
    slot_number: int
    start_time: time
    end_time: time
    is_break: bool = False

class TimeSlotConfigCreate(TimeSlotConfigBase):
    pass

class TimeSlotConfigUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_break: Optional[bool] = None

class TimeSlotConfigResponse(TimeSlotConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Room ─────────────────────────────────────────────────────────────────────

class RoomBase(BaseModel):
    school_id: int
    name: str
    capacity: int = 30
    room_type: str = "classroom"

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    room_type: Optional[str] = None

class RoomResponse(RoomBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Subject ───────────────────────────────────────────────────────────────────

class SubjectBase(BaseModel):
    cluster_id: int
    name: str
    code: Optional[str] = None
    color: str = "#3498db"
    weekly_structure: str = "1+1"
    regime: str = "annual"
    default_semester: Optional[int] = None
    paired_subject_id: Optional[int] = None
    is_physical_education: bool = False
    can_exempt_articulado: bool = False

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    color: Optional[str] = None
    weekly_structure: Optional[str] = None
    regime: Optional[str] = None
    default_semester: Optional[int] = None
    paired_subject_id: Optional[int] = None
    is_physical_education: bool = False
    can_exempt_articulado: bool = False

class SubjectResponse(SubjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    paired_subject_name: Optional[str] = None


# ── Class ─────────────────────────────────────────────────────────────────────

class ClassBase(BaseModel):
    school_id: int
    academic_year_id: int
    name: str
    year_level: int
    num_students: int = 25
    notes: Optional[str] = None

class ClassCreate(ClassBase):
    pass

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    year_level: Optional[int] = None
    num_students: Optional[int] = None
    notes: Optional[str] = None

class ClassResponse(ClassBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── CurriculumEntry ───────────────────────────────────────────────────────────

class CurriculumEntryBase(BaseModel):
    class_id: int
    subject_id: int
    hours_per_week: float
    is_split: bool = False
    split_count: int = 1
    consecutive_pairs: int = 0
    is_semestral: bool = False
    semester: Optional[int] = None
    paired_entry_id: Optional[int] = None

class CurriculumEntryCreate(CurriculumEntryBase):
    class_id: Optional[int] = None  # may be supplied via URL path param instead
    teacher_id: Optional[int] = None

class CurriculumEntryUpdate(BaseModel):
    hours_per_week: Optional[float] = None
    is_split: Optional[bool] = None
    split_count: Optional[int] = None
    consecutive_pairs: Optional[int] = None
    is_semestral: Optional[bool] = None
    semester: Optional[int] = None
    paired_entry_id: Optional[int] = None
    teacher_id: Optional[int] = None

class CurriculumEntryResponse(CurriculumEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None


# ── SubjectGroup ──────────────────────────────────────────────────────────────

class SubjectGroupEntryBase(BaseModel):
    curriculum_entry_id: int

class SubjectGroupEntryCreate(SubjectGroupEntryBase):
    pass

class SubjectGroupEntryResponse(SubjectGroupEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    group_id: int

class SubjectGroupBase(BaseModel):
    name: str
    academic_year_id: int

class SubjectGroupCreate(SubjectGroupBase):
    pass

class SubjectGroupUpdate(BaseModel):
    name: Optional[str] = None

class SubjectGroupResponse(SubjectGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entries: List[SubjectGroupEntryResponse] = []


# ── Teacher ───────────────────────────────────────────────────────────────────

class TeacherBase(BaseModel):
    cluster_id: int
    name: str
    email: Optional[str] = None
    max_daily_lessons: int = 5
    preferred_free_day: Optional[int] = None
    min_start_slot: Optional[int] = None
    max_end_slot: Optional[int] = None
    preferred_shift: Optional[str] = None
    max_consecutive_lessons: Optional[int] = None
    teaching_component: Optional[int] = None
    credit_hours: Optional[int] = 0
    birth_date: Optional[date] = None
    total_hours: Optional[int] = 25
    base_teaching_hours: Optional[int] = 22
    te_hours: Optional[int] = 3
    te_role: Optional[str] = None
    credit_role: Optional[str] = None

class TeacherCreate(TeacherBase):
    pass

class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    max_daily_lessons: Optional[int] = None
    preferred_free_day: Optional[int] = None
    min_start_slot: Optional[int] = None
    max_end_slot: Optional[int] = None
    preferred_shift: Optional[str] = None
    max_consecutive_lessons: Optional[int] = None
    teaching_component: Optional[int] = None
    credit_hours: Optional[int] = None
    birth_date: Optional[date] = None
    total_hours: Optional[int] = None
    base_teaching_hours: Optional[int] = None
    te_hours: Optional[int] = None
    te_role: Optional[str] = None
    credit_role: Optional[str] = None

class TeacherResponse(TeacherBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_names: List[str] = []
    subject_ids: List[int] = []
    school_ids: List[int] = []
    primary_school_id: Optional[int] = None
    primary_school_name: Optional[str] = None


# ── TeacherSchoolAssignment ───────────────────────────────────────────────────

class TeacherSchoolAssignmentBase(BaseModel):
    teacher_id: int
    school_id: int
    academic_year_id: int
    travel_time_minutes: int = 0
    is_primary: bool = False

class TeacherSchoolAssignmentCreate(TeacherSchoolAssignmentBase):
    teacher_id: Optional[int] = None  # supplied via URL path param

class TeacherSchoolAssignmentUpdate(BaseModel):
    travel_time_minutes: Optional[int] = None
    is_primary: Optional[bool] = None

class TeacherSchoolAssignmentResponse(TeacherSchoolAssignmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_name: Optional[str] = None


# ── TeacherAvailability ───────────────────────────────────────────────────────

class TeacherAvailabilityBase(BaseModel):
    teacher_id: int
    academic_year_id: int
    day_of_week: int
    slot_number: int
    is_available: bool = True

class TeacherAvailabilityCreate(TeacherAvailabilityBase):
    pass

class TeacherAvailabilityBulk(BaseModel):
    academic_year_id: int
    availabilities: List[TeacherAvailabilityCreate]

class TeacherAvailabilityResponse(TeacherAvailabilityBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Timetable ─────────────────────────────────────────────────────────────────

class TimetableBase(BaseModel):
    academic_year_id: int
    name: str

class TimetableCreate(TimetableBase):
    pass

class TimetableUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None

class TimetableResponse(TimetableBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    solver_status: Optional[str] = None
    generation_log: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── ScheduledLesson ───────────────────────────────────────────────────────────

class ScheduledLessonBase(BaseModel):
    timetable_id: int
    curriculum_entry_id: int
    teacher_id: Optional[int] = None
    room_id: Optional[int] = None
    day_of_week: int
    slot_number: int
    semester: Optional[int] = None

class ScheduledLessonCreate(ScheduledLessonBase):
    pass

class ScheduledLessonResponse(ScheduledLessonBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ScheduledLessonDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timetable_id: int
    day_of_week: int
    slot_number: int
    curriculum_entry_id: int
    teacher_id: Optional[int] = None
    room_id: Optional[int] = None
    semester: Optional[int] = None
    subject_name: Optional[str] = None
    subject_color: Optional[str] = None
    class_name: Optional[str] = None
    teacher_name: Optional[str] = None
    room_name: Optional[str] = None


class TimetableDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    academic_year_id: int
    name: str
    status: str
    solver_status: Optional[str] = None
    generation_log: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    lessons: List[ScheduledLessonDetail] = []


# ── NonTeachingType ───────────────────────────────────────────────────────────

class NonTeachingTypeBase(BaseModel):
    cluster_id: int
    name: str
    color: str = "#e74c3c"

class NonTeachingTypeCreate(NonTeachingTypeBase):
    pass

class NonTeachingTypeUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class NonTeachingTypeResponse(NonTeachingTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── NonTeachingAssignment ─────────────────────────────────────────────────────

class NonTeachingAssignmentBase(BaseModel):
    teacher_id: int
    non_teaching_type_id: int
    academic_year_id: int
    day_of_week: int
    slot_number: int
    school_id: Optional[int] = None

class NonTeachingAssignmentCreate(NonTeachingAssignmentBase):
    pass

class NonTeachingAssignmentUpdate(BaseModel):
    non_teaching_type_id: Optional[int] = None
    school_id: Optional[int] = None

class NonTeachingAssignmentResponse(NonTeachingAssignmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
