import csv
import io
from app.models.models import Timetable, ScheduledLesson, CurriculumEntry
from collections import defaultdict

DAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]


def generate_csv_timetable(db, timetable_id: int, view_type: str = "class", entity_id: int = None) -> str:
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        return ""

    q = db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id)
    if view_type == "teacher" and entity_id:
        q = q.filter(ScheduledLesson.teacher_id == entity_id)
    elif view_type == "room" and entity_id:
        q = q.filter(ScheduledLesson.room_id == entity_id)
    elif view_type == "class" and entity_id:
        q = q.join(CurriculumEntry, ScheduledLesson.curriculum_entry_id == CurriculumEntry.id)
        q = q.filter(CurriculumEntry.class_id == entity_id)

    lessons = q.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Dia", "Slot", "Disciplina", "Turma", "Professor", "Sala"])

    for lesson in sorted(lessons, key=lambda l: (l.day_of_week, l.slot_number)):
        entry = lesson.curriculum_entry
        writer.writerow([
            DAYS_PT[lesson.day_of_week],
            lesson.slot_number,
            entry.subject.name if entry and entry.subject else "",
            entry.class_.name if entry and entry.class_ else "",
            lesson.teacher.name if lesson.teacher else "",
            lesson.room.name if lesson.room else "",
        ])

    return output.getvalue()
