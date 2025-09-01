# vision/recognizer.py
import os, json, cv2
import numpy as np
from flask import current_app as app

def _prep(img: np.ndarray) -> np.ndarray:
    """Return a 2D uint8 C-contiguous face image of target size."""
    if img is None:
        raise RuntimeError("Encountered None image during preprocessing.")
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    target = tuple(app.config["CAPTURE_IMAGE_SIZE"])
    if img.shape != target:
        img = cv2.resize(img, target)
    img = cv2.equalizeHist(img)
    img = np.ascontiguousarray(img, dtype=np.uint8)
    if img.ndim != 2 or img.dtype != np.uint8 or not img.flags["C_CONTIGUOUS"]:
        raise RuntimeError(f"Prepped image invalid (ndim={img.ndim}, dtype={img.dtype}, contiguous={img.flags['C_CONTIGUOUS']})")
    return img

def _list_images(dataset_dir):
    """Collect grayscale, prepped images + int32 labels + label_map."""
    images, labels = [], []
    label_map = {}     # numeric label -> student_code
    next_label = 0

    if not os.path.isdir(dataset_dir):
        return images, np.asarray([], dtype=np.int32), label_map

    persons = sorted([p for p in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, p))])
    for person in persons:
        pdir = os.path.join(dataset_dir, person)
        label_map[next_label] = person
        for fname in sorted(os.listdir(pdir)):
            if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            path = os.path.join(pdir, fname)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            prepped = _prep(img)
            images.append(prepped)
            labels.append(next_label)
        next_label += 1

    labels_np = np.ascontiguousarray(labels, dtype=np.int32)
    return images, labels_np, label_map

def _validate_training_set(images, labels_np):
    if len(images) == 0:
        raise RuntimeError("No face images found. Capture or upload faces first into dataset/<student_code>/")
    if len(images) != int(labels_np.shape[0]):
        raise RuntimeError(f"Images/labels mismatch: images={len(images)} labels={labels_np.shape}")
    # Strong checks on first few images
    for i, im in enumerate(images[:5]):
        if not isinstance(im, np.ndarray): raise RuntimeError(f"Image #{i} not numpy array (type={type(im)})")
        if im.ndim != 2:                  raise RuntimeError(f"Image #{i} not 2D (ndim={im.ndim})")
        if im.dtype != np.uint8:          raise RuntimeError(f"Image #{i} not uint8 (dtype={im.dtype})")
        if not im.flags['C_CONTIGUOUS']:  raise RuntimeError(f"Image #{i} not C-contiguous")
    if not isinstance(labels_np, np.ndarray) or labels_np.dtype != np.int32:
        raise RuntimeError(f"Labels must be np.int32 (got type={type(labels_np)} dtype={getattr(labels_np,'dtype',None)})")

def _train_with_fallbacks(recognizer, images, labels_np):
    """
    Try several input forms to handle OpenCV binding quirks on some platforms.
    """
    errors = []

    # 1) Plain list
    try:
        recognizer.train(images, labels_np)
        return
    except Exception as e:
        errors.append(f"list:{e}")

    # 2) Tuple(images)
    try:
        recognizer.train(tuple(images), labels_np)
        return
    except Exception as e:
        errors.append(f"tuple:{e}")

    # 3) Labels as (N,1)
    labels_col = labels_np.reshape(-1, 1)
    try:
        recognizer.train(images, labels_col)
        return
    except Exception as e:
        errors.append(f"list+labels_col:{e}")
    try:
        recognizer.train(tuple(images), labels_col)
        return
    except Exception as e:
        errors.append(f"tuple+labels_col:{e}")

    # 4) UMat list (some Win builds prefer UMats)
    try:
        umat_imgs = [cv2.UMat(im) for im in images]
        recognizer.train(umat_imgs, labels_np)
        return
    except Exception as e:
        errors.append(f"umat_list:{e}")

    try:
        recognizer.train(umat_imgs, labels_col)
        return
    except Exception as e:
        errors.append(f"umat_list+labels_col:{e}")

    # If we reach here, raise a concise combined error
    raise RuntimeError("LBPH.train failed. Tried forms: " + " | ".join(errors))

def train_lbph_model():
    dataset_dir = app.config["DATASET_DIR"]
    model_dir   = app.config["MODEL_DIR"]
    lbph_path   = app.config["LBPH_MODEL"]
    labels_path = app.config["LABELS_JSON"]

    images, labels_np, label_map = _list_images(dataset_dir)

    # Diagnostics (stdout)
    persons_count = len(set(label_map.values()))
    print(f"[train] persons={persons_count}, images={len(images)}, labels={labels_np.shape}, dtype={labels_np.dtype}")

    _validate_training_set(images, labels_np)

    # Re-assert they are strictly 2D uint8 C-contiguous (defensive)
    images = [np.ascontiguousarray(im, dtype=np.uint8) for im in images]

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    # Attempt with fallbacks
    _train_with_fallbacks(recognizer, images, labels_np)

    os.makedirs(model_dir, exist_ok=True)
    recognizer.write(lbph_path)
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(label_map, f, ensure_ascii=False, indent=2)

    print(f"[train] saved model: {lbph_path}")
    print(f"[train] saved labels: {labels_path}")
    return True

def load_recognizer():
    lbph_path   = app.config["LBPH_MODEL"]
    labels_path = app.config["LABELS_JSON"]
    if not os.path.exists(lbph_path) or not os.path.exists(labels_path):
        return None, None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(lbph_path)
    with open(labels_path, "r", encoding="utf-8") as f:
        label_map = json.load(f)  # {"0":"s1001", ...}
    inv = {int(k): v for k, v in label_map.items()}
    return recognizer, inv
