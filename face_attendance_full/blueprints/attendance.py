from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required
from models import db, Course, Section, Student, Enrollment, Attendance, AttendanceSession
from vision.stream import gen_frames_for_session, camera_diagnostics

bp = Blueprint("attendance", __name__, template_folder="../templates")

@bp.route("/start", methods=["GET", "POST"])
@login_required
def start():
    if request.method == "GET":
        courses = Course.query.all()
        return render_template("start_session.html", courses=courses)
    course_id = int(request.form.get("course_id"))
    section_id = request.form.get("section_id")
    section_id = int(section_id) if section_id else None
    s = AttendanceSession(course_id=course_id, section_id=section_id, closed=False)
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("attendance.session", session_id=s.id))

@bp.route("/session/<int:session_id>")
@login_required
def session(session_id):
    s = AttendanceSession.query.get_or_404(session_id)
    course = Course.query.get_or_404(s.course_id)
    section = Section.query.get(s.section_id) if s.section_id else None
    return render_template("attendance_session.html", session=s, course=course, section=section)

@bp.route("/session/<int:session_id>/video")
@login_required
def video(session_id):
    return Response(gen_frames_for_session(session_id),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@bp.route("/session/<int:session_id>/manual", methods=["GET", "POST"])
@login_required
def manual(session_id):
    s = AttendanceSession.query.get_or_404(session_id)
    # students in this course (and section if set)
    q = Enrollment.query.filter_by(course_id=s.course_id)
    if s.section_id:
        q = q.filter_by(section_id=s.section_id)
    enrolled = q.all()
    students = Student.query.filter(Student.id.in_([e.student_id for e in enrolled]) if enrolled else False).all() if enrolled else []

    if request.method == "POST":
        present_ids = set(map(int, request.form.getlist("present")))
        for st in students:
            row = Attendance.query.filter_by(session_id=s.id, student_id=st.id).first()
            if st.id in present_ids:
                if not row:
                    db.session.add(Attendance(session_id=s.id, student_id=st.id, status="present"))
                else:
                    row.status = "present"
            else:
                if not row:
                    db.session.add(Attendance(session_id=s.id, student_id=st.id, status="absent"))
                else:
                    row.status = "absent"
        db.session.commit()
        flash("Manual attendance saved.", "success")
        return redirect(url_for("attendance.session", session_id=session_id))

    statuses = {}
    for st in students:
        row = Attendance.query.filter_by(session_id=s.id, student_id=st.id).first()
        statuses[st.id] = (row.status if row else "absent")
    return render_template("manual_attendance.html", session=s, students=students, statuses=statuses)

@bp.route("/session/<int:session_id>/close", methods=["POST"])
@login_required
def close(session_id):
    s = AttendanceSession.query.get_or_404(session_id)
    if s.closed:
        flash("Session already closed.", "warning")
        return redirect(url_for("attendance.session", session_id=session_id))

    # Fetch all enrolled students for this session's course/section
    q = Enrollment.query.filter_by(course_id=s.course_id)
    if s.section_id:
        q = q.filter_by(section_id=s.section_id)
    enrolled_ids = [e.student_id for e in q.all()]

    # Present students (already auto-marked by the stream)
    present_ids = {
        a.student_id for a in Attendance.query
        .filter_by(session_id=session_id, status="present")
        .all()
    }

    # Mark remaining as absent (idempotent upsert)
    for sid in enrolled_ids:
        if sid in present_ids:
            continue
        row = Attendance.query.filter_by(session_id=session_id, student_id=sid).first()
        if not row:
            db.session.add(Attendance(session_id=session_id, student_id=sid, status="absent"))
        else:
            row.status = "absent"

    s.closed = True
    db.session.commit()

    flash("Session closed. Absent marked for all remaining students.", "success")
    return redirect(url_for("attendance.session", session_id=session_id))


@bp.route("/present/<int:session_id>.json", methods=["GET"])
@login_required
def present_json(session_id):
    s = AttendanceSession.query.get_or_404(session_id)
    q = Enrollment.query.filter_by(course_id=s.course_id)
    if s.section_id:
        q = q.filter_by(section_id=s.section_id)
    enrolled_ids = [e.student_id for e in q.all()]
    students = Student.query.filter(Student.id.in_(enrolled_ids)).all()
    present_ids = {a.student_id for a in Attendance.query.filter_by(session_id=session_id, status="present")}
    present_names = [f"{st.name} ({st.student_code})" for st in students if st.id in present_ids]
    remaining_names = [f"{st.name} ({st.student_code})" for st in students if st.id not in present_ids]
    return {"present_names": present_names, "remaining_names": remaining_names}

@bp.route("/camera-diag", methods=["GET"])
@login_required
def camera_diag():
    return camera_diagnostics()
