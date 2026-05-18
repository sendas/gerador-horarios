from collections import defaultdict
from app.models.models import Timetable, ScheduledLesson, CurriculumEntry, TimeSlotConfig

DAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]


def _get_lessons(db, timetable_id: int, view_type: str, entity_id: int):
    q = db.query(ScheduledLesson).filter(ScheduledLesson.timetable_id == timetable_id)
    if view_type == "teacher":
        q = q.filter(ScheduledLesson.teacher_id == entity_id)
    elif view_type == "room":
        q = q.filter(ScheduledLesson.room_id == entity_id)
    elif view_type == "class":
        q = q.join(CurriculumEntry, ScheduledLesson.curriculum_entry_id == CurriculumEntry.id)
        q = q.filter(CurriculumEntry.class_id == entity_id)
    return q.all()


def generate_html_timetable(db, timetable_id: int, view_type: str = "class", entity_id: int = None) -> str:
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        return "<p>Horário não encontrado</p>"

    lessons = _get_lessons(db, timetable_id, view_type, entity_id) if entity_id else []

    slot_rows = db.query(TimeSlotConfig).filter(
        TimeSlotConfig.academic_year_id == tt.academic_year_id,
        TimeSlotConfig.is_break == False  # noqa
    ).order_by(TimeSlotConfig.day_of_week, TimeSlotConfig.slot_number).all()

    all_slots = sorted({r.slot_number for r in slot_rows})
    slot_times = {}
    for r in slot_rows:
        if r.slot_number not in slot_times:
            slot_times[r.slot_number] = (r.start_time.strftime("%H:%M"), r.end_time.strftime("%H:%M"))

    grid = defaultdict(dict)
    for lesson in lessons:
        entry = lesson.curriculum_entry
        subject_name = entry.subject.name if entry and entry.subject else "?"
        subject_color = entry.subject.color if entry and entry.subject else "#ccc"
        class_name = entry.class_.name if entry and entry.class_ else ""
        teacher_name = lesson.teacher.name if lesson.teacher else ""
        room_name = lesson.room.name if lesson.room else ""

        if view_type == "teacher":
            label = f"{subject_name}<br><small>{class_name}</small>"
        elif view_type == "room":
            label = f"{subject_name}<br><small>{class_name} / {teacher_name}</small>"
        else:
            label = f"{subject_name}<br><small>{teacher_name}</small>"

        grid[lesson.slot_number][lesson.day_of_week] = (label, subject_color)

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Horário - {tt.name}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; }}
  h2 {{ color: #2c3e50; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: center; }}
  th {{ background: #2c3e50; color: white; }}
  .slot-time {{ background: #ecf0f1; font-weight: bold; font-size: 11px; }}
  .lesson {{ border-radius: 4px; padding: 4px; }}
</style>
</head>
<body>
<h2>Horário: {tt.name}</h2>
<table>
<thead>
<tr>
  <th>Hora</th>
  {"".join(f"<th>{DAYS_PT[d]}</th>" for d in range(5))}
</tr>
</thead>
<tbody>
"""
    for slot in all_slots:
        start, end = slot_times.get(slot, ("", ""))
        html += f'<tr><td class="slot-time">{start}<br>{end}</td>'
        for day in range(5):
            cell = grid[slot].get(day)
            if cell:
                label, color = cell
                html += f'<td><div class="lesson" style="background:{color}20;border-left:4px solid {color}">{label}</div></td>'
            else:
                html += '<td></td>'
        html += '</tr>\n'

    html += "</tbody></table></body></html>"
    return html
