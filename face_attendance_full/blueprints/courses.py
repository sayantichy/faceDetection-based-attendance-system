from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from models import db, Course, Section, Student, Enrollment
from utils import attendance_percentages, student_attendance_overview
from vision.recognizer import train_lbph_model
from vision.dataset import save_uploaded_images, capture_guided_three

# Define the blueprint FIRST
bp = Blueprint("courses", __name__, template_folder="../templates")

# -------------------- OPTIONAL DIAGNOSTICS ROUTES --------------------

@bp.route("/train-model/diag", methods=["GET"])
@login_required
def train_model_diag():
    """
    Quick sanity check for the training dataset.
    Visit: /courses/train-model/diag
    """
    from vision.recognizer import _list_images
    dataset_dir = current_app.config["DATASET_DIR"]
    images, labels_np, label_map = _list_images(dataset_dir)
    return {
        "ok": True,
        "dataset_dir": dataset_dir,
        "persons": len(set(label_map.values())),
        "labels_dtype": str(getattr(labels_np, "dtype", None)),
        "labels_len": int(getattr(labels_np, "shape", [0])[0]),
        "images_len": len(images),
        "label_map": label_map,
    }

@bp.route("/train-model/inspect", methods=["GET"])
@login_required
def train_model_inspect():
    """
    Inspect the first few samples the trainer will use.
    Visit: /courses/train-model/inspect
    """
    from vision.recognizer import _list_images
    dataset_dir = current_app.config["DATASET_DIR"]
    images, labels_np, label_map = _list_images(dataset_dir)

    samples = []
    for i, im in enumerate(images[:5]):
        samples.append({
            "index": i,
            "type": str(type(im)),
            "shape": tuple(int(x) for x in getattr(im, "shape", ())),
            "dtype": str(getattr(im, "dtype", None)),
            "contiguous": bool(getattr(im, "flags", {}).c_contiguous if hasattr(im, "flags") else False),
            "min": int(im.min()) if hasattr(im, "min") else None,
            "max": int(im.max()) if hasattr(im, "max") else None,
        })

    return {
        "ok": True,
        "dataset_dir": dataset_dir,
        "persons": len(set(label_map.values())),
        "total_images": len(images),
        "labels_len": int(labels_np.shape[0]),
        "labels_dtype": str(labels_np.dtype),
        "label_map": label_map,
        "samples": samples
    }

# -------------------- YOUR PAGES / ACTIONS --------------------

@bp.route("/", methods=["GET"])
@login_required
def index():
    courses = Course.query.all()
    return render_template("courses.html", courses=courses)

@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_course():
    if request.method == "GET":
        return render_template("create_course.html")
    code = request.form.get("code", "").strip()
    title = request.form.get("title", "").strip()
    if not code or not title:
        flash("Code and Title are required.", "danger")
        return render_template("create_course.html"), 400
    if Course.query.filter_by(code=code).first():
        flash("Course code already exists.", "danger")
        return render_template("create_course.html"), 400
    c = Course(code=code, title=title)
    db.session.add(c)
    db.session.commit()
    flash("Course created.", "success")
    return redirect(url_for("courses.course_detail", course_id=c.id))

@bp.route("/<int:course_id>", methods=["GET"])
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    sections = Section.query.filter_by(course_id=course_id).all()
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    students = Student.query.filter(
        Student.id.in_([e.student_id for e in enrollments]) if enrollments else False
    ).all() if enrollments else []
    chart = attendance_percentages(course_id)
    return render_template("course_detail.html", course=course, sections=sections, students=students, chart=chart)

@bp.route("/<int:course_id>/create-section", methods=["POST"])
@login_required
def create_section(course_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Section name required.", "danger")
        return redirect(url_for("courses.course_detail", course_id=course_id))
    s = Section(name=name, course_id=course_id)
    db.session.add(s)
    db.session.commit()
    flash("Section created.", "success")
    return redirect(url_for("courses.course_detail", course_id=course_id))

@bp.route("/enroll", methods=["GET", "POST"])
@login_required
def enroll_student():
    if request.method == "GET":
        courses = Course.query.all()
        return render_template("enroll_student.html", courses=courses)

    student_code = request.form.get("student_code", "").strip()
    name = request.form.get("name", "").strip()
    course_id = int(request.form.get("course_id"))
    section_id = request.form.get("section_id")
    section_id = int(section_id) if section_id else None

    if not student_code or not name:
        flash("Student ID and Name required.", "danger")
        return redirect(url_for("courses.enroll_student"))

    student = Student.query.filter_by(student_code=student_code).first()
    if not student:
        student = Student(student_code=student_code, name=name)
        db.session.add(student)
        db.session.flush()

    exists = Enrollment.query.filter_by(student_id=student.id, course_id=course_id, section_id=section_id).first()
    if exists:
        flash("Student already enrolled in this course/section.", "warning")
    else:
        db.session.add(Enrollment(student_id=student.id, course_id=course_id, section_id=section_id))
        db.session.commit()
        flash("Student enrolled.", "success")

    return redirect(url_for("courses.course_detail", course_id=course_id))

@bp.route("/<int:course_id>/enroll-inline", methods=["POST"])
@login_required
def enroll_student_inline(course_id):
    student_code = request.form.get("student_code", "").strip()
    name = request.form.get("name", "").strip()
    section_id = request.form.get("section_id")
    section_id = int(section_id) if section_id else None

    if not student_code or not name:
        flash("Student ID and Name required.", "danger")
        return redirect(url_for("courses.course_detail", course_id=course_id))

    student = Student.query.filter_by(student_code=student_code).first()
    if not student:
        student = Student(student_code=student_code, name=name)
        db.session.add(student)
        db.session.flush()

    exists = Enrollment.query.filter_by(student_id=student.id, course_id=course_id, section_id=section_id).first()
    if exists:
        flash("Student already enrolled.", "warning")
    else:
        db.session.add(Enrollment(student_id=student.id, course_id=course_id, section_id=section_id))
        db.session.commit()
        flash("Student enrolled.", "success")

    return redirect(url_for("courses.course_detail", course_id=course_id))

@bp.route("/student/<int:student_id>", methods=["GET"])
@login_required
def student_detail(student_id):
    student = Student.query.get_or_404(student_id)
    overview = student_attendance_overview(student_id)
    return render_template("student_detail.html", student=student, overview=overview)

@bp.route("/students/<int:student_id>/capture", methods=["GET", "POST"])
@login_required
def capture_faces(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        saved = capture_guided_three(student.student_code)
        if saved:
            flash(f"Captured {saved} images for {student.name}.", "success")
        else:
            flash("No face captured. Try again with better lighting.", "warning")
        return redirect(url_for("courses.student_detail", student_id=student_id))
    return render_template("capture_faces.html")

@bp.route("/<int:course_id>/students/<int:student_id>/upload", methods=["POST"])
@login_required
def upload_student_photos(course_id, student_id):
    student = Student.query.get_or_404(student_id)
    files = request.files.getlist("photos")
    saved, skipped = save_uploaded_images(student.student_code, files)
    msg = f"Uploaded {saved} photos for {student.name}."
    if skipped:
        msg += f" Skipped {skipped} (no face / invalid)."
    flash(msg, "success" if saved else "warning")
    return redirect(url_for("courses.course_detail", course_id=course_id))

@bp.route("/train-model", methods=["POST"])
@login_required
def train_model():
    try:
        train_lbph_model()
        flash("Model trained successfully.", "success")
    except Exception as e:
        flash(f"Training failed: {e}", "danger")
    return redirect(request.referrer or url_for("courses.index"))
# put this in blueprints/courses.py after bp=...:
@bp.route("/train-model/opencv-info")
def opencv_info():
    import cv2, numpy as np, sys, platform, os
    return {
        "opencv_version": cv2.__version__,
        "opencv_file": getattr(cv2, "__file__", None),
        "has_face": bool(hasattr(cv2, "face")),
        "numpy_version": np.__version__,
        "python": sys.version,
        "platform": platform.platform(),
    }
