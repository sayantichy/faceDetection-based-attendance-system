import os
import cv2

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATASET_DIR = os.path.join(BASE_DIR, "dataset")
    MODEL_DIR   = os.path.join(BASE_DIR, "models")
    HAAR_CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    LBPH_MODEL   = os.path.join(MODEL_DIR, "lbph.yml")
    LABELS_JSON  = os.path.join(MODEL_DIR, "labels.json")

    # Camera config
    CAMERA_SOURCE   = 0              # try 0, then 1 if you have external webcam
    CAMERA_BACKENDS = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
    CAMERA_INDICES  = [0, 1, 2, 3]


    # Detection/recognition
    DETECTION_SCALE_FACTOR = 1.1
    DETECTION_MIN_NEIGHBORS = 6
    RECOGNITION_CONFIDENCE_THRESHOLD = 95   # LBPH distance; lower is better
    RECOGNITION_COOLDOWN_SECONDS = 8
    CAPTURE_IMAGE_SIZE = (200, 200)

    # Capture / uploads
    CAPTURE_SHOW_WINDOW = True
    AUTO_TRAIN_AFTER_CAPTURE = False  # you can turn this on

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "models"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "dataset"), exist_ok=True)
