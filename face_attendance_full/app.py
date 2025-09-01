from flask import Flask, render_template
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, Teacher, Course
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # DB
    db.init_app(app)

    # Login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return Teacher.query.get(int(user_id))

    # Blueprints
    from routes import routes as api_routes
    app.register_blueprint(api_routes, url_prefix="/api")  # dev/JSON API under /api

    from blueprints.auth import bp as auth_bp
    from blueprints.courses import bp as courses_bp
    from blueprints.attendance import bp as attendance_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(courses_bp, url_prefix="/courses")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")

    # Seed admin user and tables
    with app.app_context():
        db.create_all()
        if not Teacher.query.filter_by(email="admin@example.com").first():
            t = Teacher(email="admin@example.com",
                        password_hash=generate_password_hash("admin123"),
                        name="Admin")
            db.session.add(t)
            db.session.commit()

    @app.route("/")
    @login_required
    def index():
        courses = Course.query.all()
        return render_template("dashboard.html", user=current_user, courses=courses)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False, threaded=True)
