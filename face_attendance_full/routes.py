# routes.py – dev JSON API (separate from web views)
from __future__ import annotations
import io, time, uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, Response, current_app
try:
    import cv2
except Exception:
    cv2 = None

routes = Blueprint("routes", __name__)

def _cors(json, code=200):
    resp = jsonify(json); resp.status_code = code
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return resp

@dataclass
class Student:
    id: str; name: str; roll: str; embedding: Optional[List[float]] = None; meta: Dict = None

@dataclass
class Session:
    id: str; title: str; course_code: Optional[str]; is_open: bool = True; created_at: float = time.time()

@dataclass
class Attendance:
    id: str; session_id: str; student_id: str; status: str; timestamp: float = time.time()

DB = { "students": {}, "sessions": {}, "attendance": {} }

@routes.route("/_health", methods=["GET"])
def health(): return _cors({"ok": True, "service": "face-attendance-api"})

@routes.route("/<path:any>", methods=["OPTIONS"])
def options_any(any): return _cors({"ok": True})

@routes.route("/dev/seed", methods=["POST"])
def dev_seed():
    s1 = Student(id="stu_"+uuid.uuid4().hex[:8], name="Alice", roll="R001")
    s2 = Student(id="stu_"+uuid.uuid4().hex[:8], name="Bob", roll="R002")
    DB["students"][s1.id] = s1; DB["students"][s2.id] = s2
    ses = Session(id="ses_"+uuid.uuid4().hex[:8], title="Demo Session", course_code="CS101")
    DB["sessions"][ses.id] = ses
    return _cors({"ok": True, "session_id": ses.id, "student_ids": [s1.id, s2.id]})
