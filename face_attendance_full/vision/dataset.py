import os, cv2, time, numpy as np
from flask import current_app as app

def _camera():
    cam = cv2.VideoCapture(app.config.get("CAMERA_SOURCE", 0))
    if not cam.isOpened():
        raise RuntimeError("Could not access camera")
    return cam

def _prep(gray):
    return cv2.equalizeHist(gray)

def _save_face(gray_face, person_dir):
    face_resized = cv2.resize(gray_face, app.config["CAPTURE_IMAGE_SIZE"])
    os.makedirs(person_dir, exist_ok=True)
    img_path = os.path.join(person_dir, f"{int(time.time()*1000)}.png")
    cv2.imwrite(img_path, face_resized)
    return img_path

def capture_guided_three(student_code:str):
    prompts = [
        ("Front", "Look straight ahead."),
        ("Left",  "Turn your head slightly LEFT."),
        ("Right", "Turn your head slightly RIGHT."),
    ]
    person_dir = os.path.join(app.config["DATASET_DIR"], student_code)
    face_cascade = cv2.CascadeClassifier(app.config["HAAR_CASCADE"])
    cam = _camera()
    saved = 0
    try:
        for title, tip in prompts:
            captured = False
            while not captured:
                ret, frame = cam.read()
                if not ret:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = _prep(gray)
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=app.config["DETECTION_SCALE_FACTOR"],
                    minNeighbors=app.config["DETECTION_MIN_NEIGHBORS"]
                )
                if len(faces):
                    (x,y,w,h) = max(faces, key=lambda b: b[2]*b[3])
                    face = gray[y:y+h, x:x+w]
                    _save_face(face, person_dir)
                    saved += 1
                    captured = True
                if app.config.get("CAPTURE_SHOW_WINDOW", False):
                    vis = frame.copy()
                    for (x,y,w,h) in faces:
                        cv2.rectangle(vis, (x,y), (x+w,y+h), (0,255,0), 2)
                    cv2.putText(vis, f"{title}: {tip}", (10,30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                    cv2.imshow("Capture", vis)
                    if cv2.waitKey(1) & 0xFF == 27:
                        cam.release()
                        cv2.destroyAllWindows()
                        return saved
            time.sleep(0.2)
        return saved
    finally:
        cam.release()
        cv2.destroyAllWindows()

def save_uploaded_images(student_code:str, files):
    person_dir = os.path.join(app.config["DATASET_DIR"], student_code)
    face_cascade = cv2.CascadeClassifier(app.config["HAAR_CASCADE"])
    saved = 0
    skipped = 0
    for f in files:
        if not f or f.filename == "":
            continue
        data = np.frombuffer(f.read(), np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            skipped += 1
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = _prep(gray)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=app.config["DETECTION_SCALE_FACTOR"],
            minNeighbors=app.config["DETECTION_MIN_NEIGHBORS"]
        )
        if len(faces) == 0:
            skipped += 1
            continue
        (x,y,w,h) = max(faces, key=lambda b: b[2]*b[3])
        face = gray[y:y+h, x:x+w]
        _save_face(face, person_dir)
        saved += 1
    return saved, skipped
