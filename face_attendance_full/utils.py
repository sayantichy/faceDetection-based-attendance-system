from models import db, Enrollment, Attendance, AttendanceSession

def attendance_percentages(course_id:int):
    sessions = AttendanceSession.query.filter_by(course_id=course_id, closed=True).all()
    if not sessions:
        return {"labels": [], "percentages": []}
    labels, percentages = [], []
    for s in sessions:
        total = Enrollment.query.filter_by(course_id=course_id, section_id=s.section_id).count()
        present = db.session.query(Attendance).filter_by(session_id=s.id, status="present").count()
        pct = round(100.0 * present / total, 1) if total else 0.0
        labels.append(f"Sess {s.id}")
        percentages.append(pct)
    return {"labels": labels, "percentages": percentages}

def student_attendance_overview(student_id:int):
    rows = (
        db.session.query(Attendance, AttendanceSession)
        .join(AttendanceSession, Attendance.session_id == AttendanceSession.id)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.timestamp.desc())
        .all()
    )
    return [{"session_id": s.id, "course_id": s.course_id, "status": a.status, "time": a.timestamp.isoformat()} for a, s in rows]
