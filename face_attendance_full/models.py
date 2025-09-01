from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Teacher(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False, default="Teacher")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    sections = db.relationship("Section", backref="course", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="course", cascade="all, delete-orphan")

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    enrollments = db.relationship("Enrollment", backref="section", cascade="all, delete-orphan")

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")
    attendance = db.relationship("Attendance", backref="student", cascade="all, delete-orphan")

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"))
    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "section_id", name="uq_enroll"),)

class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed = db.Column(db.Boolean, default=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_session.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    status = db.Column(db.String(16), default="present")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("session_id", "student_id", name="uq_attendance"),)
