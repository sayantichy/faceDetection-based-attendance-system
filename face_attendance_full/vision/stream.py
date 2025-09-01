import time, cv2, platform, numpy as np
from collections import defaultdict
from flask import current_app, request
from models import db, Student, Enrollment, Attendance, AttendanceSession
from .recognizer import load_recognizer

_last_mark = defaultdict(float)

def _cfg(key, default=None):
    try:
        return current_app.config.get(key, default)
    except Exception:
        return default

def _open_camera():
    import itertools
    errors = []
    src = _cfg("CAMERA_SOURCE", 0)
    backends = _cfg("CAMERA_BACKENDS", [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY])
    indices  = _cfg("CAMERA_INDICES", [0, 1, 2, 3])

    # 1) URL string
    if isinstance(src, str) and src.strip():
        try:
            cam = cv2.VideoCapture(src)
            if cam is not None and cam.isOpened():
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return cam, {"url": src}
            if cam is not None:
                cam.release()
            errors.append(f"url not opened: {src}")
        except Exception as e:
            errors.append(f"url error: {e}")

    # Build index order: try the configured source first (if int), then the rest
    try_indices = []
    if isinstance(src, int):
        try_indices.append(src)
    for i in indices:
        if i not in try_indices:
            try_indices.append(i)

    # 2) Try (backend, index)
    for be, idx in itertools.product(backends, try_indices):
        try:
            cam = cv2.VideoCapture(idx, be)
            if cam is not None and cam.isOpened():
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return cam, {"index": idx, "backend": int(be)}
            if cam is not None:
                cam.release()
            errors.append(f"index={idx} backend={int(be)} not opened")
        except Exception as e:
            errors.append(f"index={idx} backend={int(be)} error={e}")

    # 3) FINAL FALLBACK: plain VideoCapture(index) WITHOUT backend
    for idx in try_indices:
        try:
            cam = cv2.VideoCapture(idx)
            if cam is not None and cam.isOpened():
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return cam, {"index": idx, "backend": "auto"}
            if cam is not None:
                cam.release()
            errors.append(f"index={idx} (no backend) not opened")
        except Exception as e:
            errors.append(f"index={idx} (no backend) error={e}")

    return None, {
        "errors": errors,
        "hint": "Try adjusting CAMERA_SOURCE/CAMERA_INDICES (0/1/2/3) and camera privacy settings; close apps using the camera."
    }

def camera_diagnostics():
    cam, meta = _open_camera()
    if cam is None:
        return {"ok": False, "meta": meta, "platform": platform.platform()}
    ret, frame = cam.read()
    cam.release()
    if not ret or frame is None:
        return {"ok": False, "meta": {"error": "read() failed"}, "platform": platform.platform()}
    return {"ok": True, "meta": meta, "platform": platform.platform(), "shape": [int(frame.shape[1]), int(frame.shape[0])]}

def gen_frames_for_session(session_id:int):
    cam, meta = _open_camera()
    if cam is None:
        # stream error frames so the <img> doesn't hang
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Camera not available", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
            msg = meta.get("errors", [""])[0] if isinstance(meta, dict) else ""
            if msg:
                cv2.putText(frame, msg[:48], (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
            ret, buffer = cv2.imencode(".jpg", frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
            time.sleep(0.5)

    face_cascade_path = _cfg("HAAR_CASCADE")
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    recog, label_map = load_recognizer()
    scale = _cfg("DETECTION_SCALE_FACTOR", 1.1)
    neighbors = _cfg("DETECTION_MIN_NEIGHBORS", 6)
    size = tuple(_cfg("CAPTURE_IMAGE_SIZE", (200,200)))
    thr = _cfg("RECOGNITION_CONFIDENCE_THRESHOLD", 95)
    cooldown = _cfg("RECOGNITION_COOLDOWN_SECONDS", 8)

    debug = request.args.get("debug") in ("1","true","yes")

    while True:
        ok, frame = cam.read()
        if not ok or frame is None:
            frame = np.zeros((480,640,3), dtype=np.uint8)
            cv2.putText(frame, "Camera read() failed", (40,80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(gray, scaleFactor=scale, minNeighbors=neighbors, minSize=(70,70))

        for (x,y,w,h) in faces:
            face = cv2.resize(gray[y:y+h, x:x+w], size)

            name = "Unknown"
            conf_txt = ""

            if recog is not None and label_map:
                try:
                    label, confidence = recog.predict(face)  # LBPH distance
                except Exception:
                    label, confidence = (-1, 9999.0)

                if (label in label_map) and (confidence <= thr):
                    student_code = label_map[label]
                    student = Student.query.filter_by(student_code=student_code).first()
                    if student:
                        name = f"{student.name} ({student.student_code})"
                        conf_txt = f"{confidence:.1f}"
                        now = time.time()
                        if now - _last_mark[student.id] > cooldown:
                            sess = AttendanceSession.query.get(session_id)
                            if sess:
                                enrolled = Enrollment.query.filter_by(
                                    student_id=student.id,
                                    course_id=sess.course_id,
                                    section_id=sess.section_id
                                ).first()
                                if enrolled:
                                    if not Attendance.query.filter_by(session_id=session_id, student_id=student.id).first():
                                        db.session.add(Attendance(session_id=session_id, student_id=student.id, status="present"))
                                        db.session.commit()
                                    _last_mark[student.id] = now

            color = (0,255,0) if name != "Unknown" else (0,0,255)
            cv2.rectangle(frame, (x,y), (x+w,y+h), color, 2)
            label_text = f"{name}" + (f"  conf:{conf_txt}" if (debug and conf_txt) else "")
            cv2.putText(frame, label_text, (x, y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        ret, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
