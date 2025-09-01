# Face Attendance (Flask + OpenCV) — v2

**Flask + SQLAlchemy + Flask-Login + OpenCV (LBPH) + Tailwind + Bootstrap + Chart.js**

## What's new in v2
- Enroll students directly on the **Course** page (inline form)
- Upload **multiple photos** per student from the Course page
- **Train model** button on the Course header (and dashboard)
- HaarCascade now uses OpenCV's built-in location automatically

## Quickstart

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
export FLASK_APP=app.py          # Windows PowerShell:  $env:FLASK_APP="app.py"
flask run --debug
```

Login: `admin@example.com` / `admin123`

## Flow
1. Create a **course** (+ section optional)
2. **Enroll students** (inline on the course page)
3. **Upload photos** for each student (10–30 per student recommended)
4. Click **Train Model**
5. Start **Attendance Session** -> students show face -> marked present automatically
6. Adjust in **Manual Attendance** if needed

> Images are cropped to face and normalized to 200×200 grayscale for better recognition.
